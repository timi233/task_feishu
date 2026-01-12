#!/usr/bin/env python3
"""
数据库迁移: 添加creator字段到tasks表

用途:
    为tasks表添加creator_id和creator_name字段，用于记录任务发起人

运行方式:
    python migrations/add_creator_fields_to_tasks.py

日期: 2025-11-03
阶段: Phase 4.6 - 权限管理功能
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


def check_column_exists(cursor, table_name: str, column_name: str) -> bool:
    """检查列是否已存在"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate():
    """执行数据库迁移"""
    logger.info("="*60)
    logger.info("开始迁移: 添加creator字段到tasks表")
    logger.info("="*60)
    logger.info(f"数据库文件: {DB_FILE}")

    if not os.path.exists(DB_FILE):
        logger.error(f"❌ 数据库文件不存在: {DB_FILE}")
        logger.error("请先运行init_db()创建数据库")
        return False

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 检查creator_id字段
            if check_column_exists(cursor, "tasks", "creator_id"):
                logger.warning("⚠️ creator_id字段已存在，跳过添加")
            else:
                logger.info("📝 添加creator_id字段...")
                cursor.execute("ALTER TABLE tasks ADD COLUMN creator_id TEXT")
                logger.info("✅ creator_id字段添加成功")

            # 检查creator_name字段
            if check_column_exists(cursor, "tasks", "creator_name"):
                logger.warning("⚠️ creator_name字段已存在，跳过添加")
            else:
                logger.info("📝 添加creator_name字段...")
                cursor.execute("ALTER TABLE tasks ADD COLUMN creator_name TEXT")
                logger.info("✅ creator_name字段添加成功")

            # 创建索引
            logger.info("📝 创建creator_id索引...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_creator
                ON tasks(creator_id)
            """)
            logger.info("✅ 索引创建成功")

            # 验证字段已添加
            cursor.execute("PRAGMA table_info(tasks)")
            columns = cursor.fetchall()

            logger.info("")
            logger.info("="*60)
            logger.info("✅ 迁移完成!")
            logger.info("="*60)
            logger.info("")
            logger.info("当前tasks表字段:")
            for col in columns:
                field_name = col[1]
                field_type = col[2]
                if field_name in ['creator_id', 'creator_name']:
                    logger.info(f"  ✨ {field_name} ({field_type}) [NEW]")
                else:
                    logger.info(f"     {field_name} ({field_type})")

            conn.commit()
            return True

    except Exception as e:
        logger.exception(f"❌ 迁移失败: {e}")
        return False


def rollback():
    """回滚迁移 (SQLite不支持DROP COLUMN，需要重建表)"""
    logger.warning("⚠️ SQLite不支持直接删除列")
    logger.warning("如需回滚，请手动备份数据并重建表")
    return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="迁移: 添加creator字段到tasks表")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.rollback:
        success = rollback()
    else:
        success = migrate()

    sys.exit(0 if success else 1)
