import os
from read_feishu_data import FeishuBitableReader
from process_feishu_data import process_feishu_records
from task_db import init_db, save_processed_tasks_to_db

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
# --- 配置结束 ---


def sync_feishu_data_once():
    """从飞书同步数据到数据库 (仅运行一次，支持多数据源)"""
    print(f"\n[SYNC] Starting one-time data synchronization...")
    print(f"[SYNC] Data sources: {[s['name'] for s in DATA_SOURCES]}")

    try:
        # 1. 初始化飞书读取器
        reader = FeishuBitableReader(APP_ID, APP_SECRET)

        # 2. 从多个数据源获取原始数据
        all_raw_records = []

        for source in DATA_SOURCES:
            source_name = source["name"]
            app_token = source["app_token"]
            table_id = source["table_id"]

            print(f"[SYNC] Fetching data from '{source_name}' (table: {table_id})...")

            try:
                raw_records = reader.get_records(app_token, table_id)

                if raw_records:
                    print(f"[SYNC] Fetched {len(raw_records)} records from '{source_name}'")
                    all_raw_records.extend(raw_records)
                else:
                    print(f"[SYNC] No data fetched from '{source_name}'")

            except Exception as e:
                print(f"[SYNC] Failed to fetch from '{source_name}': {e}")
                # 继续同步其他数据源
                continue

        if not all_raw_records:
            print("[SYNC] No raw data fetched from any source. Skipping sync.")
            return False

        # 3. 处理原始数据
        print(f"[SYNC] Processing {len(all_raw_records)} total records...")
        processed_tasks = process_feishu_records(all_raw_records)

        # 计算任务总数
        total_tasks = sum(len(tasks) for tasks in processed_tasks.values())

        # 4. 保存处理后的数据到数据库
        print("[SYNC] Saving processed data to database...")
        save_processed_tasks_to_db(processed_tasks)

        print(f"[SYNC] One-time data synchronization completed: {len(all_raw_records)} raw records -> {total_tasks} task records")
        return True

    except Exception as e:
        print(f"[SYNC ERROR] One-time data synchronization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 初始化数据库
    init_db()

    # 运行一次同步
    success = sync_feishu_data_once()

    if success:
        print("\n[SUCCESS] Data sync finished successfully.")
    else:
        print("\n[FAILURE] Data sync failed.")
