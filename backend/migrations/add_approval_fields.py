#!/usr/bin/env python3
"""
数据库迁移脚本: 添加审批字段

功能:
- 向tasks表添加approval_instance_code和approval_status字段
- 支持SQLite和MySQL
- 幂等性: 重复执行不会报错

使用方法:
  python backend/migrations/add_approval_fields.py
"""

import sqlite3
import os
import sys
from contextlib import contextmanager

# 数据库文件路径
DB_FILE = os.getenv("DB_FILE", "./data/db/tasks.db")


@contextmanager
def get_db_connection():
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        conn.close()


def check_column_exists(cursor, table_name: str, column_name: str) -> bool:
    """检查列是否存在(SQLite)"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def upgrade_sqlite():
    """SQLite数据库迁移"""
    print("Starting SQLite migration...")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 检查tasks表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='tasks'
        """)
        if not cursor.fetchone():
            print("Error: tasks table does not exist. Please run init_db() first.")
            sys.exit(1)

        # 添加approval_instance_code字段
        if not check_column_exists(cursor, "tasks", "approval_instance_code"):
            print("Adding column: approval_instance_code")
            cursor.execute("ALTER TABLE tasks ADD COLUMN approval_instance_code TEXT")
        else:
            print("Column approval_instance_code already exists, skipping...")

        # 添加approval_status字段
        if not check_column_exists(cursor, "tasks", "approval_status"):
            print("Adding column: approval_status")
            cursor.execute("ALTER TABLE tasks ADD COLUMN approval_status TEXT")
        else:
            print("Column approval_status already exists, skipping...")

        # 创建索引
        print("Creating index: idx_tasks_approval_instance")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_approval_instance
            ON tasks(approval_instance_code)
        """)

        # 创建复合索引
        print("Creating index: idx_tasks_assignee_approval_status")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_assignee_approval_status
            ON tasks(assignee, approval_status)
        """)

        print("SQLite migration completed successfully!")


def upgrade_mysql():
    """MySQL数据库迁移(需要pymysql)"""
    print("Starting MySQL migration...")

    try:
        import pymysql
    except ImportError:
        print("Error: pymysql not installed. Run: pip install pymysql")
        sys.exit(1)

    # 从环境变量读取MySQL配置
    mysql_host = os.getenv("MYSQL_HOST", "localhost")
    mysql_port = int(os.getenv("MYSQL_PORT", 3306))
    mysql_user = os.getenv("MYSQL_USER", "root")
    mysql_password = os.getenv("MYSQL_PASSWORD", "")
    mysql_database = os.getenv("MYSQL_DATABASE", "feishu_tasks")

    conn = pymysql.connect(
        host=mysql_host,
        port=mysql_port,
        user=mysql_user,
        password=mysql_password,
        database=mysql_database
    )

    try:
        cursor = conn.cursor()

        # 检查tasks表是否存在
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = 'tasks'
        """, (mysql_database,))
        if cursor.fetchone()[0] == 0:
            print("Error: tasks table does not exist. Please run init_db() first.")
            sys.exit(1)

        # 检查列是否存在
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'tasks'
        """, (mysql_database,))
        existing_columns = [row[0] for row in cursor.fetchall()]

        # 添加审批字段
        if "approval_instance_code" not in existing_columns:
            print("Adding column: approval_instance_code")
            cursor.execute("""
                ALTER TABLE tasks
                ADD COLUMN approval_instance_code VARCHAR(255)
            """)
        else:
            print("Column approval_instance_code already exists, skipping...")

        if "approval_status" not in existing_columns:
            print("Adding column: approval_status")
            cursor.execute("""
                ALTER TABLE tasks
                ADD COLUMN approval_status VARCHAR(50)
            """)
        else:
            print("Column approval_status already exists, skipping...")

        # 创建索引
        print("Creating index: idx_tasks_approval_instance")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_approval_instance
            ON tasks(approval_instance_code)
        """)

        print("Creating index: idx_tasks_assignee_approval_status")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_assignee_approval_status
            ON tasks(assignee, approval_status)
        """)

        conn.commit()
        print("MySQL migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


def main():
    """主函数: 根据数据库类型选择迁移方法"""
    db_type = os.getenv("DB_TYPE", "sqlite")

    print(f"Database type: {db_type}")
    print(f"Database file/connection: {DB_FILE if db_type == 'sqlite' else 'MySQL'}")
    print("-" * 60)

    if db_type == "mysql":
        upgrade_mysql()
    else:  # 默认SQLite
        upgrade_sqlite()

    print("-" * 60)
    print("Migration complete. You can now use the approval management features.")


if __name__ == "__main__":
    main()
