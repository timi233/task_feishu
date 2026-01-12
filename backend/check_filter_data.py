import sqlite3
from datetime import datetime, timedelta

# 连接到数据库
conn = sqlite3.connect('db/tasks.db')
cursor = conn.cursor()

# 计算本周的开始和结束日期（周日到周六）
today = datetime.now()
start_of_week = today - timedelta(days=(today.weekday() + 1) % 7)  # 上一个周日
end_of_week = start_of_week + timedelta(days=6)  # 本周六

start_str = start_of_week.strftime('%Y-%m-%d')
end_str = end_of_week.strftime('%Y-%m-%d')

print(f'本周日期范围: {start_str} 到 {end_str}')

# 查询符合筛选条件的任务
cursor.execute('''
    SELECT record_id, task_name, assignee, status, date, start_date, end_date 
    FROM tasks 
    WHERE status IN ('已通过', '审批中') 
    AND date BETWEEN ? AND ?
''', (start_str, end_str))

rows = cursor.fetchall()
print(f'符合筛选条件的任务数量: {len(rows)}')

if rows:
    print('\n符合筛选条件的任务:')
    for row in rows:
        print(f'  Record ID: {row[0]}')
        print(f'    Task Name: {row[1]}')
        print(f'    Assignee: {row[2]}')
        print(f'    Status: {row[3]}')
        print(f'    Date: {row[4]}')
        print(f'    Start Date: {row[5]}')
        print(f'    End Date: {row[6]}')
        print('    ---')
else:
    print('\n没有符合筛选条件的任务')

# 查询所有任务的状态分布
cursor.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status')
status_rows = cursor.fetchall()
print('\n所有任务的状态分布:')
for row in status_rows:
    print(f'  {row[0]}: {row[1]} 条任务')

# 查询本周的所有任务
cursor.execute('''
    SELECT record_id, task_name, assignee, status, date, start_date, end_date 
    FROM tasks 
    WHERE date BETWEEN ? AND ?
''', (start_str, end_str))

all_week_rows = cursor.fetchall()
print(f'\n本周总任务数量: {len(all_week_rows)}')

conn.close()