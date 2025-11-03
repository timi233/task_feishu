"""从Identity Hub同步工程师数据到本地缓存

从Identity Hub拉取所有在职用户，更新本地engineers表。
缓存基础信息（姓名、邮箱、手机号、部门名称）以供前端快速显示。

使用方式:
    # 作为脚本运行
    python sync_engineers_from_hub.py

    # 作为模块调用
    from sync_engineers_from_hub import sync_engineers_from_identity_hub
    sync_engineers_from_identity_hub()

日期: 2025-10-31
阶段: Phase 4.4 - 派工系统缓存层改造
"""

import logging
import sys
import os
from typing import Dict, List, Any

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from auth_identity_hub import IdentityHubClient
from task_db import get_db_connection
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_engineers_from_identity_hub() -> Dict[str, Any]:
    """从Identity Hub同步工程师列表

    Returns:
        Dict: 同步结果统计
            {
                "success": True,
                "total_users": 50,
                "created": 10,
                "updated": 40,
                "errors": []
            }
    """
    logger.info("开始从Identity Hub同步工程师数据...")

    stats = {
        "success": False,
        "total_users": 0,
        "created": 0,
        "updated": 0,
        "errors": []
    }

    try:
        # 1. 初始化Identity Hub客户端
        client = IdentityHubClient()

        # 2. 获取所有在职用户（分页拉取）
        all_users = []
        page = 1
        page_size = 100

        while True:
            logger.info(f"拉取第{page}页用户...")
            response = client.get_users(page=page, page_size=page_size, status=1)

            users = response.get("users", [])
            all_users.extend(users)

            total = response.get("total", 0)
            logger.info(f"  获取{len(users)}个用户，总计{len(all_users)}/{total}")

            # 判断是否还有下一页
            if len(all_users) >= total:
                break

            page += 1

        stats["total_users"] = len(all_users)
        logger.info(f"共拉取{len(all_users)}个在职用户")

        # 3. 更新本地数据库
        with get_db_connection() as conn:
            cursor = conn.cursor()

            for user in all_users:
                user_id = user.get("user_id")
                name = user.get("name")
                email = user.get("email")
                mobile = user.get("mobile")
                department_name = user.get("department_name")  # 从用户列表API获取

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
                            department_name = ?,
                            status = 1,
                            synced_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    """, (name, email, mobile, department_name, user_id))

                    stats["updated"] += 1
                    logger.debug(f"  更新工程师: {name} ({user_id})")
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO engineers
                        (user_id, name, email, mobile, department_name, status, synced_at)
                        VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    """, (user_id, name, email, mobile, department_name))

                    stats["created"] += 1
                    logger.debug(f"  新增工程师: {name} ({user_id})")

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
    print("Phase 4.4 - 从Identity Hub同步工程师数据")
    print("="*60 + "\n")

    # 执行同步
    result = sync_engineers_from_identity_hub()

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
