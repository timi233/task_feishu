#!/usr/bin/env python3
"""
数据库迁移: 添加engineers表

用途:
    为已有数据库添加engineers表,用于存储从飞书同步的工程师信息

运行方式:
    python migrations/add_engineers_table.py

依赖:
    - task_db.py (获取数据库连接)
"""

import sys
import os
import logging

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_db import get_db_connection, DB_FILE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_table_exists(cursor, table_name: str) -> bool:
    """检查表是否已存在"""
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None


def migrate():
    """执行数据库迁移"""
    logger.info(f"Starting migration: add_engineers_table")
    logger.info(f"Database file: {DB_FILE}")

    if not os.path.exists(DB_FILE):
        logger.error(f"Database file not found: {DB_FILE}")
        logger.error("Please run init_db() first to create the database")
        return False

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 检查engineers表是否已存在
            if check_table_exists(cursor, "engineers"):
                logger.warning("Table 'engineers' already exists, skipping creation")
                return True

            logger.info("Creating 'engineers' table...")

            # 创建工程师表
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

            # 创建索引
            logger.info("Creating indexes on 'engineers' table...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_engineers_name ON engineers (name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_engineers_status ON engineers (status)")

            logger.info("✅ Migration completed successfully")
            logger.info("Table 'engineers' created with indexes")

            # 显示表结构
            cursor.execute("PRAGMA table_info(engineers)")
            columns = cursor.fetchall()
            logger.info("Table structure:")
            for col in columns:
                logger.info(f"  - {col[1]} ({col[2]})")

            return True

    except Exception as e:
        logger.exception(f"❌ Migration failed: {e}")
        return False


def rollback():
    """回滚迁移 (删除engineers表)"""
    logger.warning("Rolling back migration: dropping 'engineers' table")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if not check_table_exists(cursor, "engineers"):
                logger.info("Table 'engineers' does not exist, nothing to rollback")
                return True

            cursor.execute("DROP TABLE IF EXISTS engineers")
            logger.info("✅ Rollback completed: 'engineers' table dropped")
            return True

    except Exception as e:
        logger.exception(f"❌ Rollback failed: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate database: add engineers table")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        success = rollback()
    else:
        success = migrate()

    sys.exit(0 if success else 1)
