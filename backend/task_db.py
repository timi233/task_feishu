import sqlite3
from typing import Dict, List, Any, Optional
import os
from datetime import datetime, timedelta
import logging
from contextlib import contextmanager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库文件路径
# 优先使用环境变量，本地开发时使用相对路径，Docker中使用/app/db/tasks.db
DB_FILE = os.getenv("DB_FILE", "./data/db/tasks.db")


@contextmanager
def get_db_connection():
    """数据库连接上下文管理器，自动处理提交/回滚"""
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row  # 返回字典式行
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    """初始化数据库，创建任务表"""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

    with get_db_connection() as conn:
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

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_weekday ON tasks (weekday)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_date ON tasks (date)")
    logger.info("Database initialized. Table 'tasks' is ready.")


def get_week_range(date=None, week_start="sunday") -> tuple[str, str]:
    """获取一周的开始和结束日期（统一日期计算逻辑）

    Args:
        date: 基准日期，默认今天
        week_start: "sunday" 或 "monday"，表示一周从周日还是周一开始

    Returns:
        (start_date_str, end_date_str) 格式 YYYY-MM-DD
    """
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")

    # 计算本周开始日期
    if week_start == "sunday":
        # 周日为一周的开始
        start_of_week = date - timedelta(days=(date.weekday() + 1) % 7)
    else:  # monday
        # 周一为一周的开始
        start_of_week = date - timedelta(days=date.weekday())

    # 一周结束日期（开始日期+6天）
    end_of_week = start_of_week + timedelta(days=6)

    start_str = start_of_week.strftime("%Y-%m-%d")
    end_str = end_of_week.strftime("%Y-%m-%d")

    logger.debug("Week range (%s start): %s to %s", week_start, start_str, end_str)
    return start_str, end_str


def get_month_range(date=None) -> tuple[str, str]:
    """获取一个月的开始和结束日期

    Args:
        date: 基准日期，默认今天

    Returns:
        (start_date_str, end_date_str) 格式 YYYY-MM-DD
    """
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")

    start_of_month = date.replace(day=1)

    if date.month == 12:
        end_of_month = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = date.replace(month=date.month + 1, day=1) - timedelta(days=1)

    start_str = start_of_month.strftime("%Y-%m-%d")
    end_str = end_of_month.strftime("%Y-%m-%d")

    logger.debug("Month range: %s to %s", start_str, end_str)
    return start_str, end_str


def get_current_week_dates() -> tuple[str, str]:
    """获取本周的开始日期和结束日期 (YYYY-MM-DD)

    保留此函数用于向后兼容，默认使用周日作为一周开始
    """
    return get_week_range(week_start="sunday")



def save_processed_tasks_to_db(processed_tasks: Dict[str, List[Dict[str, Any]]]):
    """将处理后的任务数据保存到数据库 (用于API查询)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        conn.execute("BEGIN TRANSACTION")

        # 先清空现有数据
        cursor.execute("DELETE FROM tasks")
        logger.info("Cleared existing processed tasks from database.")

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
                    task.get("start_date"),
                    task.get("end_date"),
                    weekday,
                    task.get("priority", ""),
                    task.get("application_status", "")
                ))
                insert_count += 1

        logger.info("Successfully saved %d processed tasks to database.", insert_count)


def get_tasks_from_db(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """从数据库获取任务，并按星期分组。
    
    Args:
        start_date (str, optional): 开始日期 (YYYY-MM-DD)。如果提供，必须同时提供 end_date。
        end_date (str, optional): 结束日期 (YYYY-MM-DD)。如果提供，必须同时提供 start_date。
        
    Returns:
        Dict[str, List[Dict[str, Any]]]: 按星期分组的任务数据。
    """
    task_groups = {
        "monday": [],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "weekend": [],
        "unknown_date": []
    }

    with get_db_connection() as conn:
        cursor = conn.cursor()

        if start_date and end_date:
            logger.info("Fetching tasks for date range: %s to %s", start_date, end_date)
            cursor.execute("""
                SELECT record_id, task_name, assignee, status, priority, application_status, date, start_date, end_date, weekday 
                FROM tasks 
                WHERE date BETWEEN ? AND ?
                ORDER BY date
            """, (start_date, end_date))
        else:
            logger.info("Fetching all tasks from database")
            cursor.execute("""
                SELECT record_id, task_name, assignee, status, priority, application_status, date, start_date, end_date, weekday 
                FROM tasks
                ORDER BY date
            """)

        rows = cursor.fetchall()
        logger.info("Fetched %d rows from database.", len(rows))

        for row in rows:
            task_item = {
                "record_id": row["record_id"],
                "task_name": row["task_name"],
                "assignee": row["assignee"],
                "status": row["status"],
                "priority": row["priority"],
                "application_status": row["application_status"],
                "date": row["date"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "weekday": row["weekday"]
            }

            weekday = row["weekday"]
            if weekday in task_groups:
                task_groups[weekday].append(task_item)
            else:
                task_groups["unknown_date"].append(task_item)

    total_tasks = sum(len(v) for v in task_groups.values())
    logger.info("Successfully loaded %d tasks from database.", total_tasks)

    for day, tasks in task_groups.items():
        if tasks:
            logger.debug("%s: %d tasks", day, len(tasks))

    return task_groups


def get_task_count() -> int:
    """返回 tasks 表中的任务数量，便于健康检查和测试"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM tasks")
        row = cursor.fetchone()

    count = row["count"] if isinstance(row, sqlite3.Row) else row[0]
    logger.debug("Current task count: %d", count)
    return count


def get_tasks_by_record_id(record_id: str) -> List[Dict[str, Any]]:
    """根据 record_id 获取所有相关任务记录"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT record_id, task_name, assignee, status, priority, application_status, date, start_date, end_date, weekday
            FROM tasks
            WHERE record_id = ?
            ORDER BY date
            """,
            (record_id,)
        )
        rows = cursor.fetchall()

    tasks = [
        {
            "record_id": row["record_id"],
            "task_name": row["task_name"],
            "assignee": row["assignee"],
            "status": row["status"],
            "priority": row["priority"],
            "application_status": row["application_status"],
            "date": row["date"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "weekday": row["weekday"]
        }
        for row in rows
    ]

    logger.debug("Fetched %d tasks for record_id %s", len(tasks), record_id)
    return tasks
