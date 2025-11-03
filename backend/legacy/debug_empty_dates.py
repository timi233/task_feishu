import sqlite3
import json

# 连接到SQLite数据库
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# 1. 检查视图定义
cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'view' AND name = 'current_week_tasks_view'")
view_definition = cursor.fetchone()
if view_definition:
    print("=== current_week_tasks_view 的定义 ===")
    print(view_definition[0])
else:
    print("未找到视图 current_week_tasks_view")

# 2. 找出 date 字段为空的记录
cursor.execute("SELECT record_id, task_name, assignee, status FROM tasks WHERE date = ''")
empty_date_tasks = cursor.fetchall()

print(f"\n=== date 字段为空的记录 (共 {len(empty_date_tasks)} 条) ===")
# 为了减少输出，只打印前10条
for i, (record_id, task_name, assignee, status) in enumerate(empty_date_tasks[:10]):
    print(f"  {i+1}. Record ID: {record_id}")
    print(f"      Task Name: {task_name}")
    print(f"      Assignee: {assignee}")
    print(f"      Status: {status}")
    print("      ---")

if len(empty_date_tasks) > 10:
    print(f"  ... 还有 {len(empty_date_tasks) - 10} 条记录")

# 3. 检查这些记录在 feishu_records 表中的原始数据
print(f"\n=== 检查部分空日期记录的原始数据 ===")
for i, (record_id, _, _, _) in enumerate(empty_date_tasks[:3]):
    cursor.execute("SELECT fields FROM feishu_records WHERE record_id = ?", (record_id,))
    raw_record = cursor.fetchone()
    if raw_record:
        try:
            fields = json.loads(raw_record[0])
            print(f"  Record ID: {record_id}")
            print(f"    客户公司名称: {fields.get('客户公司名称', 'N/A')}")
            print(f"    工作内容: {fields.get('工作内容', 'N/A')}")
            print(f"    售后工程师: {fields.get('售后工程师', 'N/A')}")
            print(f"    优先级: {fields.get('优先级', 'N/A')}")
            print(f"    服务开始时间: {fields.get('服务开始时间', 'N/A')}")
            print(f"    服务开始时间1: {fields.get('服务开始时间1', 'N/A')}")
        except json.JSONDecodeError:
            print(f"  Record ID: {record_id} (无法解析原始数据)")
    print("  ---")

# 关闭连接
cursor.close()
conn.close()