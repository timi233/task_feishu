"""
Pydantic模型定义

所有API请求和响应的数据模型
"""

import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, root_validator, validator

# 导入配置（用于validator）
import approval_config


# ===== 任务相关模型 =====

class TaskItem(BaseModel):
    record_id: str
    task_name: str
    assignee: str
    status: str # 展示状态（进行中/已结束/优先级）
    priority: Optional[str] = None # 原始优先级
    application_status: Optional[str] = None # 申请状态
    date: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    weekday: Optional[str] = None


class TaskGroup(BaseModel):
    monday: List[TaskItem]
    tuesday: List[TaskItem]
    wednesday: List[TaskItem]
    thursday: List[TaskItem]
    friday: List[TaskItem]
    weekend: List[TaskItem]


class TaskListResponse(BaseModel):
    """任务列表响应(扁平结构,供其他系统使用)"""
    total: int
    tasks: List[TaskItem]


# ===== 统计相关模型 =====

class EngineerStatsItem(BaseModel):
    """工程师统计信息"""
    engineer: str
    total_tasks: int
    very_urgent: int
    urgent: int
    important: int


class StatsResponse(BaseModel):
    """统计响应"""
    date_range: dict
    by_engineer: List[EngineerStatsItem]
    by_priority: dict


# ===== 审批相关模型 =====

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


# ===== 筛选器相关模型 =====

class FilterCreate(BaseModel):
    name: str
    conditions: List[dict]
    enabled: bool = True
    logic: str = "and"
