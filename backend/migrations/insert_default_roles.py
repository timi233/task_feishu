#!/usr/bin/env python3
"""
数据库迁移: 插入默认角色数据

用途:
    为roles表插入三个默认角色：系统管理员、管理者、普通人员

运行方式:
    python migrations/insert_default_roles.py

日期: 2025-11-03
阶段: Phase 4.6 - 权限管理功能
"""

import sys
import os
import logging
import json

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_db import get_db_connection, DB_FILE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 默认角色配置
DEFAULT_ROLES = [
    {
        "role_key": "system_admin",
        "role_name": "系统管理员",
        "description": "可以管理用户权限、查看和操作所有数据",
        "permissions": json.dumps([
            "user:read", "user:write", "user:delete",
            "role:assign", "role:revoke",
            "task:read", "task:create", "task:update", "task:delete",
            "approval:read", "approval:create", "approval:update", "approval:delete"
        ]),
        "data_scope": "all",
        "is_system": 1
    },
    {
        "role_key": "manager",
        "role_name": "管理者",
        "description": "可以查看和操作所有派工数据，但不能管理用户权限",
        "permissions": json.dumps([
            "task:read", "task:create", "task:update", "task:delete",
            "approval:read", "approval:create", "approval:update", "approval:delete"
        ]),
        "data_scope": "all",
        "is_system": 1
    },
    {
        "role_key": "regular_user",
        "role_name": "普通人员",
        "description": "只能查看和操作与自己相关的派工数据（作为指派人或发起人）",
        "permissions": json.dumps([
            "task:read", "task:update",
            "approval:read", "approval:update"
        ]),
        "data_scope": "self",
        "is_system": 1
    }
]


def check_role_exists(cursor, role_key: str) -> bool:
    """检查角色是否已存在"""
    cursor.execute("SELECT id FROM roles WHERE role_key = ?", (role_key,))
    return cursor.fetchone() is not None


def migrate():
    """执行数据库迁移"""
    logger.info("="*60)
    logger.info("开始迁移: 插入默认角色数据")
    logger.info("="*60)
    logger.info(f"数据库文件: {DB_FILE}")

    if not os.path.exists(DB_FILE):
        logger.error(f"❌ 数据库文件不存在: {DB_FILE}")
        logger.error("请先运行create_role_tables.py创建角色表")
        return False

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            inserted_count = 0
            skipped_count = 0

            for role in DEFAULT_ROLES:
                if check_role_exists(cursor, role["role_key"]):
                    logger.warning(f"⚠️ 角色 {role['role_name']} ({role['role_key']}) 已存在，跳过")
                    skipped_count += 1
                    continue

                logger.info(f"📝 插入角色: {role['role_name']} ({role['role_key']})...")
                cursor.execute("""
                    INSERT INTO roles (role_key, role_name, description, permissions, data_scope, is_system)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    role["role_key"],
                    role["role_name"],
                    role["description"],
                    role["permissions"],
                    role["data_scope"],
                    role["is_system"]
                ))
                inserted_count += 1
                logger.info(f"  ✅ 插入成功")

            # 显示所有角色
            logger.info("")
            logger.info("="*60)
            logger.info("✅ 迁移完成!")
            logger.info("="*60)
            logger.info(f"插入: {inserted_count} 条, 跳过: {skipped_count} 条")
            logger.info("")

            logger.info("当前角色列表:")
            cursor.execute("""
                SELECT role_key, role_name, data_scope,
                       (SELECT COUNT(*) FROM user_roles WHERE role_id = roles.id) as user_count
                FROM roles
                ORDER BY id
            """)
            roles = cursor.fetchall()

            for role in roles:
                role_key, role_name, data_scope, user_count = role
                logger.info(f"  • {role_name} ({role_key})")
                logger.info(f"    数据范围: {data_scope} | 用户数: {user_count}")

            conn.commit()
            return True

    except Exception as e:
        logger.exception(f"❌ 迁移失败: {e}")
        return False


def rollback():
    """回滚迁移 (删除所有系统内置角色)"""
    logger.warning("⚠️ 开始回滚: 删除默认角色数据")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 删除系统内置角色
            cursor.execute("DELETE FROM roles WHERE is_system = 1")
            deleted_count = cursor.rowcount

            logger.info(f"✅ 已删除 {deleted_count} 个系统角色")
            logger.info("✅ 回滚完成")

            conn.commit()
            return True

    except Exception as e:
        logger.exception(f"❌ 回滚失败: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="迁移: 插入默认角色数据")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.rollback:
        success = rollback()
    else:
        success = migrate()

    sys.exit(0 if success else 1)
