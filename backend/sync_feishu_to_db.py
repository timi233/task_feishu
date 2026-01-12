import time
import os
import schedule
import logging
from typing import Callable, TypeVar, Any, List, Dict
from read_feishu_data import FeishuBitableReader
from process_feishu_data import process_feishu_records
from task_db import init_db, save_processed_tasks_to_db, save_engineers_to_db
from feishu_contacts import FeishuContactsReader

# 独立脚本需要配置日志
if __name__ == "__main__":
    from utils.logging_config import setup_logging
    setup_logging(app_name="sync_feishu")

logger = logging.getLogger(__name__)

# 类型变量用于重试装饰器
T = TypeVar('T')

# --- 配置部分 ---
# 飞书应用凭证
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")

# 新的多数据源配置（派工单）
DISPATCH_BASE_ID = os.getenv("FEISHU_DISPATCH_BASE_ID", "U7eAb65luaX1zKscoOzcgcednlh")
COMPANY_DISPATCH_TABLE_ID = os.getenv("FEISHU_WORK_ORDER_TABLE_ID", "tbl6CuEM97ybgRri")  # 公司派单
EISOO_DISPATCH_TABLE_ID = os.getenv("FEISHU_EISOO_DISPATCH_TABLE_ID", "tbl8DESrT22JYvfS")  # 厂家派工

# 数据源列表配置
DATA_SOURCES = [
    {
        "name": "公司派单",
        "app_token": DISPATCH_BASE_ID,
        "table_id": COMPANY_DISPATCH_TABLE_ID,
    },
    {
        "name": "厂家派工",
        "app_token": DISPATCH_BASE_ID,
        "table_id": EISOO_DISPATCH_TABLE_ID,
    },
]

# 旧配置（保留向后兼容，但不再使用）
CONFIG = {
    "app_id": APP_ID,
    "app_secret": APP_SECRET,
    "app_token": os.getenv("FEISHU_APP_TOKEN"),
    "table_id": os.getenv("FEISHU_TABLE_ID")
}

# 同步间隔（分钟）- 默认30分钟
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "30"))

# 🔄 重试配置 (P2-10)
MAX_RETRIES = int(os.getenv("SYNC_MAX_RETRIES", "3"))       # 最大重试次数
INITIAL_DELAY = float(os.getenv("SYNC_INITIAL_DELAY", "1.0"))  # 初始延迟(秒)
MAX_DELAY = float(os.getenv("SYNC_MAX_DELAY", "60.0"))      # 最大延迟(秒)
# --- 配置结束 ---


