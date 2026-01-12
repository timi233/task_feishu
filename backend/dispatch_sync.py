"""飞书派工单同步模块"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

try:  # 兼容脚本执行路径
    from backend.dispatch_db import init_dispatch_db, save_dispatch_orders  # type: ignore
except ImportError:  # pragma: no cover
    from dispatch_db import init_dispatch_db, save_dispatch_orders  # type: ignore

try:
    from backend.feishu_reader import FeishuBitableReader  # type: ignore
except ImportError:  # pragma: no cover
    from feishu_reader import FeishuBitableReader  # type: ignore

logger = logging.getLogger(__name__)

BITABLE_BASE_ID = os.getenv("FEISHU_DISPATCH_BASE_ID", "U7eAb65luaX1zKscoOzcgcednlh")
EISOO_TABLE_ID = os.getenv("FEISHU_EISOO_DISPATCH_TABLE_ID", "tbl8DESrT22JYvfS")
WORK_ORDER_TABLE_ID = os.getenv("FEISHU_WORK_ORDER_TABLE_ID", "tbl6CuEM97ybgRri")
FIELD_DISPATCH_TABLE_ID = os.getenv("FEISHU_FIELD_DISPATCH_TABLE_ID", "tblC8B2jvybfbdVM")

ORDER_TYPE_EISOO = "eisoo_dispatch"
ORDER_TYPE_WORK = "work_order"

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")

_reader: Optional[FeishuBitableReader] = None

FIELD_DISPATCH_ALIASES: Dict[str, List[str] | str] = {
    "客户公司名称": "客户名称",
    "客户联系方式": ["联系电话"],
    "工作内容": "服务内容",
    "售后工程师": ["关联销售", "发起人"],
    "服务开始时间": "预计开始服务时间",
    "服务结束时间": "预计结束服务时间",
    "时长": "预计时长",
}
FIELD_DISPATCH_SUBMITTER_FALLBACK = "未登录时显示的人名"


def _get_reader() -> FeishuBitableReader:
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        raise RuntimeError("FEISHU_APP_ID/FEISHU_APP_SECRET are required")

    global _reader
    if _reader is None:
        _reader = FeishuBitableReader(FEISHU_APP_ID, FEISHU_APP_SECRET, timeout=20)
    return _reader


def _fetch_records(table_id: str) -> List[Dict[str, Any]]:
    try:
        reader = _get_reader()
    except RuntimeError as exc:
        logger.error("Feishu credentials missing: %s", exc)
        return []
    try:
        records = reader.get_records(BITABLE_BASE_ID, table_id)
        logger.info("Fetched %d records from table %s", len(records), table_id)
        return records
    except Exception as exc:  # pragma: no cover - 网络/飞书异常
        logger.exception("Failed to fetch records from table %s: %s", table_id, exc)
        return []


def _extract_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("text", "name", "value", "link"):
            text_val = value.get(key)
            if isinstance(text_val, str) and text_val.strip():
                return text_val.strip()
        # 嵌套格式
        if "children" in value and isinstance(value["children"], list):
            child_texts = [text for text in (_extract_text(c) for c in value["children"]) if text]
            if child_texts:
                return ", ".join(child_texts)
    if isinstance(value, list):
        parts = [text for text in (_extract_text(item) for item in value) if text]
        if parts:
            return ", ".join(parts)
        return None
    text = str(value).strip()
    return text or None


def _normalize_contact_entry(value: Any) -> Tuple[Optional[str], Optional[str]]:
    if isinstance(value, dict):
        contact_id = value.get("id") or value.get("open_id") or value.get("user_id")
        contact_name = value.get("name") or value.get("text") or value.get("value")
        if contact_name is not None and not isinstance(contact_name, str):
            contact_name = _extract_text(contact_name)
        if contact_id is not None and not isinstance(contact_id, str):
            contact_id = str(contact_id)
        return contact_id, contact_name
    if isinstance(value, str):
        val = value.strip()
        return (None, val or None)
    return (None, None)


def _extract_first_contact(value: Any) -> Tuple[Optional[str], Optional[str]]:
    if isinstance(value, list):
        for item in value:
            cid, name = _normalize_contact_entry(item)
            if cid or name:
                return cid, name
        return (None, None)
    return _normalize_contact_entry(value)


def _extract_all_contact_names(value: Any) -> Optional[str]:
    if isinstance(value, list):
        names = [name for _, name in (_normalize_contact_entry(v) for v in value) if name]
        if names:
            return ", ".join(names)
        return None
    _, name = _normalize_contact_entry(value)
    return name or _extract_text(value)


def _parse_timestamp(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(float(stripped))
        except ValueError:
            pass
        try:
            parsed = datetime.fromisoformat(stripped)
        except ValueError:
            logger.debug("Unable to parse timestamp string: %s", value)
        else:
            return int(parsed.timestamp() * 1000)
    else:
        logger.debug("Unable to parse timestamp value: %s", value)
    return None


def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        logger.debug("Unable to parse float value: %s", value)
        return None


def _map_record_to_order(
    record: Dict[str, Any],
    order_type: str,
    field_aliases: Optional[Dict[str, Any]] = None,
    fallback_submitter_field: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    fields: Dict[str, Any] = record.get("fields") or {}
    used_fields: set[str] = set()

    def consume(field_name: str) -> Any:
        candidates: List[str] = [field_name]
        if field_aliases and field_name in field_aliases:
            alias_value = field_aliases[field_name]
            if isinstance(alias_value, (list, tuple)):
                candidates.extend(alias_value)
            else:
                candidates.append(alias_value)

        for candidate in candidates:
            if candidate in fields:
                used_fields.add(candidate)
                return fields.get(candidate)
        return None

    fallback_submitter_raw = consume(fallback_submitter_field) if fallback_submitter_field else None
    source_raw = consume("SourceID")
    source_id = _extract_text(source_raw) or record.get("record_id")
    if not source_id:
        logger.warning("Skip record without source_id: %s", record)
        return None

    submitter_raw = consume("发起人")
    submitter_id, submitter_name = _extract_first_contact(submitter_raw)
    fallback_submitter_name = _extract_text(fallback_submitter_raw)
    if fallback_submitter_name:
        submitter_name = fallback_submitter_name

    engineer_raw = consume("售后工程师")
    engineer_id, _ = _extract_first_contact(engineer_raw)
    # 使用 _extract_all_contact_names 获取所有工程师名字（逗号分隔）
    engineer_name = _extract_all_contact_names(engineer_raw)

    order: Dict[str, Any] = {
        "source_id": source_id,
        "order_type": order_type,
        "approval_code": _extract_text(consume("申请编号")),
        "approval_status": _extract_text(consume("申请状态")),
        "approval_flow": _extract_text(consume("审批流程")),
        "approval_node": _extract_text(consume("审批节点")),
        "submit_time": _parse_timestamp(consume("发起时间")),
        "complete_time": _parse_timestamp(consume("完成时间")),
        "submitter_id": submitter_id,
        "submitter_name": submitter_name,
        "submitter_department": _extract_text(consume("发起人部门")),
        "current_handler": _extract_all_contact_names(consume("当前处理人")),
        "product_category": _extract_text(consume("产品分类")),
        "product_model": _extract_text(consume("产品型号")),
        "work_type": _extract_text(consume("工作类型")),
        "work_method": _extract_text(consume("工作方式")),
        "priority": _extract_text(consume("优先级")),
        "service_start_time": _parse_timestamp(consume("服务开始时间")),
        "service_start_period": _extract_text(consume("服务开始时间-时间段")),
        "service_end_time": _parse_timestamp(consume("服务结束时间")),
        "service_end_period": _extract_text(consume("服务结束时间-时间段")),
        "engineer_id": engineer_id,
        "engineer_name": engineer_name,
        "engineer_identity": _extract_text(consume("工程师身份")),
        "customer_company": _extract_text(consume("客户公司名称")),
        "customer_contact": _extract_text(consume("客户联系人")),
        "customer_phone": _extract_text(consume("客户联系方式")),
        "has_channel": _extract_text(consume("是否有渠道")),
        "channel_name": _extract_text(consume("渠道名称")),
        "channel_contact": _extract_text(consume("渠道联系人")),
        "channel_phone": _extract_text(consume("渠道联系人联系方式")),
        "work_content": _extract_text(consume("工作内容")),
        "work_duration": _parse_float(consume("时长")),
        "order_status": _extract_text(consume("工单状态")),
        "vendor_contact": _extract_text(consume("厂家对接人")),
    }

    # extra_data保存剩余字段
    extra_fields = {k: v for k, v in fields.items() if k not in used_fields}
    order["extra_data"] = extra_fields or None

    return order


def _transform_records(
    records: List[Dict[str, Any]],
    default_order_type: str,
    field_aliases: Optional[Dict[str, Any]] = None,
    order_type_selector: Optional[Callable[[Dict[str, Any]], str]] = None,
    post_process: Optional[Callable[[Dict[str, Any], Dict[str, Any]], None]] = None,
    fallback_submitter_field: Optional[str] = None,
) -> List[Dict[str, Any]]:
    transformed: List[Dict[str, Any]] = []
    for record in records:
        try:
            record_type = (
                order_type_selector(record) if order_type_selector else default_order_type
            ) or default_order_type
            mapped = _map_record_to_order(
                record,
                record_type,
                field_aliases=field_aliases,
                fallback_submitter_field=fallback_submitter_field,
            )
            if mapped:
                if post_process:
                    post_process(record, mapped)
                transformed.append(mapped)
        except Exception:
            logger.exception("Failed to map record: %s", record)
    logger.info(
        "Transformed %d/%d records for order_type=%s",
        len(transformed),
        len(records),
        default_order_type,
    )
    return transformed


def sync_eisoo_dispatch() -> int:
    logger.info("Start syncing Eisoo dispatch orders")
    init_dispatch_db()
    records = _fetch_records(EISOO_TABLE_ID)
    if not records:
        logger.warning("No Eisoo dispatch records fetched")
        return 0

    orders = _transform_records(records, ORDER_TYPE_EISOO)
    return save_dispatch_orders(orders, ORDER_TYPE_EISOO)


def sync_work_orders() -> int:
    logger.info("Start syncing work orders")
    init_dispatch_db()
    records = _fetch_records(WORK_ORDER_TABLE_ID)
    if not records:
        logger.warning("No work order records fetched")
        return 0

    orders = _transform_records(records, ORDER_TYPE_WORK)
    return save_dispatch_orders(orders, ORDER_TYPE_WORK)


def _detect_field_dispatch_type(record: Dict[str, Any]) -> str:
    fields = record.get("fields") or {}
    dispatch_type = _extract_text(fields.get("外勤类型"))
    if dispatch_type and "厂" in dispatch_type:
        return ORDER_TYPE_EISOO
    return ORDER_TYPE_WORK


def _mark_field_dispatch_source(record: Dict[str, Any], order: Dict[str, Any]) -> None:
    extra = order.get("extra_data")
    if not isinstance(extra, dict):
        extra = {} if extra is None else {"_raw_extra": extra}
    extra["_source_table"] = "field_dispatch"
    fields = record.get("fields") or {}
    dispatch_type = fields.get("外勤类型")
    if dispatch_type:
        extra["_field_dispatch_type"] = dispatch_type
    work_order_id = fields.get("工单编号")
    if work_order_id:
        extra["_field_dispatch_work_order"] = work_order_id
    order["extra_data"] = extra


def sync_field_dispatch() -> Dict[str, int]:
    logger.info("Start syncing field dispatch orders")
    init_dispatch_db()
    records = _fetch_records(FIELD_DISPATCH_TABLE_ID)
    if not records:
        logger.info("No field dispatch records fetched")
        return {
            ORDER_TYPE_EISOO: 0,
            ORDER_TYPE_WORK: 0,
        }

    orders = _transform_records(
        records,
        ORDER_TYPE_WORK,
        field_aliases=FIELD_DISPATCH_ALIASES,
        order_type_selector=_detect_field_dispatch_type,
        post_process=_mark_field_dispatch_source,
        fallback_submitter_field=FIELD_DISPATCH_SUBMITTER_FALLBACK,
    )
    summary: Dict[str, int] = {
        ORDER_TYPE_EISOO: 0,
        ORDER_TYPE_WORK: 0,
    }
    if not orders:
        return summary

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for order in orders:
        grouped.setdefault(order["order_type"], []).append(order)

    for order_type, order_list in grouped.items():
        saved = save_dispatch_orders(order_list, order_type)
        summary[order_type] = summary.get(order_type, 0) + saved

    logger.info("Field dispatch sync finished: %s", summary)
    return summary


def sync_all() -> Dict[str, int]:
    logger.info("Running full dispatch sync")
    init_dispatch_db()
    eisoo_saved = sync_eisoo_dispatch()
    work_saved = sync_work_orders()
    summary = {
        ORDER_TYPE_EISOO: eisoo_saved,
        ORDER_TYPE_WORK: work_saved,
    }
    field_summary = sync_field_dispatch()
    for order_type, count in field_summary.items():
        summary[order_type] = summary.get(order_type, 0) + count
    logger.info("Dispatch sync finished: %s", summary)
    return summary


if __name__ == "__main__":  # pragma: no cover
    try:
        result = sync_all()
        print(result)
    except Exception as err:  # pylint: disable=broad-except
        logger.exception("Dispatch sync failed: %s", err)
