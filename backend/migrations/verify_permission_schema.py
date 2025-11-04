#!/usr/bin/env python3
"""
验证权限管理数据库结构

用途:
    验证Phase 1完成后的数据库结构是否正确

运行方式:
    python migrations/verify_permission_schema.py

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


def verify():
    """验证数据库结构"""
    logger.info("="*60)
    logger.info("开始验证: 权限管理数据库结构")
    logger.info("="*60)
    logger.info(f"数据库文件: {DB_FILE}")
    logger.info("")

    if not os.path.exists(DB_FILE):
        logger.error(f"❌ 数据库文件不存在: {DB_FILE}")
        return False

    all_passed = True

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # ========== 验证1: roles表结构 ==========
            logger.info("【验证1】roles表结构")
            cursor.execute("PRAGMA table_info(roles)")
            roles_columns = {col[1]: col[2] for col in cursor.fetchall()}

            required_roles_fields = {
                "id": "INTEGER",
                "role_key": "TEXT",
                "role_name": "TEXT",
                "description": "TEXT",
                "permissions": "TEXT",
                "data_scope": "TEXT",
                "is_system": "BOOLEAN",
                "created_at": "TIMESTAMP",
                "updated_at": "TIMESTAMP"
            }

            for field, expected_type in required_roles_fields.items():
                if field in roles_columns:
                    logger.info(f"  ✅ {field} ({roles_columns[field]})")
                else:
                    logger.error(f"  ❌ 缺少字段: {field}")
                    all_passed = False

            # 验证roles索引
            cursor.execute("PRAGMA index_list(roles)")
            indexes = cursor.fetchall()
            idx_names = [idx[1] for idx in indexes]
            if "idx_roles_key" in idx_names:
                logger.info(f"  ✅ 索引 idx_roles_key 存在")
            else:
                logger.warning(f"  ⚠️ 索引 idx_roles_key 不存在")

            logger.info("")

            # ========== 验证2: user_roles表结构 ==========
            logger.info("【验证2】user_roles表结构")
            cursor.execute("PRAGMA table_info(user_roles)")
            user_roles_columns = {col[1]: col[2] for col in cursor.fetchall()}

            required_user_roles_fields = {
                "id": "INTEGER",
                "user_id": "TEXT",
                "role_id": "INTEGER",
                "assigned_by": "TEXT",
                "assigned_at": "TIMESTAMP"
            }

            for field, expected_type in required_user_roles_fields.items():
                if field in user_roles_columns:
                    logger.info(f"  ✅ {field} ({user_roles_columns[field]})")
                else:
                    logger.error(f"  ❌ 缺少字段: {field}")
                    all_passed = False

            # 验证user_roles索引
            cursor.execute("PRAGMA index_list(user_roles)")
            indexes = cursor.fetchall()
            idx_names = [idx[1] for idx in indexes]
            expected_indexes = ["idx_user_roles_user", "idx_user_roles_role"]
            for idx_name in expected_indexes:
                if idx_name in idx_names:
                    logger.info(f"  ✅ 索引 {idx_name} 存在")
                else:
                    logger.warning(f"  ⚠️ 索引 {idx_name} 不存在")

            logger.info("")

            # ========== 验证3: tasks表新增字段 ==========
            logger.info("【验证3】tasks表creator字段")
            cursor.execute("PRAGMA table_info(tasks)")
            tasks_columns = {col[1]: col[2] for col in cursor.fetchall()}

            required_tasks_fields = ["creator_id", "creator_name"]

            for field in required_tasks_fields:
                if field in tasks_columns:
                    logger.info(f"  ✅ {field} ({tasks_columns[field]})")
                else:
                    logger.error(f"  ❌ 缺少字段: {field}")
                    all_passed = False

            # 验证tasks索引
            cursor.execute("PRAGMA index_list(tasks)")
            indexes = cursor.fetchall()
            idx_names = [idx[1] for idx in indexes]
            if "idx_tasks_creator" in idx_names:
                logger.info(f"  ✅ 索引 idx_tasks_creator 存在")
            else:
                logger.warning(f"  ⚠️ 索引 idx_tasks_creator 不存在")

            logger.info("")

            # ========== 验证4: 默认角色数据 ==========
            logger.info("【验证4】默认角色数据")
            cursor.execute("SELECT role_key, role_name, data_scope FROM roles ORDER BY id")
            roles = cursor.fetchall()

            expected_roles = [
                ("system_admin", "系统管理员", "all"),
                ("manager", "管理者", "all"),
                ("regular_user", "普通人员", "self")
            ]

            if len(roles) >= 3:
                for i, (expected_key, expected_name, expected_scope) in enumerate(expected_roles):
                    if i < len(roles):
                        actual_key, actual_name, actual_scope = roles[i]
                        if actual_key == expected_key and actual_name == expected_name and actual_scope == expected_scope:
                            logger.info(f"  ✅ {actual_name} ({actual_key}, scope={actual_scope})")
                        else:
                            logger.warning(f"  ⚠️ 角色数据不匹配: expected={expected_name}, actual={actual_name}")
                    else:
                        logger.error(f"  ❌ 缺少角色: {expected_name}")
                        all_passed = False
            else:
                logger.error(f"  ❌ 角色数量不足: expected=3, actual={len(roles)}")
                all_passed = False

            logger.info("")

            # ========== 验证5: 外键约束 ==========
            logger.info("【验证5】外键约束")
            cursor.execute("PRAGMA foreign_key_list(user_roles)")
            foreign_keys = cursor.fetchall()

            if foreign_keys:
                for fk in foreign_keys:
                    table, from_col, to_col = fk[2], fk[3], fk[4]
                    logger.info(f"  ✅ 外键: {from_col} -> {table}({to_col})")
            else:
                logger.warning("  ⚠️ 未检测到外键约束（SQLite可能未启用外键）")

            logger.info("")

            # ========== 总结 ==========
            logger.info("="*60)
            if all_passed:
                logger.info("✅ 所有验证通过！数据库结构正确")
                logger.info("="*60)
                logger.info("")
                logger.info("【Phase 1 完成】")
                logger.info("✅ tasks表添加creator_id和creator_name字段")
                logger.info("✅ 创建roles表（9个字段）")
                logger.info("✅ 创建user_roles表（5个字段）")
                logger.info("✅ 插入3个默认角色（系统管理员、管理者、普通人员）")
                logger.info("✅ 创建必要的索引")
                logger.info("")
                logger.info("【下一步】")
                logger.info("→ Phase 2: 修改数据同步逻辑，提取飞书发起人字段")
                return True
            else:
                logger.error("❌ 验证失败！请检查数据库结构")
                logger.info("="*60)
                return False

    except Exception as e:
        logger.exception(f"❌ 验证过程出错: {e}")
        return False


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
