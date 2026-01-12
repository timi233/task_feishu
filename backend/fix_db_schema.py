import sqlite3

# 连接到SQLite数据库
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# 1. 删除旧的 tasks 表 (这将丢失所有数据)
try:
    cursor.execute("DROP TABLE IF EXISTS tasks")
    print("已删除旧的 tasks 表")
except sqlite3.OperationalError as e:
    print(f"删除 tasks 表时出错: {e}")

# 2. 重新初始化数据库 (这会创建新的 tasks 表)
# 我们直接调用 task_db.py 中的 init_db 函数
try:
    from task_db import init_db
    init_db()
    print("已重新初始化数据库")
except Exception as e:
    print(f"重新初始化数据库时出错: {e}")

# 3. 验证新表结构
try:
    cursor.execute("PRAGMA table_info(tasks)")
    columns = cursor.fetchall()
    print("\n新的 tasks 表结构:")
    for col in columns:
        print(f"  列名: {col[1]}, 类型: {col[2]}, 是否可为空: {col[3]}, 默认值: {col[4]}, 是否为主键: {col[5]}")
except sqlite3.OperationalError as e:
    print(f"查询表结构时出错: {e}")

# 关闭连接
cursor.close()
conn.close()