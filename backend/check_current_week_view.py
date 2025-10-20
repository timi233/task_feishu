import sqlite3
from datetime import datetime, timedelta

# 连接到SQLite数据库
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# 计算本周的日期范围 (周一到周日)
today = datetime.now()
start_of_week = today - timedelta(days=today.weekday())
end_of_week = start_of_week + timedelta(days=6) # 周日
start_str = start_of_week.strftime("%Y-%m-%d")
end_str = end_of_week.strftime("%Y-%m-%d")

print(f"=== 本周日期范围 ({start_str} to {end_str}) ===")

# 1. 查询视图中的数据
try:
    cursor.execute("SELECT date, COUNT(*) as count FROM current_week_tasks_view GROUP BY date ORDER BY date")
    view_date_counts = cursor.fetchall()
    print("=== current_week_tasks_view 中的数据 ===")
    if view_date_counts:
        for date, count in view_date_counts:
            print(f"  {date}: {count} 条记录")
    else:
        print("  视图中没有数据")
except sqlite3.OperationalError as e:
    print(f"查询视图时出错: {e}")

# 2. 直接查询 tasks 表中本周的数据
cursor.execute("""
    SELECT date, COUNT(*) as count 
    FROM tasks 
    WHERE date BETWEEN ? AND ? 
    GROUP BY date 
    ORDER BY date
""", (start_str, end_str))

direct_query_results = cursor.fetchall()
print(f"=== 直接查询 tasks 表中 {start_str} 到 {end_str} 的数据 ===")
if direct_query_results:
    for date, count in direct_query_results:
        print(f"  {date}: {count} 条记录")
else:
    print("  直接查询没有数据")

# 关闭连接
cursor.close()
conn.close()