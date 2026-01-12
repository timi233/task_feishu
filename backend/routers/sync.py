"""
数据同步路由

提供从飞书手动同步数据到数据库的功能
"""

import os
import logging
import datetime
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["sync"]
)


@router.post("/sync")
async def sync_from_feishu():
    """
    手动触发从飞书同步数据到数据库

    用例:
    - 用户在前端点击"同步数据"按钮
    - 管理员需要立即更新数据

    示例:
    POST /api/sync
    Header: X-API-Key: your-readonly-key
    """
    logger.info("API request: manual sync triggered")

    try:
        from feishu_reader import FeishuBitableReader
        from process_feishu_data import process_feishu_records
        from task_db import save_processed_tasks_to_db

        # 从环境变量读取飞书配置
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        app_token = os.getenv("FEISHU_APP_TOKEN")
        table_id = os.getenv("FEISHU_TABLE_ID")

        if not all([app_id, app_secret, app_token, table_id]):
            raise HTTPException(
                status_code=500,
                detail="Feishu configuration incomplete. Check environment variables."
            )

        # 1. 从飞书获取数据
        logger.info("Fetching data from Feishu...")
        reader = FeishuBitableReader(app_id, app_secret)
        raw_records = reader.get_records(app_token, table_id)

        if not raw_records:
            return {
                "success": False,
                "message": "No data fetched from Feishu",
                "records_synced": 0
            }

        # 2. 处理数据
        logger.info(f"Processing {len(raw_records)} records...")
        processed_tasks = process_feishu_records(raw_records)

        # 3. 保存到数据库
        logger.info("Saving to database...")
        save_processed_tasks_to_db(processed_tasks)

        logger.info(f"Sync completed: {len(processed_tasks)} tasks synced")

        return {
            "success": True,
            "message": "Data synced successfully",
            "records_synced": len(processed_tasks),
            "timestamp": datetime.datetime.now().isoformat()
        }

    except Exception as e:
        logger.exception("Failed to sync data from Feishu")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/sync/dispatch")
async def sync_dispatch_orders():
    """手动同步派工单数据"""

    logger.info("API request: dispatch sync triggered")

    try:
        from dispatch_sync import sync_all as sync_dispatch  # 延迟导入以减少开销

        results = sync_dispatch()
        total_synced = sum(results.values())

        return {
            "success": True,
            "message": "Dispatch data synced successfully",
            "records_synced": results,
            "total_synced": total_synced,
            "timestamp": datetime.datetime.now().isoformat()
        }

    except Exception as e:  # pragma: no cover - 运行时保护
        logger.exception("Failed to sync dispatch data from Feishu")
        raise HTTPException(status_code=500, detail=f"Dispatch sync failed: {str(e)}")
