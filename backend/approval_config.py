#!/usr/bin/env python3
"""
审批类型配置模块

定义不同工单类型及其对应的审批流程配置
"""

import os
from typing import Dict, List, Any


# ===== 审批类型定义 =====

APPROVAL_TYPES: Dict[str, Dict[str, Any]] = {
    "daily_work": {
        "name": "公司日常工单",
        "display_name": "公司日常工单",
        "description": "公司内部日常售后工单,包含一般性技术支持和问题处理",
        "approval_code_env": "FEISHU_APPROVAL_CODE",  # 环境变量名
        "required_fields": [
            "task_name",      # 任务名称
            "assignee",       # 派工人员
            "priority",       # 优先级
            "start_date",     # 开始日期
            "end_date"        # 结束日期
        ],
        "optional_fields": [
            "description",    # 工作内容描述
            "customer_name"   # 客户名称(可选)
        ],
        "field_labels": {
            "task_name": "任务名称",
            "assignee": "派工人员",
            "priority": "优先级",
            "start_date": "服务开始时间",
            "end_date": "服务结束时间",
            "description": "工作内容",
            "customer_name": "客户公司名称"
        },
        "priority_options": ["非常紧急", "紧急", "重要", "普通"]
    },

    "eisoo_vendor": {
        "name": "爱数原厂派单",
        "display_name": "爱数原厂派单",
        "description": "爱数原厂技术支持派单,涉及原厂产品的技术问题和售后服务",
        "approval_code_env": "FEISHU_APPROVAL_CODE_EISOO",  # 环境变量名
        "required_fields": [
            "customer_name",      # 客户名称
            "issue_type",         # 问题类型
            "urgency",            # 紧急程度
            "contact_person",     # 联系人
            "contact_phone",      # 联系电话
            "assignee",           # 处理工程师
            "start_date",         # 预计开始时间
            "end_date"            # 预计完成时间
        ],
        "optional_fields": [
            "detailed_description",  # 问题详细描述
            "attachment_urls",       # 附件链接
            "product_model",         # 产品型号
            "serial_number",         # 序列号
            "warranty_status"        # 保修状态
        ],
        "field_labels": {
            "customer_name": "客户名称",
            "issue_type": "问题类型",
            "urgency": "紧急程度",
            "contact_person": "联系人",
            "contact_phone": "联系电话",
            "assignee": "处理工程师",
            "start_date": "预计开始时间",
            "end_date": "预计完成时间",
            "detailed_description": "问题详细描述",
            "attachment_urls": "附件链接",
            "product_model": "产品型号",
            "serial_number": "序列号",
            "warranty_status": "保修状态"
        },
        "issue_type_options": [
            "硬件故障",
            "软件故障",
            "性能问题",
            "配置调整",
            "升级维护",
            "咨询服务",
            "其他"
        ],
        "urgency_options": ["紧急", "高", "中", "低"]
    }
}


# ===== 辅助函数 =====

def get_approval_config(approval_type: str) -> Dict[str, Any]:
    """
    获取指定审批类型的配置

    Args:
        approval_type: 审批类型 (daily_work 或 eisoo_vendor)

    Returns:
        审批配置字典

    Raises:
        ValueError: 如果审批类型不存在
    """
    if approval_type not in APPROVAL_TYPES:
        raise ValueError(
            f"Unknown approval type: {approval_type}. "
            f"Valid types: {', '.join(APPROVAL_TYPES.keys())}"
        )

    return APPROVAL_TYPES[approval_type]


def get_approval_code(approval_type: str) -> str:
    """
    获取指定审批类型的审批定义Code

    Args:
        approval_type: 审批类型

    Returns:
        审批定义Code (从环境变量读取)

    Raises:
        ValueError: 如果审批类型不存在或环境变量未配置
    """
    config = get_approval_config(approval_type)
    env_var_name = config["approval_code_env"]

    approval_code = os.getenv(env_var_name)
    if not approval_code:
        raise ValueError(
            f"Approval code not configured for type '{approval_type}'. "
            f"Please set environment variable: {env_var_name}"
        )

    return approval_code


def get_available_approval_types() -> List[Dict[str, str]]:
    """
    获取所有可用的审批类型列表(用于前端选择器)

    Returns:
        审批类型列表,每个元素包含 type, name, description
    """
    return [
        {
            "type": approval_type,
            "name": config["display_name"],
            "description": config["description"]
        }
        for approval_type, config in APPROVAL_TYPES.items()
    ]


def validate_form_data(approval_type: str, form_data: Dict[str, Any]) -> List[str]:
    """
    验证表单数据是否包含所有必需字段

    Args:
        approval_type: 审批类型
        form_data: 表单数据字典

    Returns:
        缺失字段列表(空列表表示验证通过)
    """
    config = get_approval_config(approval_type)
    required_fields = config["required_fields"]

    missing_fields = []
    for field in required_fields:
        if field not in form_data or not form_data[field]:
            field_label = config["field_labels"].get(field, field)
            missing_fields.append(field_label)

    return missing_fields


# ===== 默认值 =====

DEFAULT_APPROVAL_TYPE = "daily_work"  # 默认工单类型(向后兼容)


if __name__ == "__main__":
    # 测试代码
    import json

    print("=== 审批类型配置测试 ===\n")

    print("1. 可用审批类型:")
    for item in get_available_approval_types():
        print(f"   - {item['name']} ({item['type']}): {item['description']}")

    print("\n2. 日常工单配置:")
    daily_config = get_approval_config("daily_work")
    print(f"   必填字段: {', '.join(daily_config['required_fields'])}")
    print(f"   选填字段: {', '.join(daily_config['optional_fields'])}")

    print("\n3. 爱数原厂派单配置:")
    eisoo_config = get_approval_config("eisoo_vendor")
    print(f"   必填字段: {', '.join(eisoo_config['required_fields'])}")
    print(f"   问题类型选项: {', '.join(eisoo_config['issue_type_options'])}")

    print("\n4. 表单验证测试:")
    test_form = {
        "customer_name": "测试公司",
        "issue_type": "硬件故障"
        # 缺少其他必填字段
    }
    missing = validate_form_data("eisoo_vendor", test_form)
    if missing:
        print(f"   缺失字段: {', '.join(missing)}")
    else:
        print("   验证通过")
