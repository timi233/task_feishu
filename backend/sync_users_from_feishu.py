"""从飞书通讯录同步用户到本地engineers表

使用方式:
    python sync_users_from_feishu.py

日期: 2025-11-03
"""

import logging
import sys
import os
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(__file__))

from feishu_contacts import FeishuContactsReader
from task_db import get_db_connection
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_users_from_feishu() -> Dict[str, Any]:
    """从飞书通讯录同步所有用户

    Returns:
        Dict: 同步结果统计
    """
    logger.info("开始从飞书通讯录同步用户数据...")

    stats = {
        "success": False,
        "total_users": 0,
        "created": 0,
        "updated": 0,
        "errors": []
    }

    try:
        # 1. 初始化飞书通讯录客户端
        reader = FeishuContactsReader(
            app_id=settings.feishu.app_id,
            app_secret=settings.feishu.app_secret
        )

        # 2. 获取所有用户（自动分页）
        logger.info("拉取飞书通讯录用户...")
        all_users = reader.get_users(user_id_type="user_id")

        stats["total_users"] = len(all_users)
        logger.info(f"共拉取{len(all_users)}个用户")

        # 3. 更新本地数据库
        with get_db_connection() as conn:
            cursor = conn.cursor()

            for user in all_users:
                user_id = user.get("user_id")
                name = user.get("name")
                email = user.get("email")
                mobile = user.get("mobile")

                # 获取用户状态
                status_info = user.get("status", {})
                is_resigned = status_info.get("is_resigned", False)
                is_frozen = status_info.get("is_frozen", False)
                is_activated = status_info.get("is_activated", False)

                # 状态判断：已激活且未离职且未冻结 = 在职
                status = 1 if (is_activated and not is_resigned and not is_frozen) else 0

                if not user_id or not name:
                    error_msg = f"用户缺少必要字段: {user}"
                    logger.warning(error_msg)
                    stats["errors"].append(error_msg)
                    continue

                # 检查用户是否已存在
                cursor.execute("SELECT user_id FROM engineers WHERE user_id = ?", (user_id,))
                exists = cursor.fetchone()

                if exists:
                    # 更新现有记录
                    cursor.execute("""
                        UPDATE engineers SET
                            name = ?,
                            email = ?,
                            mobile = ?,
                            status = ?,
                            synced_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    """, (name, email, mobile, status, user_id))

                    stats["updated"] += 1
                    logger.debug(f"  更新用户: {name} ({user_id})")
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO engineers
                        (user_id, name, email, mobile, status, synced_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (user_id, name, email, mobile, status))

                    stats["created"] += 1
                    logger.debug(f"  新增用户: {name} ({user_id})")

            conn.commit()

        stats["success"] = True
        logger.info(f"✅ 同步完成: 新增{stats['created']}，更新{stats['updated']}")

        return stats

    except Exception as e:
        error_msg = f"同步失败: {str(e)}"
        logger.exception(error_msg)
        stats["errors"].append(error_msg)
        return stats


if __name__ == "__main__":
    print("\n" + "="*60)
    print("从飞书通讯录同步用户数据")
    print("="*60 + "\n")

    # 执行同步
    result = sync_users_from_feishu()

    # 打印结果
    print("\n" + "="*60)
    if result["success"]:
        print("✅ 同步成功")
        print(f"  总用户数: {result['total_users']}")
        print(f"  新增: {result['created']}")
        print(f"  更新: {result['updated']}")
    else:
        print("❌ 同步失败")
        if result["errors"]:
            print("\n错误信息:")
            for error in result["errors"]:
                print(f"  - {error}")
    print("="*60 + "\n")
