#!/usr/bin/env python3
"""
数据库迁移: 创建角色管理表

用途:
    创建roles表（角色定义）和user_roles表（用户角色关联）

运行方式:
    python migrations/create_role_tables.py

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


def check_table_exists(cursor, table_name: str) -> bool:
    """检查表是否已存在"""
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None


def migrate():
    """执行数据库迁移"""
    logger.info("="*60)
    logger.info("开始迁移: 创建角色管理表")
    logger.info("="*60)
    logger.info(f"数据库文件: {DB_FILE}")

    if not os.path.exists(DB_FILE):
        logger.error(f"❌ 数据库文件不存在: {DB_FILE}")
        logger.error("请先运行init_db()创建数据库")
        return False

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. 创建roles表
            if check_table_exists(cursor, "roles"):
                logger.warning("⚠️ roles表已存在，跳过创建")
            else:
                logger.info("📝 创建roles表...")
                cursor.execute("""
                    CREATE TABLE roles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role_key TEXT UNIQUE NOT NULL,           -- 角色标识: 'system_admin', 'manager', 'regular_user'
                        role_name TEXT NOT NULL,                  -- 角色名称: '系统管理员', '管理者', '普通人员'
                        description TEXT,                         -- 角色描述
                        permissions TEXT,                         -- JSON数组: ["task:create", "task:read", ...]
                        data_scope TEXT DEFAULT 'all',            -- 数据范围: 'all'(全部), 'self'(仅自己相关)
                        is_system BOOLEAN DEFAULT 0,              -- 是否系统内置角色（不可删除）
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 创建索引
                cursor.execute("CREATE INDEX idx_roles_key ON roles(role_key)")

                logger.info("✅ roles表创建成功")

            # 2. 创建user_roles表
            if check_table_exists(cursor, "user_roles"):
                logger.warning("⚠️ user_roles表已存在，跳过创建")
            else:
                logger.info("📝 创建user_roles表...")
                cursor.execute("""
                    CREATE TABLE user_roles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,                    -- 飞书user_id
                        role_id INTEGER NOT NULL,                 -- 角色ID
                        assigned_by TEXT,                         -- 分配人user_id
                        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                        UNIQUE(user_id, role_id)                  -- 一个用户一个角色类型只能分配一次
                    )
                """)

                # 创建索引
                cursor.execute("CREATE INDEX idx_user_roles_user ON user_roles(user_id)")
                cursor.execute("CREATE INDEX idx_user_roles_role ON user_roles(role_id)")

                logger.info("✅ user_roles表创建成功")

            # 3. 显示表结构
            logger.info("")
            logger.info("="*60)
            logger.info("✅ 迁移完成!")
            logger.info("="*60)
            logger.info("")

            # roles表结构
            logger.info("roles表结构:")
            cursor.execute("PRAGMA table_info(roles)")
            for col in cursor.fetchall():
                logger.info(f"  - {col[1]} ({col[2]})")

            logger.info("")

            # user_roles表结构
            logger.info("user_roles表结构:")
            cursor.execute("PRAGMA table_info(user_roles)")
            for col in cursor.fetchall():
                logger.info(f"  - {col[1]} ({col[2]})")

            conn.commit()
            return True

    except Exception as e:
        logger.exception(f"❌ 迁移失败: {e}")
        return False


def rollback():
    """回滚迁移 (删除roles和user_roles表)"""
    logger.warning("⚠️ 开始回滚: 删除角色管理表")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if check_table_exists(cursor, "user_roles"):
                cursor.execute("DROP TABLE user_roles")
                logger.info("✅ user_roles表已删除")

            if check_table_exists(cursor, "roles"):
                cursor.execute("DROP TABLE roles")
                logger.info("✅ roles表已删除")

            logger.info("✅ 回滚完成")
            return True

    except Exception as e:
        logger.exception(f"❌ 回滚失败: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="迁移: 创建角色管理表")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.rollback:
        success = rollback()
    else:
        success = migrate()

    sys.exit(0 if success else 1)
