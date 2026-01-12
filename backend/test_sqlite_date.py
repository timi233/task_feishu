import sqlite3

# 连接到SQLite数据库
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# 测试 SQLite 的日期计算
cursor.execute("SELECT DATE('now', 'weekday 1', '-6 days') as monday, DATE('now', 'weekday 1') as sunday")
result = cursor.fetchone()
if result:
    monday, sunday = result
    print(f"SQLite 计算的本周一: {monday}")
    print(f"SQLite 计算的本周日: {sunday}")
else:
    print("无法计算日期")

# 关闭连接
cursor.close()
conn.close()