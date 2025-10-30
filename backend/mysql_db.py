import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

# 从环境变量获取数据库配置
DB_HOST = os.getenv("DB_HOST", "192.168.101.13")  # 默认改为正确的IP地址
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "Task_user_mysql")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1qaz2wsx")  # 默认改为正确的密码
DB_NAME = os.getenv("DB_NAME", "feishu_task_db")

# 创建数据库连接字符串
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建 SQLAlchemy 引擎和会话
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 定义任务表模型
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(String(255), nullable=False)
    task_name = Column(Text, nullable=False)
    assignee = Column(Text, nullable=False)
    status = Column(Text, nullable=False)  # 展示状态（进行中/已结束/优先级）
    priority = Column(Text)  # 原始优先级
    application_status = Column(Text)  # 申请状态
    date = Column(String(10), nullable=False)  # 任务在这一天展示 (YYYY-MM-DD)
    start_date = Column(String(10))  # 任务实际开始日期 (YYYY-MM-DD)
    end_date = Column(String(10))  # 任务实际结束日期 (YYYY-MM-DD)
    weekday = Column(String(20), nullable=False)  # monday, tuesday, etc.
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 添加唯一约束，防止重复插入同一天的同一条记录
    __table_args__ = (
        UniqueConstraint('record_id', 'date', name='uq_record_id_date'),
    )

# 定义飞书原始数据表模型
class FeishuRecord(Base):
    __tablename__ = "feishu_records"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(String(255), unique=True, nullable=False)
    fields = Column(Text, nullable=False)  # 存储序列化后的fields字典
    created_time = Column(Integer)  # 飞书记录创建时间戳
    last_modified_time = Column(Integer)  # 飞书记录最后修改时间戳
    last_synced = Column(DateTime, default=func.now(), onupdate=func.now())  # 本次同步时间

def init_db():
    """初始化数据库，创建任务表和视图"""
    Base.metadata.create_all(bind=engine)
    print(f"[DB] Database initialized. Tables 'tasks' and 'feishu_records' are ready.")

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_raw_feishu_records_to_db(raw_records: List[Dict[str, Any]]):
    """将从飞书获取的原始记录数据保存到数据库"""
    db = SessionLocal()
    try:
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
            
            # 将fields字典序列化为JSON字符串存储
            fields_json = json.dumps(fields, ensure_ascii=False)
            
            feishu_record = FeishuRecord(
                record_id=record_id,
                fields=fields_json,
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
        # 先清空现有数据
        db.query(Task).delete()
        print("[DB] Cleared existing processed tasks from database.")
        
        # 插入新数据
        insert_count = 0
        for weekday, tasks in processed_tasks.items():
            for task in tasks:
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
        query = db.query(Task)
        
        if start_date and end_date:
            # 查询指定日期范围的任务
            print(f"[DB] Fetching tasks for date range: {start_date} to {end_date}")
            query = query.filter(Task.date.between(start_date, end_date))
        else:
            # 如果没有提供日期范围，则查询所有数据
            print(f"[DB] Fetching all tasks from database")
            
        # 执行查询
        rows = query.order_by(Task.date).all()
        print(f"[DB] Fetched {len(rows)} rows from database.")
        
        for row in rows:
            task_item = {
                "record_id": row.record_id,
                "task_name": row.task_name,
                "assignee": row.assignee,
                "status": row.status,
                "priority": row.priority,
                "application_status": row.application_status,
                "date": row.date,
                "start_date": row.start_date,
                "end_date": row.end_date,
                "weekday": row.weekday
            }
            # 确保weekday是有效的键
            if row.weekday in task_groups:
                task_groups[row.weekday].append(task_item)
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