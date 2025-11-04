"""清理重复用户，只保留从飞书同步的用户

日期: 2025-11-03
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from task_db import get_db_connection
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_duplicate_users():
    """清理重复用户数据"""

    logger.info("开始清理重复用户...")

    stats = {
        "task_users_deleted": 0,
        "identity_hub_users_deleted": 0,
        "feishu_users_kept": 0,
        "admin_role_transferred": False
    }

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. 查找系统管理员角色
            cursor.execute("SELECT id FROM roles WHERE role_key = 'system_admin'")
            admin_role = cursor.fetchone()
            admin_role_id = admin_role['id'] if admin_role else None

            # 2. 查找当前拥有系统管理员角色的用户
            if admin_role_id:
                cursor.execute("""
                    SELECT user_id, assigned_by
                    FROM user_roles
                    WHERE role_id = ?
                """, (admin_role_id,))
                admin_users = cursor.fetchall()
                logger.info(f"当前系统管理员: {[u['user_id'] for u in admin_users]}")

                # 3. 查找飞书的张健账户
                cursor.execute("""
                    SELECT user_id, name
                    FROM engineers
                    WHERE name = '张健'
                    AND user_id NOT LIKE 'task_%'
                    AND user_id NOT LIKE 'ou_%'
                    AND user_id NOT LIKE '%-%-%-%-%'
                    LIMIT 1
                """)
                feishu_zhangjian = cursor.fetchone()

                if feishu_zhangjian:
                    feishu_user_id = feishu_zhangjian['user_id']
                    logger.info(f"找到飞书张健账户: {feishu_user_id}")

                    # 4. 检查飞书张健是否已有管理员角色
                    cursor.execute("""
                        SELECT id FROM user_roles
                        WHERE user_id = ? AND role_id = ?
                    """, (feishu_user_id, admin_role_id))

                    if not cursor.fetchone():
                        # 5. 分配管理员角色给飞书张健
                        cursor.execute("""
                            INSERT INTO user_roles (user_id, role_id, assigned_by)
                            VALUES (?, ?, 'system')
                        """, (feishu_user_id, admin_role_id))
                        logger.info(f"✅ 已将系统管理员角色分配给飞书账户: {feishu_user_id}")
                        stats["admin_role_transferred"] = True

            # 6. 删除task_开头的临时用户
            cursor.execute("DELETE FROM user_roles WHERE user_id LIKE 'task_%'")
            cursor.execute("DELETE FROM engineers WHERE user_id LIKE 'task_%'")
            stats["task_users_deleted"] = cursor.rowcount
            logger.info(f"删除 {stats['task_users_deleted']} 个临时用户（task_开头）")

            # 7. 删除Identity Hub用户（ou_开头和UUID格式）
            # 删除ou_开头的用户
            cursor.execute("DELETE FROM user_roles WHERE user_id LIKE 'ou_%'")
            cursor.execute("DELETE FROM engineers WHERE user_id LIKE 'ou_%'")
            ou_deleted = cursor.rowcount

            # 删除UUID格式的用户（包含4个'-'符号）
            cursor.execute("""
                DELETE FROM user_roles
                WHERE user_id LIKE '%-%-%-%-%'
            """)
            cursor.execute("""
                DELETE FROM engineers
                WHERE user_id LIKE '%-%-%-%-%'
            """)
            uuid_deleted = cursor.rowcount

            stats["identity_hub_users_deleted"] = ou_deleted + uuid_deleted
            logger.info(f"删除 {stats['identity_hub_users_deleted']} 个Identity Hub用户")

            # 8. 统计保留的飞书用户
            cursor.execute("SELECT COUNT(*) as count FROM engineers")
            stats["feishu_users_kept"] = cursor.fetchone()['count']
            logger.info(f"保留 {stats['feishu_users_kept']} 个飞书用户")

            conn.commit()

        logger.info("✅ 清理完成")
        return stats

    except Exception as e:
        logger.exception(f"清理失败: {e}")
        raise


if __name__ == "__main__":
    print("\n" + "="*60)
    print("清理重复用户数据")
    print("="*60 + "\n")

    result = cleanup_duplicate_users()

    print("\n" + "="*60)
    print("清理结果:")
    print(f"  删除临时用户(task_): {result['task_users_deleted']}")
    print(f"  删除Identity Hub用户: {result['identity_hub_users_deleted']}")
    print(f"  保留飞书用户: {result['feishu_users_kept']}")
    print(f"  管理员角色转移: {'是' if result['admin_role_transferred'] else '否'}")
    print("="*60 + "\n")
