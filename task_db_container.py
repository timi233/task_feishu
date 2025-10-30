import sqlite3
from typing import Dict, List, Any, Optional
import os
from datetime import datetime, timedelta
import json

# 数据库文件路径
DB_FILE = "db/tasks.db"

def init_db():
    """初始化数据库，创建任务表和视图"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建存储处理后任务的表 (用于API查询)
    # 修改表结构以支持跨天任务和新字段
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL,
            task_name TEXT NOT NULL,
            assignee TEXT NOT NULL,
            status TEXT NOT NULL, -- 展示状态（进行中/已结束/优先级）
            priority TEXT NOT NULL, -- 原始优先级
            application_status TEXT, -- 申请状态
            date TEXT NOT NULL,   -- 任务在这一天展示 (YYYY-MM-DD)
            start_date TEXT,      -- 任务实际开始日期 (YYYY-MM-DD)
            end_date TEXT,        -- 任务实际结束日期 (YYYY-MM-DD)
            weekday TEXT NOT NULL, -- monday, tuesday, etc.
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- 添加唯一约束，防止重复插入同一天的同一条记录
            UNIQUE(record_id, date)
        )
    """)
    
    # 创建存储飞书原始数据的表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feishu_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT UNIQUE NOT NULL,
            fields TEXT NOT NULL, -- 存储序列化后的fields字典
            created_time INTEGER, -- 飞书记录创建时间戳
            last_modified_time INTEGER, -- 飞书记录最后修改时间戳
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 本次同步时间
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_weekday ON tasks (weekday)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_date ON tasks (date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feishu_record_id ON feishu_records (record_id)")
    
    # 创建视图：本周任务视图
    # 注意：视图中的日期是动态计算的，所以视图本身不存储数据，
    # 每次查询视图时都会根据当前日期计算本周一和本周日
    # 修正日期计算逻辑
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS current_week_tasks_view AS
        SELECT * FROM tasks 
        WHERE date BETWEEN 
            (SELECT DATE('now', 'weekday 1', '-7 days')) -- 本周一 (修正)
            AND 
            (SELECT DATE('now', 'weekday 1', '-1 day')) -- 本周日 (修正)
    """)
    
    conn.commit()
    conn.close()
    print(f"[DB] Database initialized. Tables 'tasks', 'feishu_records' and view 'current_week_tasks_view' are ready.")


def get_current_week_dates() -> tuple[str, str]:
    """获取本周的开始日期和结束日期 (YYYY-MM-DD)"""
    today = datetime.now()
    # 计算本周一
    start_of_week = today - timedelta(days=today.weekday())
    # 计算本周五
    end_of_week = start_of_week + timedelta(days=4)
    
    start_str = start_of_week.strftime("%Y-%m-%d")
    end_str = end_of_week.strftime("%Y-%m-%d")
    
    print(f"[DEBUG] Current week dates: {start_str} to {end_str}")
    return start_str, end_str


def save_raw_feishu_records_to_db(raw_records: List[Dict[str, Any]]):
    """将从飞书获取的原始记录数据保存到数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # 开始事务
        conn.execute("BEGIN TRANSACTION")
        
        # 先清空现有数据
        cursor.execute("DELETE FROM feishu_records")
        print("[DB] Cleared existing raw Feishu records from database.")
        
        # 插入新数据
        insert_count = 0
        for record in raw_records:
            record_id = record.get("record_id")
            fields = record.get("fields", {})
            created_time = record.get("created_time")
            last_modified_time = record.get("last_modified_time")
            
            # 将fields字典序列化为JSON字符串存储
            fields_json = json.dumps(fields, ensure_ascii=False)
            
            cursor.execute("""
                INSERT OR REPLACE INTO feishu_records 
                (record_id, fields, created_time, last_modified_time)
                VALUES (?, ?, ?, ?)
            """, (record_id, fields_json, created_time, last_modified_time))
            
            insert_count += 1
                
        # 提交事务
        conn.commit()
        print(f"[DB] Successfully saved {insert_count} raw Feishu records to database.")
        
    except Exception as e:
        # 回滚事务
        conn.rollback()
        print(f"[DB ERROR] Failed to save raw Feishu records to database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


def save_processed_tasks_to_db(processed_tasks: Dict[str, List[Dict[str, Any]]]):
    """将处理后的任务数据保存到数据库 (用于API查询)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # 开始事务
        conn.execute("BEGIN TRANSACTION")
        
        # 先清空现有数据
        cursor.execute("DELETE FROM tasks")
        print("[DB] Cleared existing processed tasks from database.")
        
        # 插入新数据
        insert_count = 0
        for weekday, tasks in processed_tasks.items():
            for task in tasks:
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks 
                    (record_id, task_name, assignee, status, date, start_date, end_date, weekday, priority, application_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task["record_id"],
                    task["task_name"],
                    task["assignee"],
                    task["status"],
                    task["date"],
                    task.get("start_date"),  # 新增字段
                    task.get("end_date"),    # 新增字段
                    weekday,
                    task.get("priority", ""),  # 新增字段
                    task.get("application_status", "")  # 新增字段
                ))
                insert_count += 1
                
        # 提交事务
        conn.commit()
        print(f"[DB] Successfully saved {insert_count} processed tasks to database.")
        
    except Exception as e:
        # 回滚事务
        conn.rollback()
        print(f"[DB ERROR] Failed to save processed tasks to database: {e}")
    finally:
        conn.close()


def get_tasks_from_db(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """从数据库获取任务，并按星期分组。
    
    Args:
        start_date (str, optional): 开始日期 (YYYY-MM-DD)。如果提供，必须同时提供 end_date。
        end_date (str, optional): 结束日期 (YYYY-MM-DD)。如果提供，必须同时提供 start_date。
        
    Returns:
        Dict[str, List[Dict[str, Any]]]: 按星期分组的任务数据。
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 初始化分组
    task_groups = {
        "monday": [],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "weekend": [],
        "unknown_date": []
    }
    
    try:
        if start_date and end_date:
            # 查询指定日期范围的任务
            print(f"[DB] Fetching tasks for date range: {start_date} to {end_date}")
            cursor.execute("""
                SELECT record_id, task_name, assignee, status, priority, application_status, date, start_date, end_date, weekday 
                FROM tasks 
                WHERE date BETWEEN ? AND ?
                ORDER BY date
            """, (start_date, end_date))
        else:
            # 如果没有提供日期范围，则查询所有数据
            print(f"[DB] Fetching all tasks from database")
            cursor.execute("""
                SELECT record_id, task_name, assignee, status, priority, application_status, date, start_date, end_date, weekday 
                FROM tasks
                ORDER BY date
            """)
        
        rows = cursor.fetchall()
        print(f"[DB] Fetched {len(rows)} rows from database.")
        
        for row in rows:
            record_id, task_name, assignee, status, priority, application_status, date, start_date, end_date, weekday = row
            task_item = {
                "record_id": record_id,
                "task_name": task_name,
                "assignee": assignee,
                "status": status,
                "priority": priority,
                "application_status": application_status,
                "date": date,
                "start_date": start_date,
                "end_date": end_date
            }
            # 确保weekday是有效的键
            if weekday in task_groups:
                task_groups[weekday].append(task_item)
            else:
                task_groups["unknown_date"].append(task_item) # 防御性编程
                
        total_tasks = sum(len(v) for v in task_groups.values())
        print(f"[DB] Successfully loaded {total_tasks} tasks from database.")
        
        # 打印每个分组的任务数量，方便调试
        for day, tasks in task_groups.items():
            if tasks:  # 只打印有任务的天
                print(f"[DB]   {day}: {len(tasks)} tasks")
        
    except Exception as e:
        print(f"[DB ERROR] Failed to load tasks from database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        
    return task_groups
