import sqlite3

# 连接到SQLite数据库
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# 1. 检查总任务数
cursor.execute("SELECT COUNT(*) FROM tasks")
total_count = cursor.fetchone()[0]
print(f"数据库中总共有 {total_count} 条任务记录")

# 2. 查找一些跨天任务的例子
cursor.execute("""
    SELECT record_id, task_name, assignee, status, date, start_date, end_date 
    FROM tasks 
    WHERE start_date != end_date AND start_date IS NOT NULL AND end_date IS NOT NULL
    LIMIT 5
""")
cross_day_tasks = cursor.fetchall()
print(f"\n跨天任务示例 (最多显示5条):")
for task in cross_day_tasks:
    print(f"  Record ID: {task[0]}")
    print(f"    Task Name: {task[1]}")
    print(f"    Assignee: {task[2]}")
    print(f"    Status: {task[3]}")
    print(f"    Display Date: {task[4]}")
    print(f"    Start Date: {task[5]}")
    print(f"    End Date: {task[6]}")
    print("    ---")

# 3. 查找一个特定任务的所有日期记录
if cross_day_tasks:
    sample_record_id = cross_day_tasks[0][0]
    cursor.execute("""
        SELECT record_id, task_name, assignee, status, date, start_date, end_date 
        FROM tasks 
        WHERE record_id = ?
        ORDER BY date
    """, (sample_record_id,))
    
    all_dates_for_task = cursor.fetchall()
    print(f"\n任务 {sample_record_id} 的所有日期记录:")
    for task in all_dates_for_task:
        print(f"  Date: {task[4]}, Start: {task[5]}, End: {task[6]}")

# 关闭连接
cursor.close()
conn.close()