"""Approvals router encapsulating Feishu approval operations."""

import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, root_validator, validator

import approval_config
from feishu_approval import FeishuApprovalManager, ApprovalAPIError
from task_db import get_db_connection
from auth_permission import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/approvals",
    tags=["approvals"],
)


def initialize_approval_manager() -> Optional[FeishuApprovalManager]:
    """Create Feishu approval manager if configuration is present."""
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        logger.warning("Feishu approval manager not initialized: missing credentials")
        return None

    try:
        manager = FeishuApprovalManager(
            app_id=app_id,
            app_secret=app_secret,
            approval_code=None,
        )
        try:
            default_code = approval_config.get_approval_code(approval_config.DEFAULT_APPROVAL_TYPE)
        except ValueError:
            logger.info(
                "Default approval code for type '%s' not configured; manager will require overrides",
                approval_config.DEFAULT_APPROVAL_TYPE,
            )
        else:
            manager.approval_code = default_code
            logger.info(
                "Default approval code for type '%s' loaded successfully",
                approval_config.DEFAULT_APPROVAL_TYPE,
            )
        logger.info("Feishu approval manager initialized successfully")
        return manager
    except Exception as exc:  # noqa: broad-except - log and fallback to None
        logger.exception("Failed to initialize Feishu approval manager: %s", exc)
        return None


approval_manager = initialize_approval_manager()
try:
    approval_code_env = approval_config.get_approval_code(approval_config.DEFAULT_APPROVAL_TYPE)
except ValueError:
    approval_code_env = None
approval_admin_user_id = os.getenv("FEISHU_APPROVAL_ADMIN_USER_ID")


