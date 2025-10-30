import sqlite3
import json

# 连接到SQLite数据库
# 数据库文件在当前目录下，名为 tasks.db
conn = sqlite3.connect('tasks.db')

# 创建一个Cursor对象
cursor = conn.cursor()

# 执行查询语句，获取原始记录的数量
cursor.execute('SELECT COUNT(*) FROM feishu_records')
count = cursor.fetchone()[0]
print(f"数据库中总共有 {count} 条原始飞书记录")

# 如果有数据，我们可以查看前几条
if count > 0:
    cursor.execute('SELECT record_id, fields, created_time, last_modified_time FROM feishu_records LIMIT 3')
    rows = cursor.fetchall()
    print("\n前3条原始记录:")
    for i, row in enumerate(rows):
        record_id, fields_json, created_time, last_modified_time = row
        print(f"\n--- Record {i+1} ---")
        print(f"  Record ID: {record_id}")
        print(f"  Created Time: {created_time}")
        print(f"  Last Modified Time: {last_modified_time}")
        # 将JSON字符串反序列化为字典
        try:
            fields = json.loads(fields_json)
            print(f"  Fields (first 5 items):")
            # 打印前5个字段
            for j, (key, value) in enumerate(fields.items()):
                if j >= 5:
                    print(f"    ... and {len(fields) - 5} more fields")
                    break
                print(f"    {key}: {value}")
        except json.JSONDecodeError:
            print(f"  Fields: (Invalid JSON) {fields_json}")

# 关闭Cursor和Connection
cursor.close()
conn.close()