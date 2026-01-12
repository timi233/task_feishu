import sqlite3

# 连接到SQLite数据库
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# 1. 检查总任务数
cursor.execute("SELECT COUNT(*) FROM tasks")
total_count = cursor.fetchone()[0]
print(f"数据库中总共有 {total_count} 条任务记录")

# 2. 检查有多少任务的 start_date 或 end_date 为空
cursor.execute("""
    SELECT COUNT(*) 
    FROM tasks 
    WHERE start_date = '' OR end_date = '' OR start_date IS NULL OR end_date IS NULL
""")
empty_date_count = cursor.fetchone()[0]
print(f"start_date 或 end_date 为空的任务数: {empty_date_count}")

# 3. 查找一些日期不为空的任务的例子
cursor.execute("""
    SELECT record_id, task_name, assignee, status, date, start_date, end_date 
    FROM tasks 
    WHERE start_date != '' AND end_date != '' AND start_date IS NOT NULL AND end_date IS NOT NULL
    LIMIT 5
""")
valid_tasks = cursor.fetchall()
print(f"\n日期有效的任务示例 (最多显示5条):")
for task in valid_tasks:
    print(f"  Record ID: {task[0]}")
    print(f"    Task Name: {task[1]}")
    print(f"    Assignee: {task[2]}")
    print(f"    Status: {task[3]}")
    print(f"    Display Date: {task[4]}")
    print(f"    Start Date: {task[5]}")
    print(f"    End Date: {task[6]}")
    print("    ---")

# 关闭连接
cursor.close()
conn.close()