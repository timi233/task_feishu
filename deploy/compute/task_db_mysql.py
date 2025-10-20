import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# MySQL数据库连接相关导入
from sqlalchemy import create_engine, text, Column, Integer, String, Text, DateTime, BIGINT
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import JSON as MySQLJSON

# 获取数据库连接信息
DB_HOST = os.environ.get("DB_HOST", "192.168.101.13")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_USER = os.environ.get("DB_USER", "feishu_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "feishu_password")
DB_NAME = os.environ.get("DB_NAME", "feishu_task_db")

# 构建数据库连接URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建数据库引擎
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 定义ORM模型
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(String(255), nullable=False, unique=True)
    task_name = Column(Text, nullable=False)
    assignee = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    priority = Column(String(50), nullable=False)
    application_status = Column(String(255))
    date = Column(String(20), nullable=False)
    start_date = Column(String(20))
    end_date = Column(String(20))
    weekday = Column(String(20), nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FeishuRecord(Base):
    __tablename__ = "feishu_records"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(String(255), nullable=False, unique=True)
    fields = Column(MySQLJSON, nullable=False)
    created_time = Column(BIGINT)
    last_modified_time = Column(BIGINT)
    last_synced = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """初始化数据库，创建任务表和视图"""
    # 创建表
    Base.metadata.create_all(bind=engine)
    print("[DB] Database initialized. Tables 'tasks' and 'feishu_records' are ready.")


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
    db = SessionLocal()
    
    try:
        # 开始事务
        # 先清空现有数据
        db.query(FeishuRecord).delete()
        print("[DB] Cleared existing raw Feishu records from database.")
        
        # 插入新数据
        insert_count = 0
        for record in raw_records:
            record_id = record.get("record_id")
            fields = record.get("fields", {})
            created_time = record.get("created_time")
            last_modified_time = record.get("last_modified_time")
            
            # 创建FeishuRecord对象
            feishu_record = FeishuRecord(
                record_id=record_id,
                fields=fields,
                created_time=created_time,
                last_modified_time=last_modified_time
            )
            
            db.add(feishu_record)
            insert_count += 1
                
        # 提交事务
        db.commit()
        print(f"[DB] Successfully saved {insert_count} raw Feishu records to database.")
        
    except Exception as e:
        # 回滚事务
        db.rollback()
        print(f"[DB ERROR] Failed to save raw Feishu records to database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def save_processed_tasks_to_db(processed_tasks: Dict[str, List[Dict[str, Any]]]):
    """将处理后的任务数据保存到数据库 (用于API查询)"""
    db = SessionLocal()
    
    try:
        # 开始事务
        # 先清空现有数据
        db.query(Task).delete()
        print("[DB] Cleared existing processed tasks from database.")
        
        # 插入新数据
        insert_count = 0
        for weekday, tasks in processed_tasks.items():
            for task in tasks:
                # 创建Task对象
                task_record = Task(
                    record_id=task["record_id"],
                    task_name=task["task_name"],
                    assignee=task["assignee"],
                    status=task["status"],
                    date=task["date"],
                    start_date=task.get("start_date"),
                    end_date=task.get("end_date"),
                    weekday=weekday,
                    priority=task.get("priority", ""),
                    application_status=task.get("application_status", "")
                )
                
                db.add(task_record)
                insert_count += 1
                
        # 提交事务
        db.commit()
        print(f"[DB] Successfully saved {insert_count} processed tasks to database.")
        
    except Exception as e:
        # 回滚事务
        db.rollback()
        print(f"[DB ERROR] Failed to save processed tasks to database: {e}")
    finally:
        db.close()


def get_tasks_from_db(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """从数据库获取任务，并按星期分组。
    
    Args:
        start_date (str, optional): 开始日期 (YYYY-MM-DD)。如果提供，必须同时提供 end_date。
        end_date (str, optional): 结束日期 (YYYY-MM-DD)。如果提供，必须同时提供 start_date。
        
    Returns:
        Dict[str, List[Dict[str, Any]]]: 按星期分组的任务数据。
    """
    db = SessionLocal()
    
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
            tasks = db.query(Task).filter(Task.date.between(start_date, end_date)).order_by(Task.date).all()
        else:
            # 如果没有提供日期范围，则查询所有数据
            print(f"[DB] Fetching all tasks from database")
            tasks = db.query(Task).order_by(Task.date).all()
        
        print(f"[DB] Fetched {len(tasks)} rows from database.")
        
        for task in tasks:
            task_item = {
                "record_id": task.record_id,
                "task_name": task.task_name,
                "assignee": task.assignee,
                "status": task.status,
                "priority": task.priority,
                "application_status": task.application_status,
                "date": task.date,
                "start_date": task.start_date,
                "end_date": task.end_date,
                "weekday": task.weekday
            }
            # 确保weekday是有效的键
            if task.weekday in task_groups:
                task_groups[task.weekday].append(task_item)
            else:
                task_groups["unknown_date"].append(task_item)  # 防御性编程
                
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
        db.close()
        
    return task_groups