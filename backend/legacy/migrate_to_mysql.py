import sqlite3
import pymysql
from datetime import datetime

def migrate_data():
    # 连接 SQLite 数据库
    sqlite_conn = sqlite3.connect('/app/db/tasks.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # 连接 MySQL 数据库
    mysql_conn = pymysql.connect(
        host='mysql',
        port=3306,
        user='root',
        password='1qaz2wsx',
        database='feishu_task_db'
    )
    mysql_cursor = mysql_conn.cursor()
    
    # 创建表结构
    mysql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            record_id VARCHAR(255) NOT NULL,
            task_name TEXT NOT NULL,
            assignee VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            priority VARCHAR(50) NOT NULL,
            application_status VARCHAR(255),
            date DATE NOT NULL,
            start_date DATE,
            end_date DATE,
            weekday VARCHAR(20) NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_record_date (record_id, date)
        )
    """)
    
    mysql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS feishu_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            record_id VARCHAR(255) UNIQUE NOT NULL,
            fields JSON NOT NULL,
            created_time BIGINT,
            last_modified_time BIGINT,
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    
    mysql_conn.commit()
    
    # 迁移 tasks 表数据
    sqlite_cursor.execute("SELECT * FROM tasks")
    tasks_rows = sqlite_cursor.fetchall()
    for row in tasks_rows:
        mysql_cursor.execute("""
            INSERT INTO tasks (record_id, task_name, assignee, status, priority, application_status, date, start_date, end_date, weekday)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            task_name=VALUES(task_name), assignee=VALUES(assignee), status=VALUES(status), 
            priority=VALUES(priority), application_status=VALUES(application_status), 
            start_date=VALUES(start_date), end_date=VALUES(end_date), weekday=VALUES(weekday)
        """, row[1:])  # 跳过 SQLite 的 id 字段
    
    # 迁移 feishu_records 表数据
    sqlite_cursor.execute("SELECT * FROM feishu_records")
    feishu_rows = sqlite_cursor.fetchall()
    for row in feishu_rows:
        # 将 fields 字段转换为 JSON 字符串
        fields_json = row[2]
        mysql_cursor.execute("""
            INSERT INTO feishu_records (record_id, fields, created_time, last_modified_time)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            fields=VALUES(fields), created_time=VALUES(created_time), last_modified_time=VALUES(last_modified_time)
        """, (row[1], fields_json, row[3], row[4]))
    
    mysql_conn.commit()
    
    # 关闭连接
    sqlite_conn.close()
    mysql_conn.close()
    
    print("数据迁移完成")

if __name__ == "__main__":
    migrate_data()