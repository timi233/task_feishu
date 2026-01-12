"""
飞书通讯录API封装模块

用途:
    从飞书通讯录获取用户(工程师)列表

权限要求:
    - contact:user:read (获取通讯录用户信息)

API文档:
    https://open.feishu.cn/document/server-docs/contact-v3/user/list
"""

import requests
import time
import json
import logging
from typing import Dict, List, Any, Optional

from feishu_reader import FeishuBitableReader

# 日志由main.py统一配置
logger = logging.getLogger(__name__)


class FeishuContactsReader:
    """飞书通讯录API读取类"""

    def __init__(self, app_id: str, app_secret: str, timeout: int = 15):
        """
        初始化飞书通讯录读取器

        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            timeout: 请求超时时间(秒)
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.timeout = timeout
        # 复用FeishuBitableReader的token管理
        self._token_provider = FeishuBitableReader(app_id, app_secret, timeout=timeout)

    def _get_tenant_access_token(self) -> Optional[str]:
        """获取tenant_access_token (复用FeishuBitableReader的实现)"""
        token = self._token_provider._get_tenant_access_token()
        if not token:
            logger.error("Unable to obtain tenant_access_token")
        return token

    def get_users(
        self,
        department_id: Optional[str] = None,
        page_size: int = 50,
        user_id_type: str = "user_id"
    ) -> List[Dict[str, Any]]:
        """
        获取通讯录用户列表 (支持分页自动获取全部)

        Args:
            department_id: 部门ID,为None时获取所有部门用户
            page_size: 每页数量(最大50)
            user_id_type: 用户ID类型 (user_id, union_id, open_id)

        Returns:
            List[Dict]: 用户列表,每个元素包含:
                - user_id: 用户ID
                - name: 姓名
                - en_name: 英文名
                - email: 邮箱
                - mobile: 手机号
                - department_ids: 部门ID列表
                - status: 用户状态 (is_frozen, is_resigned, is_activated等)

        API文档:
            https://open.feishu.cn/document/server-docs/contact-v3/user/list
        """
        token = self._get_tenant_access_token()
        if not token:
            logger.error("Failed to get access token, cannot fetch users")
            return []

        users = []
        page_token = None
        has_more = True

        while has_more:
            url = "https://open.feishu.cn/open-apis/contact/v3/users"
            params = {
                "user_id_type": user_id_type,
                "page_size": min(page_size, 50)  # 最大50
            }

            if department_id:
                params["department_id"] = department_id

            if page_token:
                params["page_token"] = page_token

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }

            try:
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()

                if result.get("code") == 0:
                    data = result.get("data", {})
                    items = data.get("items", [])
                    users.extend(items)

                    logger.debug(f"Fetched {len(items)} users, total so far: {len(users)}")

                    # 检查是否还有更多数据
                    page_token = data.get("page_token")
                    has_more = data.get("has_more", False)
                else:
                    logger.error(f"Failed to fetch users: {result}")
                    break

            except Exception as e:
                logger.exception(f"Exception while fetching users: {e}")
                break

        logger.info(f"Finished fetching all users. Total: {len(users)}")
        return users

    def filter_active_users(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤在职用户 (未冻结、未离职、已激活)

        Args:
            users: 原始用户列表

        Returns:
            List[Dict]: 在职用户列表
        """
        active_users = []

        for user in users:
            status = user.get("status", {})

            # 检查用户状态
            is_frozen = status.get("is_frozen", False)
            is_resigned = status.get("is_resigned", False)
            is_activated = status.get("is_activated", True)

            # 只保留在职用户: 未冻结、未离职、已激活
            if not is_frozen and not is_resigned and is_activated:
                active_users.append(user)

        logger.info(f"Filtered active users: {len(active_users)}/{len(users)}")
        return active_users

    def transform_to_engineers(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将飞书用户数据转换为工程师数据格式

        Args:
            users: 飞书API返回的用户列表

        Returns:
            List[Dict]: 工程师数据列表,包含:
                - user_id: 用户ID
                - name: 姓名
                - department_ids: 部门ID列表(JSON字符串)
                - mobile: 手机号
                - email: 邮箱
                - status: 状态(1=在职, 0=离职)
        """
        engineers = []

        for user in users:
            status_data = user.get("status", {})
            is_resigned = status_data.get("is_resigned", False)

            # 部门ID列表转为JSON字符串
            department_ids = user.get("department_ids", [])
            department_ids_str = json.dumps(department_ids, ensure_ascii=False) if department_ids else None

            engineer = {
                "user_id": user.get("user_id") or user.get("open_id"),
                "name": user.get("name", ""),
                "department_ids": department_ids_str,
                "mobile": user.get("mobile", ""),
                "email": user.get("email", ""),
                "status": 0 if is_resigned else 1
            }

            engineers.append(engineer)

        logger.debug(f"Transformed {len(engineers)} users to engineer format")
        return engineers


if __name__ == "__main__":
    import os

    # 测试代码
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        logger.error("Missing FEISHU_APP_ID or FEISHU_APP_SECRET environment variables")
        exit(1)

    reader = FeishuContactsReader(app_id, app_secret)

    logger.info("开始从飞书通讯录获取用户...")
    users = reader.get_users(page_size=50)

    if users:
        logger.info(f"成功获取到 {len(users)} 个用户")

        # 过滤在职用户
        active_users = reader.filter_active_users(users)
        logger.info(f"在职用户: {len(active_users)} 个")

        # 转换为工程师格式
        engineers = reader.transform_to_engineers(active_users)

        # 打印前3个工程师信息作为示例
        for i, engineer in enumerate(engineers[:3]):
            logger.info(f"--- Engineer {i + 1} ---")
            logger.info(f"Name: {engineer['name']}")
            logger.info(f"User ID: {engineer['user_id']}")
            logger.info(f"Mobile: {engineer['mobile']}")
            logger.info(f"Email: {engineer['email']}")
            logger.info(f"Status: {'在职' if engineer['status'] == 1 else '离职'}")

        if len(engineers) > 3:
            logger.info(f"... and {len(engineers) - 3} more engineers.")
    else:
        logger.warning("未能获取到任何用户。请检查权限配置!")