def exponential_backoff_retry(
    func: Callable[[], T],
    max_retries: int = MAX_RETRIES,
    initial_delay: float = INITIAL_DELAY,
    max_delay: float = MAX_DELAY,
    operation_name: str = "operation"
) -> T:
    """
    指数退避重试函数

    🔄 P2-10: 添加飞书API调用重试机制

    Args:
        func: 要重试的函数（无参数）
        max_retries: 最大重试次数（默认3次）
        initial_delay: 初始延迟秒数（默认1秒）
        max_delay: 最大延迟秒数（默认60秒）
        operation_name: 操作名称（用于日志）

    Returns:
        函数执行结果

    Raises:
        最后一次重试的异常

    Example:
        >>> def fetch_data():
        ...     return reader.get_records(token, table_id)
        >>> records = exponential_backoff_retry(fetch_data, operation_name="fetch records")
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            logger.debug(f"[RETRY] {operation_name}: attempt {attempt + 1}/{max_retries}")
            result = func()

            if attempt > 0:
                logger.info(f"[RETRY] {operation_name} succeeded on attempt {attempt + 1}")

            return result

        except Exception as e:
            last_exception = e

            # 最后一次重试失败，直接抛出异常
            if attempt == max_retries - 1:
                logger.error(
                    f"[RETRY] {operation_name} failed after {max_retries} attempts: {e}"
                )
                raise

            # 计算下次重试延迟（指数退避）
            delay = min(initial_delay * (2 ** attempt), max_delay)

            logger.warning(
                f"[RETRY] {operation_name} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                f"Retrying in {delay:.1f}s..."
            )

            time.sleep(delay)

    # 理论上不会到达这里，但为了类型安全
    raise last_exception or Exception(f"{operation_name} failed")


def sync_engineers_to_db():
    """从飞书通讯录同步工程师数据到数据库（带重试机制）

    🔄 P2-10: 应用重试机制到工程师同步
    """
    logger.info("\n[ENGINEER SYNC] Starting engineer synchronization...")

    try:
        # 1. 初始化飞书通讯录读取器
        contacts_reader = FeishuContactsReader(CONFIG["app_id"], CONFIG["app_secret"])

        # 2. 从飞书通讯录获取用户列表（带重试）
        logger.info("[ENGINEER SYNC] Fetching users from Feishu contacts...")

        def fetch_users():
            """闭包函数用于重试"""
            return contacts_reader.get_users(page_size=50)

        users = exponential_backoff_retry(
            fetch_users,
            operation_name="fetch Feishu contacts"
        )

        if not users:
            logger.warning("[ENGINEER SYNC] No users fetched from Feishu contacts.")
            return 0

        logger.info(f"[ENGINEER SYNC] Fetched {len(users)} users from Feishu")

        # 3. 过滤在职用户
        active_users = contacts_reader.filter_active_users(users)
        logger.info(f"[ENGINEER SYNC] Active users: {len(active_users)}/{len(users)}")

        # 4. 转换为工程师格式
        engineers = contacts_reader.transform_to_engineers(active_users)

        # 5. 保存到数据库
        logger.info(f"[ENGINEER SYNC] Saving {len(engineers)} engineers to database...")
        saved_count = save_engineers_to_db(engineers)

        logger.info(f"[ENGINEER SYNC] Engineer synchronization completed: {saved_count} engineers saved")
        return saved_count

    except Exception as e:
        logger.error(f"[ENGINEER SYNC ERROR] Engineer synchronization failed: {e}")
        return 0


def sync_feishu_data_to_db():
    """从飞书同步数据到数据库（包括任务数据和工程师数据，带重试机制）

    🔄 支持多数据源同步：公司派单 + 厂家派工
    """
    logger.info(f"\n[SYNC] Starting data synchronization at {time.ctime()}")

    try:
        # === 第一部分: 同步任务数据（多数据源） ===
        # 初始化飞书读取器
        reader = FeishuBitableReader(APP_ID, APP_SECRET)

        # 合并所有数据源的记录
        all_raw_records = []

        for source in DATA_SOURCES:
            source_name = source["name"]
            app_token = source["app_token"]
            table_id = source["table_id"]

            logger.info(f"[SYNC] Fetching data from '{source_name}' (table: {table_id})...")

            def fetch_records_from_source(token=app_token, tid=table_id):
                """闭包函数用于重试"""
                return reader.get_records(token, tid)

            try:
                raw_records = exponential_backoff_retry(
                    fetch_records_from_source,
                    operation_name=f"fetch {source_name}"
                )

                if raw_records:
                    logger.info(f"[SYNC] Fetched {len(raw_records)} records from '{source_name}'")
                    all_raw_records.extend(raw_records)
                else:
                    logger.warning(f"[SYNC] No data fetched from '{source_name}'")

            except Exception as e:
                logger.error(f"[SYNC] Failed to fetch from '{source_name}': {e}")
                # 继续同步其他数据源
                continue

        if not all_raw_records:
            logger.warning("[SYNC] No raw data fetched from any source. Skipping task sync.")
        else:
            # 处理合并后的原始数据
            logger.info(f"[SYNC] Processing {len(all_raw_records)} total records...")
            processed_tasks = process_feishu_records(all_raw_records)

            # 计算任务总数
            total_tasks = sum(len(tasks) for tasks in processed_tasks.values())

            # 保存处理后的数据到数据库
            logger.info("[SYNC] Saving processed tasks to database...")
            save_processed_tasks_to_db(processed_tasks)

            logger.info(f"[SYNC] Task synchronization completed: {total_tasks} task records saved")

        # === 第二部分: 同步工程师数据 ===
        engineer_count = sync_engineers_to_db()

        logger.info("[SYNC] Data synchronization completed successfully.")
        logger.info(f"[SYNC] Summary: {len(all_raw_records)} raw records from {len(DATA_SOURCES)} sources, {engineer_count} engineers synced")

    except Exception as e:
        logger.error(f"[SYNC ERROR] Data synchronization failed: {e}")


if __name__ == "__main__":
    # 初始化数据库
    init_db()
    
    # 立即运行一次同步
    sync_feishu_data_to_db()
    
    # 安排定时任务
    schedule.every(SYNC_INTERVAL_MINUTES).minutes.do(sync_feishu_data_to_db)
    print(f"[SCHEDULER] Scheduled data sync every {SYNC_INTERVAL_MINUTES} minutes.")
    
    # 保持脚本运行
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SCHEDULER] Scheduler stopped by user.")