class CreateDispatchRequest(BaseModel):
    """Request model for creating a new dispatch approval."""

    task_name: str
    assignee: str
    priority: str
    start_date: datetime.date
    end_date: datetime.date
    user_id: Optional[str] = None
    description: Optional[str] = None
    extra_fields: Optional[Dict[str, Any]] = None
    approval_type: str = approval_config.DEFAULT_APPROVAL_TYPE

    @root_validator(skip_on_failure=True)
    def validate_dates(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        start = values.get("start_date")
        end = values.get("end_date")
        if start and end and start > end:
            raise ValueError("start_date must be on or before end_date")
        return values

    @validator("approval_type")
    def validate_approval_type(cls, value: str) -> str:
        """Ensure the provided approval type exists in configuration."""
        approval_config.get_approval_config(value)
        return value


class UpdateDispatchRequest(BaseModel):
    """Request model for updating an existing dispatch approval."""

    task_name: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    user_id: Optional[str] = None
    remark: Optional[str] = None

    @root_validator(skip_on_failure=True)
    def validate_payload(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        start = values.get("start_date")
        end = values.get("end_date")
        if start and end and start > end:
            raise ValueError("start_date must be on or before end_date")

        change_fields = [
            values.get("task_name"),
            values.get("assignee"),
            values.get("priority"),
            values.get("start_date"),
            values.get("end_date"),
        ]
        if not any(change_fields):
            raise ValueError("At least one field must be provided for update")
        return values


class TransferDispatchRequest(BaseModel):
    """Request model for transferring a dispatch to another assignee."""

    new_assignee: str
    user_id: Optional[str] = None
    reason: Optional[str] = None


class CloseDispatchRequest(BaseModel):
    """Request model for canceling an approval instance."""

    user_id: Optional[str] = None
    reason: Optional[str] = None


class CompleteDispatchRequest(BaseModel):
    """Request model for marking a dispatch as completed."""

    user_id: Optional[str] = None
    completion_note: Optional[str] = None


class ApprovalDetailResponse(BaseModel):
    """Response model for approval detail queries."""

    success: bool
    message: str
    instance_code: str
    approval_name: Optional[str] = None
    status: Optional[str] = None
    form_data: Dict[str, Any]
    task_list: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]


def get_effective_manager() -> FeishuApprovalManager:
    """Return the initialized approval manager or raise an HTTP error."""
    if approval_manager is None:
        logger.error("Feishu approval manager is not configured")
        raise HTTPException(status_code=503, detail="Feishu approval integration is not configured")
    return approval_manager


def resolve_user_id(provided_user_id: Optional[str]) -> str:
    """Resolve the effective user id for approval actions."""
    effective_user_id = provided_user_id or approval_admin_user_id
    if not effective_user_id:
        logger.error("Approval action requested without user_id and no default configured")
        raise HTTPException(status_code=400, detail="user_id is required for approval operations")
    return effective_user_id


def format_approval_url(instance_code: str, approval_code: Optional[str] = None) -> str:
    """Construct a Feishu approval deep link URL."""
    effective_code = approval_code or approval_code_env
    if not effective_code:
        logger.warning("Approval code not set; approval URL may be incomplete")
    approval_code_value = effective_code or ""
    return (
        "https://applink.feishu.cn/client/approval/detail"
        f"?approvalCode={approval_code_value}&instanceCode={instance_code}"
    )


def parse_form_data(raw_form: Any) -> Dict[str, Any]:
    """Parse form data from the approval detail response into a dict."""
    if not raw_form:
        return {}

    try:
        if isinstance(raw_form, str):
            parsed = json.loads(raw_form)
        else:
            parsed = raw_form
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to parse approval form data: %s", exc)
        return {}

    if isinstance(parsed, list):
        return {
            str(item.get("name") or item.get("id")): item.get("value")
            for item in parsed
            if isinstance(item, dict)
        }

    if isinstance(parsed, dict):
        return parsed

    return {}


def merge_form_data(original: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge fields into the original form data, ignoring None values."""
    merged = dict(original or {})
    for key, value in updates.items():
        if value is not None:
            merged[key] = value
    return merged


def update_local_task(instance_code: str, **fields: Any) -> None:
    """Best-effort update to the local tasks table for the given approval instance."""
    if not instance_code or not fields:
        return

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            assignments = ", ".join(f"{column} = ?" for column in fields)
            params: List[Any] = list(fields.values()) + [instance_code]
            cursor.execute(
                f"UPDATE tasks SET {assignments}, last_updated = CURRENT_TIMESTAMP WHERE approval_instance_code = ?",
                params,
            )
    except Exception as exc:  # noqa: broad-except - do not block API on local cache issues
        logger.warning(
            "Failed to update local task cache for instance %s: %s",
            instance_code,
            exc,
        )


def assignee_exists(assignee: str) -> bool:
    """Check whether the assignee already exists in the cached task table."""
    if not assignee:
        return False

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM tasks WHERE assignee = ? LIMIT 1",
                (assignee,),
            )
            return cursor.fetchone() is not None
    except Exception as exc:  # noqa: broad-except - missing table/column should not break API
        logger.warning(
            "Failed to verify assignee %s in local cache: %s",
            assignee,
            exc,
        )
        return False


@router.post("")
async def create_dispatch(
    payload: CreateDispatchRequest,
    current_user: Dict[str, Any] = Depends(require_permission("task:create"))
) -> Dict[str, Any]:
    """创建派工(新建审批实例)。

    流程:
        1. 校验提交参数与工程师信息
        2. 构造审批表单并调用飞书创建审批实例
        3. 记录审批编号并返回审批跳转链接

    Returns:
        dict: 包含success/message/instance_code/approval_url字段
    """
    logger.info(
        "Create dispatch request: task=%s assignee=%s priority=%s approval_type=%s",
        payload.task_name,
        payload.assignee,
        payload.priority,
        payload.approval_type,
    )

    manager = get_effective_manager()
    user_id = resolve_user_id(payload.user_id)

    try:
        approval_code = approval_config.get_approval_code(payload.approval_type)
    except ValueError as exc:
        logger.error("Approval code lookup failed for type %s: %s", payload.approval_type, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not assignee_exists(payload.assignee):
        logger.warning("Assignee %s not found in local cache", payload.assignee)

    form_data = {
        "task_name": payload.task_name,
        "assignee": payload.assignee,
        "priority": payload.priority,
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat(),
    }
    if payload.description:
        form_data["description"] = payload.description
    if payload.extra_fields:
        form_data.update(payload.extra_fields)

    missing_fields = approval_config.validate_form_data(payload.approval_type, form_data)
    if missing_fields:
        missing_str = ", ".join(missing_fields)
        logger.error(
            "Form data validation failed for approval_type=%s missing=%s",
            payload.approval_type,
            missing_str,
        )
        raise HTTPException(status_code=400, detail=f"缺少必填字段: {missing_str}")

    request_uuid = f"dispatch-{uuid4()}"

    try:
        instance_code = manager.create_instance(
            user_id=user_id,
            form_data=form_data,
            uuid=request_uuid,
            approval_code_override=approval_code,
        )
    except ApprovalAPIError as exc:
        logger.exception("Failed to create approval instance: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: broad-except - surface unexpected errors
        logger.exception("Unexpected error during approval creation: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create approval instance") from exc

    update_local_task(
        instance_code,
        approval_instance_code=instance_code,
        approval_status="PENDING",
        approval_type=payload.approval_type,
    )

    approval_url = format_approval_url(instance_code, approval_code)
    return {
        "success": True,
        "message": "派工申请已提交,等待审批",
        "instance_code": instance_code,
        "approval_url": approval_url,
    }


@router.get("/types")
async def list_approval_types(
    current_user: Dict[str, Any] = Depends(require_permission("task:read"))
) -> Dict[str, Any]:
    """获取所有可用的审批类型供前端选择。"""
    return {
        "success": True,
        "approval_types": approval_config.get_available_approval_types(),
    }


@router.put("/{instance_code}")
async def update_dispatch(
    instance_code: str,
    payload: UpdateDispatchRequest,
    current_user: Dict[str, Any] = Depends(require_permission("task:update"))
) -> Dict[str, Any]:
    """修改派工(撤回旧实例并创建新实例)。

    步骤:
        1. 读取原审批实例并合并最新字段
        2. 撤回原审批实例
        3. 以新参数创建替换实例,并标注来源实例编号
        4. 更新本地缓存中的审批实例编号

    Returns:
        dict: 包含success/message/old_instance_code/new_instance_code等信息
    """
    logger.info("Update dispatch request for instance %s", instance_code)

    manager = get_effective_manager()
    user_id = resolve_user_id(payload.user_id)

    try:
        original_detail = manager.get_instance_detail(instance_code)
        original_form = parse_form_data(original_detail.get("form"))
    except ApprovalAPIError as exc:
        logger.exception("Failed to fetch approval detail before update: %s", exc)
        raise HTTPException(status_code=404, detail="Approval instance not found") from exc
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error while reading approval detail: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to read approval detail") from exc

    updates = {
        "task_name": payload.task_name,
        "assignee": payload.assignee,
        "priority": payload.priority,
        "start_date": payload.start_date.isoformat() if payload.start_date else None,
        "end_date": payload.end_date.isoformat() if payload.end_date else None,
    }
    if payload.assignee and not assignee_exists(payload.assignee):
        logger.warning("Updated assignee %s not found in local cache", payload.assignee)
    new_form = merge_form_data(original_form, updates)
    new_form["modified_instance_code"] = instance_code
    new_form["remark"] = payload.remark or f"修改自{instance_code}"

    try:
        manager.cancel_instance(instance_code, user_id)
    except ApprovalAPIError as exc:
        logger.exception("Failed to cancel original approval instance %s: %s", instance_code, exc)
        raise HTTPException(status_code=502, detail="Failed to cancel original approval instance") from exc
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error canceling approval instance %s: %s", instance_code, exc)
        raise HTTPException(status_code=500, detail="Failed to cancel approval instance") from exc

    request_uuid = f"dispatch-update-{uuid4()}"

    try:
        new_instance_code = manager.create_instance(
            user_id=user_id,
            form_data=new_form,
            uuid=request_uuid,
        )
    except ApprovalAPIError as exc:
        logger.exception("Failed to create replacement approval instance for %s: %s", instance_code, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error creating replacement approval instance: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create replacement approval instance") from exc

    update_fields: Dict[str, Any] = {
        "approval_instance_code": new_instance_code,
        "approval_status": "PENDING",
    }
    if payload.assignee:
        update_fields["assignee"] = payload.assignee
    update_local_task(instance_code, **update_fields)

    return {
        "success": True,
        "message": "派工已修改,等待审批",
        "old_instance_code": instance_code,
        "new_instance_code": new_instance_code,
        "approval_url": format_approval_url(new_instance_code),
    }


@router.post("/{instance_code}/transfer")
async def transfer_dispatch(
    instance_code: str,
    payload: TransferDispatchRequest,
    current_user: Dict[str, Any] = Depends(require_permission("task:update"))
) -> Dict[str, Any]:
    """转交派工(撤回旧实例并转交给新工程师)。

    流程:
        1. 获取原审批详情,保留表单上下文
        2. 撤回原实例并创建新的审批实例(更新派工人)
        3. 可选地抄送原派工人,告知转交原因
        4. 更新本地缓存的审批编号与派工人

    Returns:
        dict: 包含success/message/old_instance_code/new_instance_code及链接
    """
    logger.info(
        "Transfer dispatch request for instance %s -> %s",
        instance_code,
        payload.new_assignee,
    )

    manager = get_effective_manager()
    user_id = resolve_user_id(payload.user_id)

    try:
        original_detail = manager.get_instance_detail(instance_code)
        original_form = parse_form_data(original_detail.get("form"))
    except ApprovalAPIError as exc:
        logger.exception("Failed to fetch approval detail before transfer: %s", exc)
        raise HTTPException(status_code=404, detail="Approval instance not found") from exc
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error while reading approval detail for transfer: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to read approval detail") from exc

    if not assignee_exists(payload.new_assignee):
        logger.warning("New assignee %s not found in local cache", payload.new_assignee)

    if payload.reason:
        logger.info(
            "Transfer reason for %s -> %s: %s",
            instance_code,
            payload.new_assignee,
            payload.reason,
        )

    original_assignee = original_form.get("assignee")
    new_form = dict(original_form)
    new_form["assignee"] = payload.new_assignee
    if payload.reason:
        new_form["transfer_reason"] = payload.reason
    new_form["transferred_from"] = original_assignee
    new_form["modified_instance_code"] = instance_code

    try:
        manager.cancel_instance(instance_code, user_id)
    except ApprovalAPIError as exc:
        logger.exception("Failed to cancel original approval instance %s during transfer: %s", instance_code, exc)
        raise HTTPException(status_code=502, detail="Failed to cancel original approval instance") from exc
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error canceling approval instance during transfer: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to cancel approval instance") from exc

    request_uuid = f"dispatch-transfer-{uuid4()}"

    try:
        new_instance_code = manager.create_instance(
            user_id=user_id,
            form_data=new_form,
            uuid=request_uuid,
        )
    except ApprovalAPIError as exc:
        logger.exception("Failed to create transfer approval instance: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error creating transfer approval instance: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create transfer approval instance") from exc

    original_assignee_id = (
        original_form.get("assignee_id")
        or original_form.get("assignee_user_id")
        or original_form.get("assignee_uid")
    )
    if original_assignee_id:
        comment = f"派工已转交至{payload.new_assignee}"
        if payload.reason:
            comment = f"{comment}，原因：{payload.reason}"
        try:
            manager.cc_instance(
                new_instance_code,
                [original_assignee_id],
                comment,
            )
        except ApprovalAPIError as exc:
            logger.warning("Failed to CC original assignee %s: %s", original_assignee_id, exc)
        except Exception as exc:  # noqa: broad-except
            logger.warning("Unexpected error CCing original assignee %s: %s", original_assignee_id, exc)
    else:
        logger.warning("Skip CC for instance %s: original assignee id missing", instance_code)

    update_local_task(
        instance_code,
        approval_instance_code=new_instance_code,
        approval_status="PENDING",
        assignee=payload.new_assignee,
    )

    return {
        "success": True,
        "message": f"派工已转交至{payload.new_assignee}",
        "old_instance_code": instance_code,
        "new_instance_code": new_instance_code,
        "approval_url": format_approval_url(new_instance_code),
    }


@router.delete("/{instance_code}")
async def close_dispatch(
    instance_code: str,
    payload: CloseDispatchRequest,
    current_user: Dict[str, Any] = Depends(require_permission("task:delete"))
) -> Dict[str, Any]:
    """关闭派工(撤回审批实例)。

    步骤:
        1. 校验操作人并撤回飞书审批实例
        2. 更新本地任务缓存的审批状态

    Returns:
        dict: 包含success/message/instance_code字段
    """
    logger.info("Close dispatch request for instance %s", instance_code)

    manager = get_effective_manager()
    user_id = resolve_user_id(payload.user_id)

    if payload.reason:
        logger.info(
            "Close dispatch %s reason: %s",
            instance_code,
            payload.reason,
        )

    try:
        manager.cancel_instance(instance_code, user_id)
    except ApprovalAPIError as exc:
        logger.exception("Failed to cancel approval instance %s: %s", instance_code, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error canceling approval instance %s: %s", instance_code, exc)
        raise HTTPException(status_code=500, detail="Failed to cancel approval instance") from exc

    update_local_task(instance_code, approval_status="CANCELED")

    return {
        "success": True,
        "message": "派工已关闭",
        "instance_code": instance_code,
    }


@router.post("/{instance_code}/complete")
async def complete_dispatch(
    instance_code: str,
    payload: CompleteDispatchRequest,
    current_user: Dict[str, Any] = Depends(require_permission("task:update"))
) -> Dict[str, Any]:
    """完成派工(标记任务完成)。

    流程:
        1. 获取审批详情并校验状态为APPROVED
        2. 更新本地缓存的审批状态与申请状态
        3. 记录操作日志,等待后续同步刷新

    Returns:
        dict: 包含success/message/instance_code字段
    """
    logger.info("Complete dispatch request for instance %s", instance_code)

    manager = get_effective_manager()
    user_id = resolve_user_id(payload.user_id)

    try:
        detail = manager.get_instance_detail(instance_code)
    except ApprovalAPIError as exc:
        logger.exception("Failed to fetch approval instance %s before completion: %s", instance_code, exc)
        raise HTTPException(status_code=404, detail="Approval instance not found") from exc
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error fetching approval instance detail %s: %s", instance_code, exc)
        raise HTTPException(status_code=500, detail="Failed to read approval detail") from exc

    status = detail.get("status")
    if status != "APPROVED":
        logger.warning(
            "Attempt to complete instance %s with status %s", instance_code, status
        )
        raise HTTPException(status_code=400, detail="审批未通过,无法标记完成")

    update_fields: Dict[str, Any] = {"approval_status": "COMPLETED", "application_status": "已完成"}
    update_local_task(instance_code, **update_fields)

    if payload.completion_note:
        logger.info(
            "Completion note for instance %s: %s",
            instance_code,
            payload.completion_note,
        )

    # Completion is a local status update; cancellation not required but logged
    logger.info("Dispatch instance %s marked as completed by %s", instance_code, user_id)

    return {
        "success": True,
        "message": "派工已标记为完成",
        "instance_code": instance_code,
    }


@router.get("/{instance_code}", response_model=ApprovalDetailResponse)
async def get_approval_detail(
    instance_code: str,
    current_user: Dict[str, Any] = Depends(require_permission("task:read"))
) -> ApprovalDetailResponse:
    """查询审批实例详情。

    返回内容:
        - 审批基础信息(名称/状态)
        - 表单数据字典
        - 审批节点任务(task_list)
        - 审批时间线(timeline)

    Returns:
        ApprovalDetailResponse: 标准化的审批详情响应
    """
    logger.info("Query approval detail for instance %s", instance_code)

    manager = get_effective_manager()

    try:
        detail = manager.get_instance_detail(instance_code)
    except ApprovalAPIError as exc:
        logger.exception("Failed to fetch approval detail %s: %s", instance_code, exc)
        raise HTTPException(status_code=404, detail="Approval instance not found") from exc
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error fetching approval detail %s: %s", instance_code, exc)
        raise HTTPException(status_code=500, detail="Failed to read approval detail") from exc

    form_data = parse_form_data(detail.get("form"))
    task_list = detail.get("task_list") or detail.get("tasks") or []
    if not isinstance(task_list, list):
        task_list = []
    timeline = detail.get("timeline") or detail.get("timeline_nodes") or []
    if not isinstance(timeline, list):
        timeline = []

    return ApprovalDetailResponse(
        success=True,
        message="审批详情获取成功",
        instance_code=instance_code,
        approval_name=detail.get("approval_name") or detail.get("name"),
        status=detail.get("status"),
        form_data=form_data,
        task_list=task_list,
        timeline=timeline,
    )
