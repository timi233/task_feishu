import sqlite3
import json
from datetime import datetime

# 连接到SQLite数据库
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

print("=== 检查 feishu_records 表中的 '服务开始时间' 和 '服务开始时间1' 字段 ===")

# 获取所有记录
cursor.execute("SELECT record_id, fields FROM feishu_records")
all_feishu_rows = cursor.fetchall()

# 统计两个字段的使用情况
start_time_count = 0
start_time_1_count = 0
both_count = 0
neither_count = 0

# 查找特定日期的记录
target_date = "2025-08-25"
target_timestamp_start = 1756089600000  # 2025-08-25 00:00:00 UTC
target_timestamp_end = 1756175999999    # 2025-08-25 23:59:59 UTC

records_with_target_date = []

for record_id, fields_json in all_feishu_rows:
    try:
        fields = json.loads(fields_json)
        
        # 检查字段存在性
        has_start_time = '服务开始时间' in fields
        has_start_time_1 = '服务开始时间1' in fields
        
        if has_start_time:
            start_time_count += 1
        if has_start_time_1:
            start_time_1_count += 1
        if has_start_time and has_start_time_1:
            both_count += 1
        if not has_start_time and not has_start_time_1:
            neither_count += 1
            
        # 检查目标日期
        # 检查 '服务开始时间'
        service_start_time = fields.get('服务开始时间')
        if isinstance(service_start_time, (int, float)) and target_timestamp_start <= service_start_time <= target_timestamp_end:
            records_with_target_date.append({
                'record_id': record_id,
                'field': '服务开始时间',
                'timestamp': service_start_time,
                'date': datetime.fromtimestamp(service_start_time/1000.0).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # 检查 '服务开始时间1'
        service_start_time_1 = fields.get('服务开始时间1')
        if isinstance(service_start_time_1, (int, float)) and target_timestamp_start <= service_start_time_1 <= target_timestamp_end:
            records_with_target_date.append({
                'record_id': record_id,
                'field': '服务开始时间1',
                'timestamp': service_start_time_1,
                'date': datetime.fromtimestamp(service_start_time_1/1000.0).strftime('%Y-%m-%d %H:%M:%S')
            })
            
    except json.JSONDecodeError:
        pass # 忽略无效的JSON

print(f"'服务开始时间' 字段存在的记录数: {start_time_count}")
print(f"'服务开始时间1' 字段存在的记录数: {start_time_1_count}")
print(f"两个字段都存在的记录数: {both_count}")
print(f"两个字段都不存在的记录数: {neither_count}")

print(f"\n在 {target_date} 的记录:")
if records_with_target_date:
    print(f"找到 {len(records_with_target_date)} 条记录:")
    for i, record in enumerate(records_with_target_date):
        print(f"  {i+1}. Record ID: {record['record_id']}")
        print(f"      字段: {record['field']}")
        print(f"      时间戳: {record['timestamp']}")
        print(f"      转换日期: {record['date']}")
else:
    print(f"没有找到日期为 {target_date} 的记录。")

# 关闭连接
cursor.close()
conn.close()