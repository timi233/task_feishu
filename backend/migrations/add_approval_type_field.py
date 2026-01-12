#!/usr/bin/env python3
"""
数据库迁移脚本: 添加审批类型字段

功能:
- 向tasks表添加approval_type字段,用于区分不同工单类型
- 支持SQLite和MySQL
- 幂等性: 重复执行不会报错

使用方法:
  python backend/migrations/add_approval_type_field.py
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

        # 添加approval_type字段
        if not check_column_exists(cursor, "tasks", "approval_type"):
            print("Adding column: approval_type")
            cursor.execute("""
                ALTER TABLE tasks
                ADD COLUMN approval_type VARCHAR(50) DEFAULT 'daily_work'
            """)
            print("  Column added successfully")
            print("  Default value: 'daily_work' (公司日常工单)")
        else:
            print("Column approval_type already exists, skipping...")

        # 创建索引以优化按工单类型查询
        print("Creating index: idx_tasks_approval_type")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_approval_type
            ON tasks(approval_type)
        """)

        # 创建复合索引(approval_type + approval_status)
        print("Creating composite index: idx_tasks_approval_type_status")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_approval_type_status
            ON tasks(approval_type, approval_status)
        """)

        # 数据迁移: 将所有现有记录的approval_type设为daily_work
        cursor.execute("""
            UPDATE tasks
            SET approval_type = 'daily_work'
            WHERE approval_type IS NULL
        """)
        updated_count = cursor.rowcount
        if updated_count > 0:
            print(f"  Updated {updated_count} existing records to approval_type='daily_work'")

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

        # 添加approval_type字段
        if "approval_type" not in existing_columns:
            print("Adding column: approval_type")
            cursor.execute("""
                ALTER TABLE tasks
                ADD COLUMN approval_type VARCHAR(50) DEFAULT 'daily_work'
            """)
            print("  Column added successfully")
        else:
            print("Column approval_type already exists, skipping...")

        # 创建索引
        print("Creating index: idx_tasks_approval_type")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_approval_type
            ON tasks(approval_type)
        """)

        print("Creating composite index: idx_tasks_approval_type_status")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_approval_type_status
            ON tasks(approval_type, approval_status)
        """)

        # 数据迁移
        cursor.execute("""
            UPDATE tasks
            SET approval_type = 'daily_work'
            WHERE approval_type IS NULL
        """)
        updated_count = cursor.rowcount
        if updated_count > 0:
            print(f"  Updated {updated_count} existing records to approval_type='daily_work'")

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
    print("Migration complete.")
    print("\n工单类型说明:")
    print("  - daily_work: 公司日常工单(默认)")
    print("  - eisoo_vendor: 爱数原厂派单")
    print("\n所有现有记录已设置为'daily_work'以保持向后兼容。")


if __name__ == "__main__":
    main()
