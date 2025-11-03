#!/usr/bin/env python3
"""
获取飞书审批定义的详细信息,包括所有表单字段
"""
import json
import os
import sys
from typing import Dict, Any

import requests
from feishu_reader import FeishuBitableReader


def get_approval_definition(app_id: str, app_secret: str, approval_code: str) -> Dict[str, Any]:
    """获取审批定义详情"""
    # 获取access token
    reader = FeishuBitableReader(app_id, app_secret)
    token = reader._get_tenant_access_token()

    if not token:
        raise Exception("无法获取tenant_access_token")

    # 调用审批定义接口
    url = f"https://open.feishu.cn/open-apis/approval/v4/approvals/{approval_code}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    response = requests.get(url, headers=headers, timeout=15)

    if response.status_code != 200:
        raise Exception(f"API请求失败: {response.status_code} - {response.text}")

    data = response.json()

    if data.get("code") != 0:
        raise Exception(f"API返回错误: {data.get('msg')} - {data}")

    return data.get("data", {})


def print_approval_fields(approval_data: Dict[str, Any], approval_name: str):
    """打印审批定义的字段信息"""
    print(f"\n{'='*80}")
    print(f"审批定义: {approval_name}")
    print(f"{'='*80}\n")

    print(f"审批名称: {approval_data.get('approval_name', 'N/A')}")
    print(f"审批Code: {approval_data.get('approval_code', 'N/A')}")
    print(f"描述: {approval_data.get('description', 'N/A')}")
    print(f"\n表单字段:")
    print("-" * 80)

    form_content = approval_data.get('form', {})
    form_list = form_content.get('form_content', [])

    if not form_list:
        print("未找到表单字段")
        return

    for idx, field in enumerate(form_list, 1):
        field_id = field.get('id', 'N/A')
        field_name = field.get('name', 'N/A')
        field_type = field.get('type', 'N/A')
        required = field.get('required', False)

        print(f"\n{idx}. 字段ID: {field_id}")
        print(f"   名称: {field_name}")
        print(f"   类型: {field_type}")
        print(f"   必填: {'是' if required else '否'}")

        # 如果有选项(如下拉框),打印选项
        if 'option' in field and field['option']:
            options = field['option']
            if isinstance(options, list):
                print(f"   选项:")
                for opt in options:
                    opt_key = opt.get('key', 'N/A')
                    opt_value = opt.get('value', 'N/A')
                    print(f"     - {opt_key}: {opt_value}")

    print("\n" + "=" * 80)


def main():
    # 从环境变量获取配置
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        print("错误: 请设置FEISHU_APP_ID和FEISHU_APP_SECRET环境变量")
        sys.exit(1)

    # 两个审批定义的code
    daily_work_code = os.getenv("FEISHU_APPROVAL_CODE")  # 公司日常工单
    eisoo_vendor_code = os.getenv("FEISHU_APPROVAL_CODE_EISOO", "1258F9D1-FFEB-4C1F-A0ED-200A7807261A")  # 爱数原厂派单

    if not daily_work_code:
        print("错误: 请设置FEISHU_APPROVAL_CODE环境变量(公司日常工单)")
        sys.exit(1)

    try:
        # 获取公司日常工单定义
        print("\n正在获取公司日常工单定义...")
        daily_work_data = get_approval_definition(app_id, app_secret, daily_work_code)
        print_approval_fields(daily_work_data, "公司日常工单")

        # 保存到JSON文件
        with open("approval_daily_work.json", "w", encoding="utf-8") as f:
            json.dump(daily_work_data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 已保存到: approval_daily_work.json")

        # 获取爱数原厂派单定义
        print("\n正在获取爱数原厂派单定义...")
        eisoo_vendor_data = get_approval_definition(app_id, app_secret, eisoo_vendor_code)
        print_approval_fields(eisoo_vendor_data, "爱数原厂派单")

        # 保存到JSON文件
        with open("approval_eisoo_vendor.json", "w", encoding="utf-8") as f:
            json.dump(eisoo_vendor_data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 已保存到: approval_eisoo_vendor.json")

    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
