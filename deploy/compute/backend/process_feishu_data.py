import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from read_feishu_data import FeishuBitableReader

# --- 配置部分 (需要根据你的飞书表格字段进行修改) ---
# 请根据你实际的飞书多维表格字段名修改以下映射
CUSTOMER_NAME_FIELD = "客户公司名称"  # 客户公司名称字段
TASK_CONTENT_FIELD = "工作内容"  # 工作内容字段
ASSIGNEE_FIELD = "售后工程师"  # 负责人字段
PRIORITY_FIELD = "优先级"  # 优先级字段
APPLICATION_STATUS_FIELD = "申请状态"  # 申请状态字段
# 日期字段 (开始时间和结束时间)
START_DATE_FIELD = "服务开始时间"  # 开始日期字段 (时间戳)
END_DATE_FIELD = "服务结束时间"    # 结束日期字段 (时间戳)
# --- 配置结束 ---


def convert_timestamp_to_date(timestamp_ms: int) -> str:
    """将毫秒级时间戳转换为 YYYY-MM-DD 格式的日期字符串"""
    try:
        # 飞书时间戳通常是毫秒级的
        dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"[WARN] Failed to convert timestamp {timestamp_ms}: {e}")
        return ""


def process_feishu_records(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    将原始飞书记录处理并转换为前端所需的格式（按星期一分组）
    对于跨天任务，会在每个涵盖的日期都生成一条记录
    """
    task_groups = {
        "monday": [],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "weekend": [],  # 可选：处理周末数据
        "unknown_date": []  # 可选：处理日期解析失败的数据
    }

    # 星期映射
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]

    for item in records:
        record_id = item.get("record_id", "")
        fields = item.get("fields", {})

        # 1. 提取任务名称: 客户公司名称 + 工作内容
        customer_name = fields.get(CUSTOMER_NAME_FIELD, "")
        task_content = fields.get(TASK_CONTENT_FIELD, "")
        task_name = f"{customer_name} {task_content}".strip()

        # 2. 提取负责人 (售后工程师)
        # 假设是一个用户列表，提取所有用户的名字
        assignee = "未知负责人"
        assignee_obj = fields.get(ASSIGNEE_FIELD, [])
        if isinstance(assignee_obj, list) and len(assignee_obj) > 0:
            assignee_names = []
            for user in assignee_obj:
                if isinstance(user, dict) and "name" in user:
                    assignee_names.append(user["name"])
            if assignee_names:
                assignee = ", ".join(assignee_names)  # 用逗号分隔多个负责人
        elif isinstance(assignee_obj, dict) and "name" in assignee_obj:
            # 如果不是列表而是单个对象
            assignee = assignee_obj["name"]

        # 3. 提取状态 (现在是优先级)
        priority = fields.get(PRIORITY_FIELD, "未知优先级")
        
        # 4. 提取申请状态并转换为展示状态
        application_status = fields.get(APPLICATION_STATUS_FIELD, "")
        # 根据申请状态转换为展示状态
        if application_status == "审批中":
            status = "进行中"
        elif application_status == "已通过":
            status = "已结束"
        else:
            # 如果没有申请状态或不是指定的值，则使用优先级作为默认状态
            status = priority

        # 4. 提取并转换开始和结束日期
        # 优先使用 "服务开始时间" 和 "服务结束时间"
        # 如果这两个字段都为空，则跳过这条记录
        start_timestamp = fields.get(START_DATE_FIELD)
        end_timestamp = fields.get(END_DATE_FIELD)
        
        # 如果主字段为空，不使用带1的备选字段
        # 直接跳过这条记录
        if start_timestamp is None and end_timestamp is None:
            # 添加到 unknown_date 组，因为没有有效日期
            task_item = {
                "record_id": record_id,
                "task_name": task_name,
                "assignee": assignee,
                "status": status,
                "date": "",  # 日期为空
                "start_date": "",
                "end_date": ""
            }
            task_groups["unknown_date"].append(task_item)
            continue # 跳过后续处理
            
        # 如果只有一个字段有值，也视为无效，跳过
        # (根据业务需求，你也可以选择只使用有的那个字段)
        # 这里我们选择跳过
        if start_timestamp is None or end_timestamp is None:
            # 添加到 unknown_date 组
            task_item = {
                "record_id": record_id,
                "task_name": task_name,
                "assignee": assignee,
                "status": status,
                "date": "",  # 日期为空
                "start_date": "",
                "end_date": ""
            }
            task_groups["unknown_date"].append(task_item)
            continue # 跳过后续处理
        
        start_date_str = ""
        end_date_str = ""
        
        if isinstance(start_timestamp, (int, float)):
            start_date_str = convert_timestamp_to_date(int(start_timestamp))
        if isinstance(end_timestamp, (int, float)):
            end_date_str = convert_timestamp_to_date(int(end_timestamp))

        # 5. 为每个涵盖的日期生成任务记录
        # 如果只有开始日期或只有结束日期，则只在那一天显示
        # 如果开始日期和结束日期都有效，则在两者之间的每一天都显示
        dates_to_show = []
        
        if start_date_str and end_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
                # 包含开始和结束日期
                current_dt = start_dt
                while current_dt <= end_dt:
                    dates_to_show.append(current_dt.strftime("%Y-%m-%d"))
                    current_dt += timedelta(days=1)
            except ValueError:
                # 日期格式无法解析
                if start_date_str:
                    dates_to_show.append(start_date_str)
                elif end_date_str:
                    dates_to_show.append(end_date_str)
        elif start_date_str:
            dates_to_show.append(start_date_str)
        elif end_date_str:
            dates_to_show.append(end_date_str)
        else:
            # 日期解析失败，添加到 unknown_date 组
            task_item = {
                "record_id": record_id,
                "task_name": task_name,
                "assignee": assignee,
                "status": status,
                "date": "",  # 日期为空
                "start_date": start_date_str,
                "end_date": end_date_str
            }
            task_groups["unknown_date"].append(task_item)
            continue # 跳过后续处理

        # 6. 为每个日期创建任务记录并分组
        for date_str in dates_to_show:
            # 确定星期几并分组
            weekday_key = "unknown_date"
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                weekday_index = date_obj.weekday()  # Monday is 0, Sunday is 6
                if 0 <= weekday_index <= 4:
                    weekday_key = weekdays[weekday_index]
                else:
                    weekday_key = "weekend"
            except ValueError:
                # 日期格式无法解析
                pass

            # 构造前端需要的任务对象
            task_item = {
                "record_id": record_id,
                "task_name": task_name,
                "assignee": assignee,
                "status": status,
                "priority": priority,  # 保留原始优先级字段
                "application_status": application_status,  # 添加申请状态字段
                "date": date_str,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "weekday": weekday_key
            }

            # 添加到对应的分组
            task_groups[weekday_key].append(task_item)

    return task_groups


if __name__ == "__main__":
    # 请替换为你的实际飞书应用信息和多维表格信息
    CONFIG = {
        "app_id": "cli_a8e5c86826ab9013",
        "app_secret": "ObaI5gvFKKKtKZD09olblhM13kXrNFXB",
        "app_token": "ZbpqbNgpNa0IvTsXfLuc5seBnJg",  # 派工表格
        "table_id": "tblIrTdzXCFUwjti"  # 派工表格中的具体表
    }

    print("开始从飞书多维表格获取数据...")
    reader = FeishuBitableReader(CONFIG["app_id"], CONFIG["app_secret"])
    raw_records = reader.get_records(CONFIG["app_token"], CONFIG["table_id"])

    if not raw_records:
        print("未能获取到任何记录，程序退出。")
        exit(1)

    print(f"成功获取到 {len(raw_records)} 条原始记录，开始处理...")
    processed_tasks = process_feishu_records(raw_records)

    # 打印处理结果统计
    print("\n处理结果统计:")
    for day, tasks in processed_tasks.items():
        print(f"  {day}: {len(tasks)} 个任务")

    # 打印本周一的前几个任务作为示例
    monday_tasks = processed_tasks.get("monday", [])
    if monday_tasks:
        print(f"\n本周一的部分任务示例 (共{len(monday_tasks)}个):")
        for i, task in enumerate(monday_tasks[:3]):
            print(f"  {i+1}. {task}")
    else:
        print("\n本周一没有任务。")
        
    # 为了方便查看，也可以将处理后的数据保存为JSON文件
    # with open("processed_tasks.json", "w", encoding="utf-8") as f:
    #     json.dump(processed_tasks, f, ensure_ascii=False, indent=2)
    # print("\n处理后的数据已保存到 processed_tasks.json")