import sqlite3
from typing import Dict, List, Any, Optional
import os
from datetime import datetime, timedelta
import logging
from contextlib import contextmanager

# 日志由main.py统一配置
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

        # 创建工程师表 (存储从飞书同步的人员信息)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engineers (
                user_id TEXT PRIMARY KEY,          -- 飞书user_id
                name TEXT NOT NULL,                 -- 工程师姓名
                department_ids TEXT,                -- 部门ID列表(JSON数组)
                mobile TEXT,                        -- 手机号
                email TEXT,                         -- 邮箱
                status INTEGER DEFAULT 1,           -- 状态: 1=在职, 0=离职
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)

        # 创建工程师表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_engineers_name ON engineers (name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_engineers_status ON engineers (status)")

    logger.info("Database initialized. Tables 'tasks' and 'engineers' are ready.")


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
    """将处理后的任务数据保存到数据库 (使用UPSERT避免并发问题)

    🔒 安全修复: 使用INSERT OR REPLACE替代DELETE+INSERT，避免并发数据丢失
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # ❌ 移除全量删除 - 避免并发问题
        # cursor.execute("DELETE FROM tasks")

        # ✓ 使用UPSERT逻辑: INSERT OR REPLACE
        # 依赖唯一约束 UNIQUE(record_id, date)
        upsert_count = 0
        for weekday, tasks in processed_tasks.items():
            for task in tasks:
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks
                    (record_id, task_name, assignee, status, date, start_date, end_date,
                     weekday, priority, application_status, approval_instance_code,
                     approval_status, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
                    task.get("application_status", ""),
                    task.get("approval_instance_code"),
                    task.get("approval_status")
                ))
                upsert_count += 1

        logger.info("Successfully upserted %d processed tasks to database.", upsert_count)


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


# ===== 工程师数据管理函数 =====

def save_engineers_to_db(engineers: List[Dict[str, Any]]) -> int:
    """
    保存工程师列表到数据库 (使用REPLACE策略更新)

    Args:
        engineers: 工程师列表,每个元素包含 user_id, name, department_ids, mobile, email, status

    Returns:
        int: 成功保存的工程师数量
    """
    if not engineers:
        logger.warning("No engineers to save")
        return 0

    with get_db_connection() as conn:
        cursor = conn.cursor()

        saved_count = 0
        for engineer in engineers:
            try:
                # 使用REPLACE策略: 如果user_id已存在则更新,否则插入
                cursor.execute("""
                    REPLACE INTO engineers (user_id, name, department_ids, mobile, email, status, synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    engineer.get("user_id"),
                    engineer.get("name"),
                    engineer.get("department_ids"),  # JSON字符串
                    engineer.get("mobile"),
                    engineer.get("email"),
                    engineer.get("status", 1)  # 默认在职
                ))
                saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save engineer {engineer.get('name', 'unknown')}: {e}")
                continue

    logger.info(f"Successfully saved {saved_count}/{len(engineers)} engineers to database")
    return saved_count


def get_engineers_from_db(status: Optional[int] = 1) -> List[Dict[str, Any]]:
    """
    从数据库获取工程师列表

    Args:
        status: 筛选状态 (1=在职, 0=离职, None=全部)

    Returns:
        List[Dict]: 工程师列表,每个元素包含 user_id, name, department_ids, mobile, email, status
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if status is not None:
            cursor.execute("""
                SELECT user_id, name, department_ids, mobile, email, status, synced_at
                FROM engineers
                WHERE status = ?
                ORDER BY name
            """, (status,))
        else:
            cursor.execute("""
                SELECT user_id, name, department_ids, mobile, email, status, synced_at
                FROM engineers
                ORDER BY name
            """)

        rows = cursor.fetchall()

    engineers = [
        {
            "user_id": row["user_id"],
            "name": row["name"],
            "department_ids": row["department_ids"],
            "mobile": row["mobile"],
            "email": row["email"],
            "status": row["status"],
            "synced_at": row["synced_at"]
        }
        for row in rows
    ]

    logger.debug(f"Fetched {len(engineers)} engineers from database (status={status})")
    return engineers
