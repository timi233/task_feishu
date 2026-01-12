import sqlite3
import json
from datetime import datetime

# 连接到SQLite数据库
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

print("=== 检查 tasks 表中的日期字段 ===")
# 1. 检查 tasks 表中 date 字段为 '2025-08-25' 的记录
cursor.execute("SELECT * FROM tasks WHERE date = '2025-08-25'")
tasks_rows = cursor.fetchall()
print(f"tasks 表中 date = '2025-08-25' 的记录数: {len(tasks_rows)}")
if tasks_rows:
    print("前2条记录:")
    for i, row in enumerate(tasks_rows[:2]):
        print(f"  {i+1}. {row}")

print("\n=== 检查 feishu_records 表中的原始日期字段 ===")
# 2. 检查 feishu_records 表中 fields 包含 '服务开始时间1' 且对应日期为 2025-08-25 的记录
# 飞书时间戳是毫秒级的，2025-08-25 00:00:00 UTC 对应的时间戳是 1756089600000
# 2025-08-25 23:59:59 UTC 对应的时间戳是 1756175999999
start_timestamp = 1756089600000
end_timestamp = 1756175999999

# 我们需要遍历 feishu_records 表，反序列化 fields，然后检查服务开始时间
cursor.execute("SELECT record_id, fields FROM feishu_records")
all_feishu_rows = cursor.fetchall()
matching_records = []

for record_id, fields_json in all_feishu_rows:
    try:
        fields = json.loads(fields_json)
        # 检查 '服务开始时间1' 字段
        service_start_time = fields.get('服务开始时间1')
        if isinstance(service_start_time, (int, float)) and start_timestamp <= service_start_time <= end_timestamp:
            matching_records.append((record_id, fields))
    except json.JSONDecodeError:
        pass # 忽略无效的JSON

print(f"feishu_records 表中 '服务开始时间1' 在 2025-08-25 的记录数: {len(matching_records)}")
if matching_records:
    print("前2条匹配的原始记录:")
    for i, (record_id, fields) in enumerate(matching_records[:2]):
        print(f"  {i+1}. Record ID: {record_id}")
        print(f"      服务开始时间1: {fields.get('服务开始时间1')}")
        # 尝试转换时间戳以验证
        try:
            ts = fields.get('服务开始时间1')
            dt = datetime.fromtimestamp(ts/1000.0)
            print(f"      转换为日期: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            pass
        print(f"      客户公司名称: {fields.get('客户公司名称', 'N/A')}")
        print(f"      工作内容: {fields.get('工作内容', 'N/A')}")
        print("      ---")

# 3. 检查 tasks 表中所有不同的日期
print("\n=== tasks 表中所有不同的日期 ===")
cursor.execute("SELECT DISTINCT date FROM tasks ORDER BY date")
distinct_dates = cursor.fetchall()
print("所有日期:")
for date_row in distinct_dates:
    print(f"  {date_row[0]}")

# 4. 检查 feishu_records 表中所有不同的 '服务开始时间1' 日期
print("\n=== feishu_records 表中 '服务开始时间1' 的日期分布 ===")
date_distribution = {}
for record_id, fields_json in all_feishu_rows:
    try:
        fields = json.loads(fields_json)
        service_start_time = fields.get('服务开始时间1')
        if isinstance(service_start_time, (int, float)):
            # 转换为日期字符串
            dt = datetime.fromtimestamp(service_start_time/1000.0)
            date_str = dt.strftime('%Y-%m-%d')
            date_distribution[date_str] = date_distribution.get(date_str, 0) + 1
    except json.JSONDecodeError:
        pass

# 打印日期分布
sorted_dates = sorted(date_distribution.items())
print("日期分布:")
for date_str, count in sorted_dates:
    print(f"  {date_str}: {count} 条记录")

# 关闭连接
cursor.close()
conn.close()