import sqlite3

# 连接到SQLite数据库
# 数据库文件在当前目录下，名为 tasks.db
conn = sqlite3.connect('tasks.db')

# 创建一个Cursor对象
cursor = conn.cursor()

# 1. 检查 feishu_records 表
cursor.execute('SELECT COUNT(*) FROM feishu_records')
raw_count = cursor.fetchone()[0]
print(f"数据库中总共有 {raw_count} 条原始飞书记录")

# 2. 检查 tasks 表
cursor.execute('SELECT COUNT(*) FROM tasks')
processed_count = cursor.fetchone()[0]
print(f"数据库中总共有 {processed_count} 条处理后的任务记录")

# 3. 检查 current_week_tasks_view 视图
try:
    cursor.execute('SELECT COUNT(*) FROM current_week_tasks_view')
    view_count = cursor.fetchone()[0]
    print(f"数据库视图中总共有 {view_count} 条本周任务记录")
except sqlite3.OperationalError as e:
    print(f"无法查询视图: {e}")

# 如果处理后的任务表有数据，查看前几条
if processed_count > 0:
    cursor.execute('SELECT record_id, task_name, assignee, status, date, weekday FROM tasks LIMIT 5')
    rows = cursor.fetchall()
    print("\n处理后的任务表前5条记录:")
    for row in rows:
        print(row)

# 如果原始记录表有数据，查看前几条
if raw_count > 0:
    cursor.execute('SELECT record_id, LENGTH(fields) FROM feishu_records LIMIT 3')
    rows = cursor.fetchall()
    print("\n原始飞书记录表前3条记录 (仅显示Record ID和fields长度):")
    for row in rows:
        print(row)

# 关闭Cursor和Connection
cursor.close()
conn.close()