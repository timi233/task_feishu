import sqlite3

# 连接到SQLite数据库
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# 1. 删除旧的视图 (如果存在)
try:
    cursor.execute("DROP VIEW IF EXISTS current_week_tasks_view")
    print("已删除旧的视图")
except sqlite3.OperationalError as e:
    print(f"删除视图时出错: {e}")

# 2. 创建新的视图
try:
    cursor.execute("""
        CREATE VIEW current_week_tasks_view AS
        SELECT * FROM tasks 
        WHERE date BETWEEN 
            (SELECT DATE('now', 'weekday 1', '-7 days')) -- 本周一
            AND 
            (SELECT DATE('now', 'weekday 1', '-1 day')) -- 本周日
    """)
    print("已创建新的视图")
except sqlite3.OperationalError as e:
    print(f"创建视图时出错: {e}")

# 3. 测试新的视图
try:
    cursor.execute("SELECT COUNT(*) FROM current_week_tasks_view")
    count = cursor.fetchone()[0]
    print(f"新视图中的记录数: {count}")
    
    cursor.execute("SELECT DISTINCT date FROM current_week_tasks_view ORDER BY date")
    dates = cursor.fetchall()
    print("新视图中的日期:")
    for date_row in dates:
        print(f"  {date_row[0]}")
        
except sqlite3.OperationalError as e:
    print(f"测试视图时出错: {e}")

# 4. 再次测试 SQLite 的日期计算
cursor.execute("SELECT DATE('now', 'weekday 1', '-7 days') as monday, DATE('now', 'weekday 1', '-1 day') as sunday")
result = cursor.fetchone()
if result:
    monday, sunday = result
    print(f"\nSQLite 计算的本周一: {monday}")
    print(f"SQLite 计算的本周日: {sunday}")

# 关闭连接
cursor.close()
conn.close()