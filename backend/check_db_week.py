import sqlite3
from datetime import datetime, timedelta

# 连接到SQLite数据库
# 数据库文件在当前目录下，名为 tasks.db
conn = sqlite3.connect('tasks.db')

# 创建一个Cursor对象
cursor = conn.cursor()

# 计算本周的日期范围
today = datetime.now()
# 计算本周一
start_of_week = today - timedelta(days=today.weekday())
# 计算本周五
end_of_week = start_of_week + timedelta(days=4)

start_str = start_of_week.strftime("%Y-%m-%d")
end_str = end_of_week.strftime("%Y-%m-%d")

print(f"Current week dates: {start_str} to {end_str}")

# 1. 通过日期范围查询本周任务的数量
cursor.execute('SELECT COUNT(*) FROM tasks WHERE date BETWEEN ? AND ?', (start_str, end_str))
count_by_date = cursor.fetchone()[0]
print(f"通过日期范围查询，数据库中本周总共有 {count_by_date} 条任务记录")

# 2. 通过视图查询本周任务的数量
try:
    cursor.execute('SELECT COUNT(*) FROM current_week_tasks_view')
    count_by_view = cursor.fetchone()[0]
    print(f"通过视图查询，数据库中本周总共有 {count_by_view} 条任务记录")
except sqlite3.OperationalError as e:
    print(f"无法通过视图查询: {e}")
    count_by_view = 0

# 如果通过日期范围查询有数据，查看前几条
if count_by_date > 0:
    cursor.execute('SELECT record_id, task_name, assignee, status, date, weekday FROM tasks WHERE date BETWEEN ? AND ? LIMIT 5', (start_str, end_str))
    rows = cursor.fetchall()
    print("\n本周前5条记录 (通过日期范围查询):")
    for row in rows:
        print(row)

# 如果通过视图查询有数据，查看前几条
if count_by_view > 0:
    cursor.execute('SELECT record_id, task_name, assignee, status, date, weekday FROM current_week_tasks_view LIMIT 5')
    rows = cursor.fetchall()
    print("\n本周前5条记录 (通过视图查询):")
    for row in rows:
        print(row)

# 如果本周没有任务，查看数据库中所有的日期
if count_by_date == 0 and count_by_view == 0:
    print("\n数据库中本周没有任务记录。")
    # 查看数据库中所有的日期，以便调试
    cursor.execute('SELECT DISTINCT date FROM tasks ORDER BY date')
    all_dates = cursor.fetchall()
    print("\n数据库中所有不同的日期:")
    for date in all_dates:
        print(date[0])

# 关闭Cursor和Connection
cursor.close()
conn.close()