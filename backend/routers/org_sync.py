"""组织架构同步路由

提供手动触发从Identity Hub同步工程师数据的API端点。

日期: 2025-10-31
阶段: Phase 4.4 - 派工系统缓存层改造
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import logging
import sys
import os

# 确保能导入sync_engineers_from_hub
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sync_engineers_from_hub import sync_engineers_from_identity_hub

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/org", tags=["Organization Sync"])


@router.post("/sync-from-hub")
async def sync_from_identity_hub():
    """从Identity Hub同步工程师数据

    手动触发同步，从Identity Hub拉取所有在职用户并更新本地engineers表。

    Returns:
        同步结果统计

    Example:
        curl -X POST http://10.242.94.9:8000/api/org/sync-from-hub
    """
    logger.info("收到手动同步请求")

    try:
        result = sync_engineers_from_identity_hub()

        if result["success"]:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "success",
                    "message": f"成功同步{result['total_users']}个工程师",
                    "details": {
                        "total": result["total_users"],
                        "created": result["created"],
                        "updated": result["updated"]
                    }
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": "同步过程中出现错误",
                    "errors": result["errors"]
                }
            )

    except Exception as e:
        logger.exception(f"同步失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步失败: {str(e)}"
        )
