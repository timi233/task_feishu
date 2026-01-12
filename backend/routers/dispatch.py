"""Dispatch router exposing APIs for querying dispatch orders and stats."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from dispatch_db import (
    get_dispatch_order,
    get_dispatch_stats,
    query_dispatch_orders,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/dispatch",
    tags=["dispatch"],
)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
_VALID_ORDER_TYPES = {"all", "eisoo_dispatch", "work_order"}


@router.get("/orders")
async def list_dispatch_orders(
    order_type: str = Query(
        "all",
        description="派工单类型: eisoo_dispatch/work_order/all",
    ),
    start_time: Optional[int] = Query(
        None,
        description="服务开始时间下限，毫秒时间戳",
        ge=0,
    ),
    end_time: Optional[int] = Query(
        None,
        description="服务开始时间上限，毫秒时间戳",
        ge=0,
    ),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="每页返回数量",
    ),
):
    """Return paginated dispatch orders filtered by type and time range."""

    if order_type not in _VALID_ORDER_TYPES:
        raise HTTPException(status_code=400, detail="Invalid order_type parameter")
    if (
        start_time is not None
        and end_time is not None
        and start_time > end_time
    ):
        raise HTTPException(status_code=400, detail="start_time must be <= end_time")

    effective_type = None if order_type == "all" else order_type

    logger.info(
        "API request: list dispatch orders type=%s start=%s end=%s page=%d size=%d",
        order_type,
        start_time,
        end_time,
        page,
        page_size,
    )

    try:
        orders, total = query_dispatch_orders(
            order_type=effective_type,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to fetch dispatch orders: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch dispatch orders")

    total_pages = (total + page_size - 1) // page_size if total else 0
    return {
        "success": True,
        "data": orders,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
        "filters": {
            "order_type": order_type,
            "start_time": start_time,
            "end_time": end_time,
        },
    }


@router.get("/orders/{source_id}")
async def get_dispatch_order_detail(source_id: str):
    """Return the detail of a single dispatch order by source_id."""

    logger.info("API request: get dispatch order detail source_id=%s", source_id)

    try:
        order = get_dispatch_order(source_id)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to load dispatch order detail: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load dispatch order detail")

    if not order:
        raise HTTPException(status_code=404, detail="Dispatch order not found")

    return {"success": True, "data": order}


@router.get("/stats")
async def dispatch_stats():
    """Return aggregated dispatch order statistics."""

    logger.info("API request: dispatch stats")
    try:
        stats = get_dispatch_stats()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to gather dispatch stats: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch dispatch stats")

    return {"success": True, "stats": stats}
