"""
工程师管理路由

提供工程师列表查询和同步功能
"""

import os
import logging
import datetime
from fastapi import APIRouter, HTTPException

from task_db import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/engineers",
    tags=["engineers"]
)


@router.get("")
async def get_engineers():
    """
    获取所有工程师列表（前端专用，无需认证）

    用例:
    - 前端工程师选择器组件
    - 派工表单中的工程师下拉列表

    示例:
    GET /api/engineers
    """
    logger.info("API request: get engineers")

    try:
        from task_db import get_engineers_from_db

        # 从engineers表获取在职工程师列表
        engineers_from_db = get_engineers_from_db(status=1)

        if engineers_from_db:
            # 有工程师数据,返回user_id和name
            engineers_list = [
                {
                    "user_id": eng["user_id"],
                    "name": eng["name"]
                }
                for eng in engineers_from_db
            ]
        else:
            # 工程师表为空,使用tasks表作为fallback
            logger.warning("Engineers table is empty, falling back to tasks table")
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT assignee
                    FROM tasks
                    WHERE assignee IS NOT NULL AND assignee != ''
                    ORDER BY assignee
                """)

                # fallback模式下只返回name,user_id设为None
                engineers_list = [
                    {
                        "user_id": None,
                        "name": row["assignee"]
                    }
                    for row in cursor.fetchall()
                ]

        return {
            "total": len(engineers_list),
            "engineers": engineers_list
        }

    except Exception as e:
        logger.exception("Failed to get engineers")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_engineers_from_feishu():
    """
    从飞书通讯录同步工程师列表到数据库

    用例:
    - 初始化工程师数据
    - 定期更新人员信息
    - 在数据同步后自动调用

    权限要求:
    - contact:user:read

    示例:
    POST /api/engineers/sync
    Header: X-API-Key: your-readonly-key
    """
    logger.info("API request: manual engineers sync triggered")

    try:
        from feishu_contacts import FeishuContactsReader
        from task_db import save_engineers_to_db

        # 从环境变量读取飞书配置
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")

        if not all([app_id, app_secret]):
            raise HTTPException(
                status_code=500,
                detail="Feishu configuration incomplete. Check FEISHU_APP_ID and FEISHU_APP_SECRET."
            )

        # 1. 从飞书通讯录获取用户列表
        logger.info("Fetching users from Feishu contacts...")
        reader = FeishuContactsReader(app_id, app_secret)
        users = reader.get_users(page_size=50)

        if not users:
            return {
                "success": False,
                "message": "No users fetched from Feishu contacts",
                "engineers_synced": 0
            }

        logger.info(f"Fetched {len(users)} users from Feishu")

        # 2. 过滤在职用户
        active_users = reader.filter_active_users(users)
        logger.info(f"Active users: {len(active_users)}/{len(users)}")

        # 3. 转换为工程师格式
        engineers = reader.transform_to_engineers(active_users)

        # 4. 保存到数据库
        logger.info(f"Saving {len(engineers)} engineers to database...")
        saved_count = save_engineers_to_db(engineers)

        logger.info(f"Engineers sync completed: {saved_count} engineers saved")

        return {
            "success": True,
            "message": "Engineers synced successfully",
            "total_users": len(users),
            "active_users": len(active_users),
            "engineers_synced": saved_count,
            "timestamp": datetime.datetime.now().isoformat()
        }

    except Exception as e:
        logger.exception("Failed to sync engineers from Feishu")
        raise HTTPException(status_code=500, detail=f"Engineers sync failed: {str(e)}")
