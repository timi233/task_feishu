"""数据库模块: 存储派工单数据"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:  # 兼容脚本相对/绝对导入
    from backend.task_db import DB_FILE, get_db_connection  # type: ignore
except ImportError:  # pragma: no cover - fallback for direct execution
    from task_db import DB_FILE, get_db_connection  # type: ignore

logger = logging.getLogger(__name__)

# 表字段（除自增主键、时间戳）
DISPATCH_COLUMNS: tuple[str, ...] = (
    "source_id",
    "order_type",
    "approval_code",
    "approval_status",
    "approval_flow",
    "approval_node",
    "submit_time",
    "complete_time",
    "submitter_id",
    "submitter_name",
    "submitter_department",
    "current_handler",
    "product_category",
    "product_model",
    "work_type",
    "work_method",
    "priority",
    "service_start_time",
    "service_start_period",
    "service_end_time",
    "service_end_period",
    "engineer_id",
    "engineer_name",
    "engineer_identity",
    "customer_company",
    "customer_contact",
    "customer_phone",
    "has_channel",
    "channel_name",
    "channel_contact",
    "channel_phone",
    "work_content",
    "work_duration",
    "order_status",
    "vendor_contact",
    "extra_data",
)

INSERT_SQL = f"""
INSERT OR REPLACE INTO dispatch_orders (
    {', '.join(DISPATCH_COLUMNS)},
    updated_at,
    synced_at
) VALUES (
    {', '.join(['?'] * len(DISPATCH_COLUMNS))},
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
"""


def _is_field_dispatch(order: Dict[str, Any]) -> bool:
    extra = order.get("extra_data")
    if isinstance(extra, dict):
        source = extra.get("_source_table") or extra.get("source_table")
        return source == "field_dispatch"
    return False


def _build_overlap_key(order: Dict[str, Any]) -> Optional[Tuple[str, int, int]]:
    customer = order.get("customer_company")
    if not isinstance(customer, str):
        return None
    customer_key = customer.strip()
    if not customer_key:
        return None
    start_time = order.get("service_start_time") or order.get("submit_time")
    if start_time is None:
        return None
    try:
        start_int = int(start_time)
    except (TypeError, ValueError):
        return None
    end_time = order.get("service_end_time") or order.get("complete_time") or start_int
    try:
        end_int = int(end_time)
    except (TypeError, ValueError):
        end_int = start_int
    return (customer_key.lower(), start_int, end_int)


def _deduplicate_parallel_orders(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """移除外勤申请与其它派工来源的并行重复记录。"""
    if not orders:
        return []

    unique_orders: List[Dict[str, Any]] = []
    index_map: Dict[Tuple[str, int, int], int] = {}

    for order in orders:
        key = _build_overlap_key(order)
        if not key:
            unique_orders.append(order)
            continue

        existing_idx = index_map.get(key)
        if existing_idx is None:
            index_map[key] = len(unique_orders)
            unique_orders.append(order)
            continue

        existing_order = unique_orders[existing_idx]

        if not (_is_field_dispatch(existing_order) or _is_field_dispatch(order)):
            continue

        if _is_field_dispatch(existing_order) and not _is_field_dispatch(order):
            unique_orders[existing_idx] = order
        elif not _is_field_dispatch(existing_order) and _is_field_dispatch(order):
            continue
        else:
            continue

    return unique_orders


def _ensure_db_dir() -> None:
    """确保数据库目录存在"""
    db_dir = os.path.dirname(DB_FILE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)


def init_dispatch_db() -> None:
    """初始化派工单相关表结构和索引"""
    _ensure_db_dir()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatch_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL UNIQUE,
                order_type TEXT NOT NULL,
                approval_code TEXT,
                approval_status TEXT,
                approval_flow TEXT,
                approval_node TEXT,
                submit_time INTEGER,
                complete_time INTEGER,
                submitter_id TEXT,
                submitter_name TEXT,
                submitter_department TEXT,
                current_handler TEXT,
                product_category TEXT,
                product_model TEXT,
                work_type TEXT,
                work_method TEXT,
                priority TEXT,
                service_start_time INTEGER,
                service_start_period TEXT,
                service_end_time INTEGER,
                service_end_period TEXT,
                engineer_id TEXT,
                engineer_name TEXT,
                engineer_identity TEXT,
                customer_company TEXT,
                customer_contact TEXT,
                customer_phone TEXT,
                has_channel TEXT,
                channel_name TEXT,
                channel_contact TEXT,
                channel_phone TEXT,
                work_content TEXT,
                work_duration REAL,
                order_status TEXT,
                vendor_contact TEXT,
                extra_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dispatch_orders_type ON dispatch_orders(order_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dispatch_orders_status ON dispatch_orders(approval_status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dispatch_orders_engineer ON dispatch_orders(engineer_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dispatch_orders_submit_time ON dispatch_orders(submit_time)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dispatch_orders_service_start ON dispatch_orders(service_start_time)"
        )

    logger.info("dispatch_orders table initialized")


def _normalize_extra_data(data: Any) -> Optional[str]:
    if data is None:
        return None
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        logger.debug("Failed to serialize extra_data: %s", data)
        return None


def save_dispatch_orders(orders: Iterable[Dict[str, Any]], order_type: str) -> int:
    """批量保存派工单数据，使用UPSERT避免重复"""
    orders = list(orders or [])
    if not orders:
        logger.info("No dispatch orders to save for type '%s'", order_type)
        return 0

    init_dispatch_db()

    saved = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for order in orders:
            payload: List[Any] = []
            for column in DISPATCH_COLUMNS:
                if column == "order_type":
                    payload.append(order.get("order_type") or order_type)
                    continue
                value = order.get(column)
                if column == "extra_data":
                    value = _normalize_extra_data(value)
                payload.append(value)

            try:
                cursor.execute(INSERT_SQL, payload)
                saved += 1
            except Exception:
                logger.exception(
                    "Failed to save dispatch order source_id=%s", order.get("source_id")
                )

    logger.info("Saved %d dispatch orders for type '%s'", saved, order_type)
    return saved


EXCLUDED_APPROVAL_STATUSES = ("已撤回",)


def get_dispatch_orders(
    order_type: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """根据条件查询派工单数据"""
    query = "SELECT * FROM dispatch_orders WHERE 1=1"
    params: List[Any] = []

    # 过滤已撤回等无效状态
    if EXCLUDED_APPROVAL_STATUSES:
        placeholders = ", ".join("?" for _ in EXCLUDED_APPROVAL_STATUSES)
        query += f" AND (approval_status IS NULL OR approval_status NOT IN ({placeholders}))"
        params.extend(EXCLUDED_APPROVAL_STATUSES)

    if order_type:
        query += " AND order_type = ?"
        params.append(order_type)
    if start_time is not None:
        query += " AND service_start_time >= ?"
        params.append(start_time)
    if end_time is not None:
        query += " AND service_start_time <= ?"
        params.append(end_time)

    query += " ORDER BY (service_start_time IS NULL), service_start_time DESC, submit_time DESC"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

    raw_results: List[Dict[str, Any]] = [_row_to_order(row) for row in rows]
    results = _deduplicate_parallel_orders(raw_results)

    logger.info(
        "Fetched %d dispatch_orders (type=%s, start=%s, end=%s)",
        len(results),
        order_type or "*",
        start_time,
        end_time,
    )
    return results


def _row_to_order(row: Any) -> Dict[str, Any]:
    record = dict(row)
    extra = record.get("extra_data")
    if isinstance(extra, str) and extra:
        try:
            record["extra_data"] = json.loads(extra)
        except json.JSONDecodeError:
            logger.debug(
                "Failed to decode extra_data for source_id=%s", record.get("source_id")
            )
    return record


def query_dispatch_orders(
    order_type: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Dict[str, Any]], int]:
    """按照条件分页查询派工单数据"""

    init_dispatch_db()

    where_clauses = ["1=1"]
    params: List[Any] = []

    # 过滤已撤回等无效状态
    if EXCLUDED_APPROVAL_STATUSES:
        placeholders = ", ".join("?" for _ in EXCLUDED_APPROVAL_STATUSES)
        where_clauses.append(f"(approval_status IS NULL OR approval_status NOT IN ({placeholders}))")
        params.extend(EXCLUDED_APPROVAL_STATUSES)

    if order_type:
        where_clauses.append("order_type = ?")
        params.append(order_type)
    if start_time is not None:
        where_clauses.append("service_start_time >= ?")
        params.append(start_time)
    if end_time is not None:
        where_clauses.append("service_start_time <= ?")
        params.append(end_time)

    where_sql = " AND ".join(where_clauses)
    order_sql = "ORDER BY (service_start_time IS NULL), service_start_time DESC, submit_time DESC"

    offset = (page - 1) * page_size

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM dispatch_orders WHERE {where_sql} {order_sql}",
            params,
        )
        rows = cursor.fetchall()

    orders = [_row_to_order(row) for row in rows]
    unique_orders = _deduplicate_parallel_orders(orders)
    total = len(unique_orders)
    start_idx = offset
    end_idx = offset + page_size
    paginated = unique_orders[start_idx:end_idx]

    logger.info(
        "Fetched %d dispatch orders with pagination (total=%d, type=%s, page=%d, size=%d)",
        len(paginated),
        total,
        order_type or "*",
        page,
        page_size,
    )
    return paginated, int(total)


def get_dispatch_order(source_id: str) -> Optional[Dict[str, Any]]:
    """根据 source_id 获取单条派工单"""

    init_dispatch_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dispatch_orders WHERE source_id = ?", (source_id,))
        row = cursor.fetchone()

    if not row:
        logger.info("Dispatch order not found for source_id=%s", source_id)
        return None
    return _row_to_order(row)


def get_dispatch_stats() -> Dict[str, Any]:
    """统计派工单数据（排除已撤回等无效状态）"""

    init_dispatch_db()
    stats = {
        "by_type": [],
        "by_priority": [],
        "by_engineer": [],
        "total": 0,
    }

    exclude_clause = ""
    exclude_params: List[Any] = []
    if EXCLUDED_APPROVAL_STATUSES:
        placeholders = ", ".join("?" for _ in EXCLUDED_APPROVAL_STATUSES)
        exclude_clause = f" WHERE (approval_status IS NULL OR approval_status NOT IN ({placeholders}))"
        exclude_params = list(EXCLUDED_APPROVAL_STATUSES)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM dispatch_orders{exclude_clause}", exclude_params)
        rows = cursor.fetchall()

    orders = _deduplicate_parallel_orders([_row_to_order(row) for row in rows])

    type_counter: Dict[str, int] = {}
    priority_counter: Dict[str, int] = {}
    engineer_counter: Dict[str, int] = {}

    for order in orders:
        order_type = order.get("order_type") or "unknown"
        type_counter[order_type] = type_counter.get(order_type, 0) + 1

        priority = order.get("priority") or "unknown"
        priority_counter[priority] = priority_counter.get(priority, 0) + 1

        engineer = order.get("engineer_name") or "unknown"
        engineer_counter[engineer] = engineer_counter.get(engineer, 0) + 1

    stats["by_type"] = [
        {"order_type": key, "count": count}
        for key, count in sorted(type_counter.items(), key=lambda item: item[1], reverse=True)
    ]
    stats["by_priority"] = [
        {"priority": key, "count": count}
        for key, count in sorted(priority_counter.items(), key=lambda item: item[1], reverse=True)
    ]
    stats["by_engineer"] = [
        {"engineer_name": key, "count": count}
        for key, count in sorted(engineer_counter.items(), key=lambda item: item[1], reverse=True)
    ]
    stats["total"] = len(orders)

    logger.info(
        "Dispatch stats generated: total=%d, type_groups=%d, priority_groups=%d",
        stats["total"],
        len(stats["by_type"]),
        len(stats["by_priority"]),
    )
    return stats


def get_dispatch_orders_count() -> int:
    """获取派工单总数（用于健康检查等场景）"""

    orders = get_dispatch_orders()
    count = len(orders)
    logger.info("Dispatch order count: %d", count)
    return count
