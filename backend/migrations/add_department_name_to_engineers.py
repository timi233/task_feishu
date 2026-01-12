#!/usr/bin/env python3
"""
添加department_name字段到engineers表

执行方式:
    python migrations/add_department_name_to_engineers.py

日期: 2025-10-31
阶段: Phase 4.4 - 派工系统缓存层改造
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from task_db import get_db_connection
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate():
    """添加department_name字段到engineers表"""
    logger.info("开始迁移：添加department_name字段...")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(engineers)")
        columns = [row[1] for row in cursor.fetchall()]

        if "department_name" not in columns:
            logger.info("  添加department_name字段...")
            cursor.execute("ALTER TABLE engineers ADD COLUMN department_name TEXT")
            logger.info("  ✅ department_name字段添加成功")
        else:
            logger.info("  ✅ department_name字段已存在，跳过")

        # 验证字段已添加
        cursor.execute("PRAGMA table_info(engineers)")
        columns_after = [row[1] for row in cursor.fetchall()]

        logger.info(f"\n当前engineers表字段: {', '.join(columns_after)}")

        conn.commit()

    logger.info("\n✅ 迁移完成!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Phase 4.4 - engineers表迁移")
    print("="*60 + "\n")

    try:
        migrate()
    except Exception as e:
        logger.exception(f"❌ 迁移失败: {e}")
        sys.exit(1)

    print("\n" + "="*60)
    print("迁移成功完成")
    print("="*60 + "\n")
