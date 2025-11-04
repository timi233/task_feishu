import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
from read_feishu_data import FeishuBitableReader

# 日志由main.py统一配置
logger = logging.getLogger(__name__)

# --- 配置部分 (需要根据你的飞书表格字段进行修改) ---
# 请根据你实际的飞书多维表格字段名修改以下映射
CUSTOMER_NAME_FIELD = "客户公司名称"  # 客户公司名称字段
TASK_CONTENT_FIELD = "工作内容"  # 工作内容字段
ASSIGNEE_FIELD = "售后工程师"  # 负责人字段
PRIORITY_FIELD = "优先级"  # 优先级字段
APPLICATION_STATUS_FIELD = "申请状态"  # 申请状态字段
# 审批相关字段
APPROVAL_INSTANCE_FIELD = "审批实例ID"
APPROVAL_STATUS_FIELD = "审批状态"
# 日期字段 (开始时间和结束时间)
START_DATE_FIELD = "服务开始时间"  # 开始日期字段 (时间戳)
END_DATE_FIELD = "服务结束时间"    # 结束日期字段 (时间戳)
# 发起人字段
CREATOR_FIELD = "发起人"  # 发起人字段 (用户对象)
# --- 配置结束 ---


# ========== 辅助函数 (P2-8: 简化日期处理逻辑) ==========

def parse_timestamp(ts: Any) -> datetime | None:
    """
    解析毫秒时间戳为datetime对象

    Args:
        ts: 时间戳（毫秒），可能是int/float/None

    Returns:
        datetime对象，失败返回None
    """
    if ts is None:
        return None

    if not isinstance(ts, (int, float)):
        logger.warning(f"Invalid timestamp type: {type(ts)}, value: {ts}")
        return None

    try:
        return datetime.fromtimestamp(ts / 1000.0)
    except (ValueError, OSError) as e:
        logger.warning(f"Invalid timestamp value: {ts}, error: {e}")
        return None


def expand_date_range(start: datetime | None, end: datetime | None) -> List[str]:
    """
    展开日期范围为日期列表

    Args:
        start: 开始日期
        end: 结束日期

    Returns:
        日期字符串列表 (YYYY-MM-DD格式)
    """
    if not start or not end:
        return []

    if start > end:
        logger.warning(f"Start date {start} is after end date {end}, swapping")
        start, end = end, start

    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return dates


def get_weekday_key(date_str: str) -> str:
    """
    获取日期对应的星期key

    Args:
        date_str: 日期字符串 (YYYY-MM-DD)

    Returns:
        weekday key: monday/tuesday/.../weekend/unknown_date
    """
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        weekday_index = date_obj.weekday()  # Monday=0, Sunday=6

        if 0 <= weekday_index <= 4:
            return weekdays[weekday_index]
        else:
            return "weekend"
    except ValueError as e:
        logger.warning(f"Invalid date format: {date_str}, error: {e}")
        return "unknown_date"


def extract_assignee(assignee_field: Any) -> str:
    """
    提取负责人姓名

    Args:
        assignee_field: 负责人字段（可能是列表/字典/None）

    Returns:
        负责人姓名，多个用逗号分隔
    """
    if isinstance(assignee_field, list):
        names = [user.get("name") for user in assignee_field if isinstance(user, dict) and "name" in user]
        return ", ".join(names) if names else "未知负责人"

    if isinstance(assignee_field, dict) and "name" in assignee_field:
        return assignee_field["name"]

    return "未知负责人"


def extract_creator(creator_field: Any) -> tuple[str | None, str | None]:
    """
    提取发起人ID和姓名

    Args:
        creator_field: 发起人字段（可能是字典/列表/None）

    Returns:
        (creator_id, creator_name) 元组，如果无法提取则返回 (None, None)
    """
    # 单个用户对象（常见情况）
    if isinstance(creator_field, dict):
        user_id = creator_field.get("id")
        user_name = creator_field.get("name")
        if user_id and user_name:
            return (user_id, user_name)

    # 列表形式（取第一个）
    if isinstance(creator_field, list) and len(creator_field) > 0:
        first_user = creator_field[0]
        if isinstance(first_user, dict):
            user_id = first_user.get("id")
            user_name = first_user.get("name")
            if user_id and user_name:
                return (user_id, user_name)

    # 无法提取
    return (None, None)


def map_application_status(application_status: str, priority: str) -> str:
    """
    将申请状态转换为展示状态

    Args:
        application_status: 申请状态（审批中/已通过等）
        priority: 优先级（作为回退）

    Returns:
        展示状态
    """
    if application_status == "审批中":
        return "进行中"
    elif application_status == "已通过":
        return "已结束"
    else:
        return priority  # 使用优先级作为默认状态


