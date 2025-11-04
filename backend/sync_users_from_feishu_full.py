"""从飞书组织架构完整同步所有用户

遍历整个组织架构，获取所有部门的所有用户

使用方式:
    python sync_users_from_feishu_full.py

日期: 2025-11-03
"""

import logging
import sys
import os
from typing import Dict, List, Any, Set

sys.path.insert(0, os.path.dirname(__file__))

from task_db import get_db_connection
import requests
import time

# 手动加载.env文件（如果不在环境变量中）
if not os.getenv('FEISHU_APP_ID'):
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeishuOrgReader:
    """飞书组织架构读取器"""

    def __init__(self, app_id: str, app_secret: str, timeout: int = 15):
        self.app_id = app_id
        self.app_secret = app_secret
        self.timeout = timeout
        self._token = None
        self._token_expires_at = 0

    def _get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        if self._token and time.time() < self._token_expires_at:
            return self._token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                self._token = result.get("tenant_access_token")
                self._token_expires_at = time.time() + result.get("expire", 7200) - 300  # 提前5分钟过期
                logger.info("✅ 成功获取tenant_access_token")
                return self._token
            else:
                logger.error(f"获取token失败: {result}")
                return None
        except Exception as e:
            logger.exception(f"获取token异常: {e}")
            return None

    def get_all_departments(self) -> List[Dict[str, Any]]:
        """获取所有部门（递归遍历）"""
        token = self._get_tenant_access_token()
        if not token:
            return []

        all_departments = []

        # 从根部门开始遍历（parent_department_id为"0"表示根部门）
        departments_to_fetch = ["0"]
        fetched_ids = set()

        while departments_to_fetch:
            parent_id = departments_to_fetch.pop(0)

            if parent_id in fetched_ids:
                continue
            fetched_ids.add(parent_id)

            url = "https://open.feishu.cn/open-apis/contact/v3/departments"
            params = {
                "parent_department_id": parent_id,
                "fetch_child": False,
                "page_size": 50
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }

            page_token = None
            has_more = True

            while has_more:
                if page_token:
                    params["page_token"] = page_token

                try:
                    response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                    response.raise_for_status()
                    result = response.json()

                    if result.get("code") == 0:
                        data = result.get("data", {})
                        items = data.get("items", [])

                        for dept in items:
                            all_departments.append(dept)
                            # 将子部门ID加入待遍历列表
                            dept_id = dept.get("open_department_id")
                            if dept_id:
                                departments_to_fetch.append(dept_id)

                        logger.debug(f"获取到 {len(items)} 个部门（父部门ID: {parent_id}）")

                        has_more = data.get("has_more", False)
                        page_token = data.get("page_token")
                    else:
                        logger.error(f"获取部门失败: {result}")
                        break
                except Exception as e:
                    logger.exception(f"获取部门异常: {e}")
                    break

        logger.info(f"✅ 共获取 {len(all_departments)} 个部门")
        return all_departments

    def get_users_in_department(self, department_id: str) -> List[Dict[str, Any]]:
        """获取指定部门的所有用户"""
        token = self._get_tenant_access_token()
        if not token:
            return []

        users = []
        url = "https://open.feishu.cn/open-apis/contact/v3/users"
        params = {
            "department_id": department_id,
            "page_size": 50,
            "user_id_type": "user_id"
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        page_token = None
        has_more = True

        while has_more:
            if page_token:
                params["page_token"] = page_token

            try:
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()

                if result.get("code") == 0:
                    data = result.get("data", {})
                    items = data.get("items", [])
                    users.extend(items)

                    has_more = data.get("has_more", False)
                    page_token = data.get("page_token")
                else:
                    logger.error(f"获取部门 {department_id} 用户失败: {result}")
                    break
            except Exception as e:
                logger.exception(f"获取部门 {department_id} 用户异常: {e}")
                break

        return users

    def get_all_users(self) -> List[Dict[str, Any]]:
        """获取组织架构中的所有用户（去重）"""
        # 1. 获取所有部门
        departments = self.get_all_departments()

        if not departments:
            logger.warning("未获取到任何部门，尝试获取根部门用户")
            # 如果没有部门信息，尝试直接获取用户（不指定部门ID）
            return self.get_users_without_department()

        # 2. 遍历所有部门，获取用户
        all_users_dict = {}  # 使用dict去重，key为user_id

        for dept in departments:
            dept_id = dept.get("open_department_id")
            dept_name = dept.get("name")

            logger.info(f"正在获取部门 [{dept_name}] 的用户...")
            users = self.get_users_in_department(dept_id)

            for user in users:
                user_id = user.get("user_id")
                if user_id and user_id not in all_users_dict:
                    # 添加部门名称信息
                    if "department_ids" in user and len(user["department_ids"]) > 0:
                        user["primary_department_name"] = dept_name
                    all_users_dict[user_id] = user

            logger.debug(f"  部门 [{dept_name}] 有 {len(users)} 个用户")
            time.sleep(0.1)  # 避免API限流

        logger.info(f"✅ 共获取 {len(all_users_dict)} 个唯一用户")
        return list(all_users_dict.values())

    def get_users_without_department(self) -> List[Dict[str, Any]]:
        """获取用户（不指定部门ID）"""
        token = self._get_tenant_access_token()
        if not token:
            return []

        users = []
        url = "https://open.feishu.cn/open-apis/contact/v3/users"
        params = {
            "page_size": 50,
            "user_id_type": "user_id"
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        page_token = None
        has_more = True

        while has_more:
            if page_token:
                params["page_token"] = page_token

            try:
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()

                if result.get("code") == 0:
                    data = result.get("data", {})
                    items = data.get("items", [])
                    users.extend(items)

                    has_more = data.get("has_more", False)
                    page_token = data.get("page_token")
                else:
                    logger.error(f"获取用户失败: {result}")
                    break
            except Exception as e:
                logger.exception(f"获取用户异常: {e}")
                break

        logger.info(f"✅ 获取 {len(users)} 个用户（不指定部门）")
        return users


def sync_users_from_feishu_org() -> Dict[str, Any]:
    """从飞书组织架构同步所有用户

    Returns:
        Dict: 同步结果统计
    """
    logger.info("开始从飞书组织架构同步用户数据...")

    stats = {
        "success": False,
        "total_users": 0,
        "created": 0,
        "updated": 0,
        "errors": []
    }

    try:
        # 1. 初始化飞书组织架构客户端
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")

        if not app_id or not app_secret:
            raise ValueError("缺少飞书凭证（FEISHU_APP_ID 或 FEISHU_APP_SECRET）")

        reader = FeishuOrgReader(app_id, app_secret)

        # 2. 获取所有用户
        logger.info("拉取飞书组织架构所有用户...")
        all_users = reader.get_all_users()

        stats["total_users"] = len(all_users)
        logger.info(f"共拉取 {len(all_users)} 个用户")

        if not all_users:
            logger.warning("未获取到任何用户！")
            return stats

        # 3. 更新本地数据库
        with get_db_connection() as conn:
            cursor = conn.cursor()

            for user in all_users:
                user_id = user.get("user_id")
                name = user.get("name")
                email = user.get("email")
                mobile = user.get("mobile")
                dept_name = user.get("primary_department_name")

                # 获取用户状态
                status_info = user.get("status", {})
                is_resigned = status_info.get("is_resigned", False)
                is_frozen = status_info.get("is_frozen", False)
                is_activated = status_info.get("is_activated", False)

                # 状态判断：已激活且未离职且未冻结 = 在职
                status = 1 if (is_activated and not is_resigned and not is_frozen) else 0

                if not user_id or not name:
                    error_msg = f"用户缺少必要字段: {user}"
                    logger.warning(error_msg)
                    stats["errors"].append(error_msg)
                    continue

                # 检查用户是否已存在
                cursor.execute("SELECT user_id FROM engineers WHERE user_id = ?", (user_id,))
                exists = cursor.fetchone()

                if exists:
                    # 更新现有记录
                    cursor.execute("""
                        UPDATE engineers SET
                            name = ?,
                            email = ?,
                            mobile = ?,
                            department_name = ?,
                            status = ?,
                            synced_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    """, (name, email, mobile, dept_name, status, user_id))

                    stats["updated"] += 1
                    logger.debug(f"  更新用户: {name} ({user_id})")
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO engineers
                        (user_id, name, email, mobile, department_name, status, synced_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (user_id, name, email, mobile, dept_name, status))

                    stats["created"] += 1
                    logger.info(f"  新增用户: {name} ({user_id}) - {dept_name or '(无部门)'}")

            conn.commit()

        stats["success"] = True
        logger.info(f"✅ 同步完成: 新增{stats['created']}，更新{stats['updated']}")

        return stats

    except Exception as e:
        error_msg = f"同步失败: {str(e)}"
        logger.exception(error_msg)
        stats["errors"].append(error_msg)
        return stats


if __name__ == "__main__":
    print("\n" + "="*60)
    print("从飞书组织架构同步用户数据")
    print("="*60 + "\n")

    # 执行同步
    result = sync_users_from_feishu_org()

    # 打印结果
    print("\n" + "="*60)
    if result["success"]:
        print("✅ 同步成功")
        print(f"  总用户数: {result['total_users']}")
        print(f"  新增: {result['created']}")
        print(f"  更新: {result['updated']}")
    else:
        print("❌ 同步失败")
        if result["errors"]:
            print("\n错误信息:")
            for error in result["errors"]:
                print(f"  - {error}")
    print("="*60 + "\n")
