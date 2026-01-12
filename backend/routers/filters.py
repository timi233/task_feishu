"""
筛选器管理路由

提供筛选器的CRUD操作和激活功能
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException

from models.schemas import FilterCreate
from task_filter import task_filter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/filters",
    tags=["filters"]
)


@router.get("")
async def get_filters():
    """获取所有可用的筛选器"""
    return {
        "available_filters": task_filter.get_available_filters(),
        "active_filter": task_filter.get_active_filter()
    }


@router.post("/activate")
async def activate_filter(filter_name: str):
    """激活指定的筛选器"""
    if task_filter.set_active_filter(filter_name):
        return {"message": f"Successfully activated filter '{filter_name}'"}
    else:
        raise HTTPException(status_code=404, detail=f"Filter '{filter_name}' not found")


@router.post("/add")
async def add_filter(filter_data: FilterCreate):
    """添加新的筛选器"""
    try:
        task_filter.add_filter(
            filter_data.name,
            filter_data.conditions,
            filter_data.enabled,
            filter_data.logic
        )
        return {"message": f"Successfully added filter '{filter_data.name}'"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{name}")
async def update_filter(
    name: str,
    conditions: Optional[List[dict]] = None,
    enabled: Optional[bool] = None,
    logic: Optional[str] = None
):
    """更新现有筛选器"""
    try:
        task_filter.update_filter(name, conditions, enabled, logic)
        return {"message": f"Successfully updated filter '{name}'"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{name}")
async def remove_filter(name: str):
    """删除筛选器"""
    try:
        task_filter.remove_filter(name)
        return {"message": f"Successfully removed filter '{name}'"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