def create_task_item(
    record_id: str,
    fields: Dict[str, Any],
    date: str,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    创建单个任务项

    Args:
        record_id: 记录ID
        fields: 飞书字段数据
        date: 任务展示日期 (YYYY-MM-DD)
        start_date: 任务实际开始日期
        end_date: 任务实际结束日期

    Returns:
        任务字典
    """
    # 提取字段
    customer_name = fields.get(CUSTOMER_NAME_FIELD, "")
    task_content = fields.get(TASK_CONTENT_FIELD, "")
    task_name = f"{customer_name} {task_content}".strip()

    # 提取负责人
    assignee = extract_assignee(fields.get(ASSIGNEE_FIELD))

    # 提取发起人
    creator_id, creator_name = extract_creator(fields.get(CREATOR_FIELD))

    # 提取状态
    priority = fields.get(PRIORITY_FIELD, "未知优先级")
    application_status = fields.get(APPLICATION_STATUS_FIELD, "")
    status = map_application_status(application_status, priority)

    # 审批相关
    approval_instance_code = fields.get(APPROVAL_INSTANCE_FIELD)
    approval_status = fields.get(APPROVAL_STATUS_FIELD)

    # 获取星期key
    weekday = get_weekday_key(date) if date else "unknown_date"

    return {
        "record_id": record_id,
        "task_name": task_name,
        "assignee": assignee,
        "creator_id": creator_id,
        "creator_name": creator_name,
        "status": status,
        "priority": priority,
        "application_status": application_status,
        "date": date,
        "start_date": start_date,
        "end_date": end_date,
        "weekday": weekday,
        "approval_instance_code": approval_instance_code,
        "approval_status": approval_status
    }


# ========== 旧版转换函数（保留向后兼容） ==========
def convert_timestamp_to_date(timestamp_ms: int) -> str:
    """将毫秒级时间戳转换为 YYYY-MM-DD 格式的日期字符串

    ⚠️ 已废弃，请使用 parse_timestamp() 函数
    """
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OSError) as e:
        logger.warning("Invalid timestamp %s, using today as fallback: %s", timestamp_ms, e)
        return datetime.now().strftime("%Y-%m-%d")
    except Exception as e:
        logger.error("Unexpected error converting timestamp %s: %s", timestamp_ms, e)
        return datetime.now().strftime("%Y-%m-%d")


def process_feishu_records(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    将原始飞书记录处理并转换为前端所需的格式（按星期分组）

    🔧 P2-8: 简化版本，使用辅助函数提高可读性

    对于跨天任务，会在每个涵盖的日期都生成一条记录

    Args:
        records: 飞书原始记录列表

    Returns:
        按星期分组的任务字典
    """
    task_groups = {
        "monday": [],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "weekend": [],
        "unknown_date": []
    }

    for item in records:
        record_id = item.get("record_id", "")
        fields = item.get("fields", {})

        # 1. 解析日期（使用新的辅助函数）
        start_dt = parse_timestamp(fields.get(START_DATE_FIELD))
        end_dt = parse_timestamp(fields.get(END_DATE_FIELD))

        # 2. 如果没有有效日期，添加到unknown_date组
        if not start_dt or not end_dt:
            start_date_str = start_dt.strftime("%Y-%m-%d") if start_dt else ""
            end_date_str = end_dt.strftime("%Y-%m-%d") if end_dt else ""

            task_item = create_task_item(
                record_id=record_id,
                fields=fields,
                date="",
                start_date=start_date_str,
                end_date=end_date_str
            )
            task_groups["unknown_date"].append(task_item)
            continue

        # 3. 展开日期范围（使用新的辅助函数）
        start_date_str = start_dt.strftime("%Y-%m-%d")
        end_date_str = end_dt.strftime("%Y-%m-%d")
        dates = expand_date_range(start_dt, end_dt)

        if not dates:
            # 展开失败，添加到unknown_date
            task_item = create_task_item(
                record_id=record_id,
                fields=fields,
                date="",
                start_date=start_date_str,
                end_date=end_date_str
            )
            task_groups["unknown_date"].append(task_item)
            continue

        # 4. 为每个日期创建任务项（使用新的辅助函数）
        for date_str in dates:
            task_item = create_task_item(
                record_id=record_id,
                fields=fields,
                date=date_str,
                start_date=start_date_str,
                end_date=end_date_str
            )

            # 根据weekday分组
            weekday_key = task_item["weekday"]
            task_groups[weekday_key].append(task_item)

    return task_groups


if __name__ == "__main__":
    CONFIG = {
        "app_id": os.getenv("FEISHU_APP_ID"),
        "app_secret": os.getenv("FEISHU_APP_SECRET"),
        "app_token": os.getenv("FEISHU_APP_TOKEN"),
        "table_id": os.getenv("FEISHU_TABLE_ID")
    }

    logger.info("开始从飞书多维表格获取数据...")
    reader = FeishuBitableReader(CONFIG["app_id"], CONFIG["app_secret"])
    raw_records = reader.get_records(CONFIG["app_token"], CONFIG["table_id"])

    if not raw_records:
        logger.warning("未能获取到任何记录，程序退出。")
        exit(1)

    logger.info("成功获取到 %d 条原始记录，开始处理...", len(raw_records))
    processed_tasks = process_feishu_records(raw_records)

    # 打印处理结果统计
    logger.info("处理结果统计:")
    for day, tasks in processed_tasks.items():
        logger.info("  %s: %d 个任务", day, len(tasks))

    # 打印本周一的前几个任务作为示例
    monday_tasks = processed_tasks.get("monday", [])
    if monday_tasks:
        logger.info("本周一的部分任务示例 (共%d个):", len(monday_tasks))
        for i, task in enumerate(monday_tasks[:3]):
            logger.info("  %d. %s", i + 1, task)
    else:
        logger.info("本周一没有任务。")

    # 为了方便查看，也可以将处理后的数据保存为JSON文件
    # with open("processed_tasks.json", "w", encoding="utf-8") as f:
    #     json.dump(processed_tasks, f, ensure_ascii=False, indent=2)
    # logger.info("处理后的数据已保存到 processed_tasks.json")
