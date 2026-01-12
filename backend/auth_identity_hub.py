"""Identity Hub认证客户端

封装OAuth 2.0客户端逻辑，用于派工系统对接Identity Hub。

使用方法:
    from auth_identity_hub import IdentityHubClient

    client = IdentityHubClient()

    # 获取授权URL
    auth_url, state = client.get_authorization_url()

    # 用授权码换取token
    token_data = client.exchange_code_for_token(code, state)

    # 获取用户信息
    user_info = client.get_user_info(token_data["access_token"])
"""

import requests
import secrets
import os
from typing import Optional, Dict, Any, Tuple
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class IdentityHubClient:
    """Identity Hub OAuth 2.0客户端

    封装OAuth 2.0 Authorization Code Flow的客户端逻辑。
    """

    def __init__(
        self,
        hub_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ):
        """初始化Identity Hub客户端

        Args:
            hub_url: Identity Hub服务器地址（默认从环境变量读取）
            client_id: OAuth客户端ID（默认从环境变量读取）
            client_secret: OAuth客户端密钥（默认从环境变量读取）
            redirect_uri: 回调地址（默认从环境变量读取）
        """
        self.hub_url = hub_url or os.getenv("IDENTITY_HUB_URL", "http://192.168.101.13:9000")
        self.client_id = client_id or os.getenv("IDENTITY_HUB_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("IDENTITY_HUB_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("IDENTITY_HUB_REDIRECT_URI")

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError(
                "Missing OAuth configuration. Please set IDENTITY_HUB_CLIENT_ID, "
                "IDENTITY_HUB_CLIENT_SECRET, and IDENTITY_HUB_REDIRECT_URI in .env"
            )

        logger.info(f"Initialized IdentityHubClient: {self.hub_url}")

    def get_authorization_url(
        self,
        scope: str = "openid profile email",
        state: Optional[str] = None
    ) -> Tuple[str, str]:
        """获取OAuth授权URL

        生成授权URL，引导用户跳转到Identity Hub进行登录授权。

        Args:
            scope: 授权范围（默认: "openid profile email"）
            state: CSRF防护token（不提供则自动生成）

        Returns:
            Tuple[str, str]: (授权URL, state)

        Example:
            auth_url, state = client.get_authorization_url()
            # 保存state到session
            # 跳转到auth_url
        """
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state
        }

        # 构造URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{self.hub_url}/oauth/authorize?{query_string}"

        logger.info(f"Generated authorization URL (state={state[:16]}...)")
        return auth_url, state

    def exchange_code_for_token(
        self,
        code: str,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """用授权码换取access_token

        在OAuth回调中，用授权码换取access_token和refresh_token。

        Args:
            code: 授权码（从回调URL参数获取）
            state: CSRF防护token（应与get_authorization_url返回的state一致）

        Returns:
            Dict: Token响应
                {
                    "access_token": "xxx",
                    "token_type": "Bearer",
                    "expires_in": 7200,
                    "refresh_token": "xxx",
                    "scope": "openid profile email"
                }

        Raises:
            Exception: 如果token请求失败

        Example:
            # 在回调端点中
            code = request.args.get('code')
            callback_state = request.args.get('state')

            # 验证state
            if callback_state != session.get('oauth_state'):
                raise ValueError("Invalid state")

            token_data = client.exchange_code_for_token(code, callback_state)
            session['access_token'] = token_data['access_token']
            session['refresh_token'] = token_data['refresh_token']
        """
        token_url = f"{self.hub_url}/oauth/token"

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        try:
            response = requests.post(token_url, data=data, timeout=15)
            response.raise_for_status()

            token_data = response.json()
            logger.info(f"✅ Successfully exchanged code for token")

            return token_data

        except requests.exceptions.HTTPError as e:
            logger.exception(f"Token exchange failed: {e}")
            logger.error(f"Response: {e.response.text}")
            raise Exception(f"Failed to exchange code for token: {e.response.text}")
        except Exception as e:
            logger.exception(f"Token exchange error: {e}")
            raise

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """用access_token获取用户信息

        调用Identity Hub的UserInfo端点获取当前用户信息。

        Args:
            access_token: 访问令牌

        Returns:
            Dict: 用户信息
                {
                    "sub": "user_id",
                    "name": "张三",
                    "email": "zhangsan@company.com",
                    "mobile": "13800138000",
                    "avatar_url": "https://..."
                }

        Raises:
            Exception: 如果token无效或请求失败

        Example:
            access_token = session.get('access_token')
            user_info = client.get_user_info(access_token)
            print(f"当前用户: {user_info['name']}")
        """
        userinfo_url = f"{self.hub_url}/oauth/userinfo"

        try:
            response = requests.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15
            )
            response.raise_for_status()

            user_info = response.json()
            logger.info(f"✅ Got user info: {user_info.get('name')}")

            return user_info

        except requests.exceptions.HTTPError as e:
            logger.exception(f"UserInfo request failed: {e}")
            raise Exception(f"Failed to get user info: {e.response.text}")
        except Exception as e:
            logger.exception(f"UserInfo error: {e}")
            raise

    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新access_token

        当access_token过期时，使用refresh_token获取新的access_token。

        Args:
            refresh_token: 刷新令牌

        Returns:
            Dict: 新的Token响应
                {
                    "access_token": "new_xxx",
                    "token_type": "Bearer",
                    "expires_in": 7200,
                    "scope": "openid profile email"
                }

        Raises:
            Exception: 如果refresh_token无效或已过期

        Example:
            try:
                user_info = client.get_user_info(access_token)
            except Exception:
                # access_token过期，尝试刷新
                new_tokens = client.refresh_token(refresh_token)
                session['access_token'] = new_tokens['access_token']
                user_info = client.get_user_info(new_tokens['access_token'])
        """
        token_url = f"{self.hub_url}/oauth/token"

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        try:
            response = requests.post(token_url, data=data, timeout=15)
            response.raise_for_status()

            token_data = response.json()
            logger.info(f"✅ Successfully refreshed token")

            return token_data

        except requests.exceptions.HTTPError as e:
            logger.exception(f"Token refresh failed: {e}")
            raise Exception(f"Failed to refresh token: {e.response.text}")
        except Exception as e:
            logger.exception(f"Token refresh error: {e}")
            raise

    def revoke_token(self, token: str, token_type_hint: str = "access_token") -> bool:
        """撤销token

        撤销access_token或refresh_token（用于登出）。

        Args:
            token: 要撤销的token
            token_type_hint: Token类型提示（"access_token" 或 "refresh_token"）

        Returns:
            bool: 是否成功撤销

        Example:
            # 登出时撤销token
            access_token = session.get('access_token')
            refresh_token = session.get('refresh_token')

            client.revoke_token(access_token, "access_token")
            client.revoke_token(refresh_token, "refresh_token")

            session.clear()
        """
        revoke_url = f"{self.hub_url}/oauth/revoke"

        data = {
            "token": token,
            "token_type_hint": token_type_hint,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        try:
            response = requests.post(revoke_url, data=data, timeout=15)
            response.raise_for_status()

            logger.info(f"✅ Successfully revoked {token_type_hint}")
            return True

        except Exception as e:
            logger.warning(f"Failed to revoke token: {e}")
            return False

    def validate_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """验证token是否有效

        检查access_token是否有效，并返回用户信息。

        Args:
            access_token: 访问令牌

        Returns:
            Optional[Dict]: 如果token有效返回用户信息，否则返回None

        Example:
            access_token = request.cookies.get('access_token')

            user_info = client.validate_token(access_token)
            if user_info:
                print(f"用户已登录: {user_info['name']}")
            else:
                print("Token无效，需要重新登录")
        """
        try:
            return self.get_user_info(access_token)
        except Exception:
            return None

    def get_users(
        self,
        page: int = 1,
        page_size: int = 100,
        status: int = 1,
        department_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """从Identity Hub获取用户列表

        Args:
            page: 页码（默认1）
            page_size: 每页数量（默认100）
            status: 用户状态（1=在职，默认1）
            department_id: 部门过滤（可选）

        Returns:
            Dict: 用户列表响应
                {
                    "users": [...],
                    "total": 100,
                    "page": 1,
                    "page_size": 100
                }

        Example:
            response = client.get_users(page_size=50, status=1)
            users = response["users"]
        """
        url = f"{self.hub_url}/api/org/users"

        params = {
            "page": page,
            "page_size": page_size,
            "status": status
        }

        if department_id:
            params["department_id"] = department_id

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            logger.info(f"✅ Got {len(data.get('users', []))} users from Identity Hub")

            return data

        except Exception as e:
            logger.exception(f"Failed to get users: {e}")
            raise Exception(f"Failed to get users from Identity Hub: {e}")

    def get_user_detail(self, user_id: str) -> Dict[str, Any]:
        """从Identity Hub获取用户详细信息

        Args:
            user_id: 用户ID

        Returns:
            Dict: 用户详情
                {
                    "user_id": "...",
                    "name": "张三",
                    "email": "...",
                    "mobile": "...",
                    "primary_department": {...},
                    "all_departments": [...]
                }

        Example:
            user_detail = client.get_user_detail("ou-xxx")
            dept_name = user_detail["primary_department"]["name"]
        """
        url = f"{self.hub_url}/api/org/users/{user_id}"

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            user_detail = response.json()
            logger.info(f"✅ Got user detail: {user_detail.get('name')}")

            return user_detail

        except Exception as e:
            logger.exception(f"Failed to get user detail: {e}")
            raise Exception(f"Failed to get user detail from Identity Hub: {e}")

    def get_departments(self, format: str = "flat") -> Dict[str, Any]:
        """从Identity Hub获取部门列表

        Args:
            format: "tree" | "flat"（默认"flat"）

        Returns:
            Dict: 部门列表
                {
                    "departments": [...]
                }

        Example:
            response = client.get_departments(format="tree")
            departments = response["departments"]
        """
        url = f"{self.hub_url}/api/org/departments"
        params = {"format": format}

        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            logger.info(f"✅ Got {len(data.get('departments', []))} departments")

            return data

        except Exception as e:
            logger.exception(f"Failed to get departments: {e}")
            raise Exception(f"Failed to get departments from Identity Hub: {e}")

    def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """从Identity Hub获取用户权限

        调用Identity Hub的权限查询API，获取用户的角色和权限列表。

        Args:
            user_id: 用户ID

        Returns:
            Dict: 权限响应
                {
                    "user_id": "...",
                    "roles": [
                        {
                            "role_id": "...",
                            "role_name": "系统管理员",
                            "scope": null,
                            "is_system": 1
                        }
                    ],
                    "permissions": [
                        {
                            "permission_id": "...",
                            "resource": "task",
                            "action": "create",
                            "description": "创建任务"
                        }
                    ]
                }

        Example:
            response = client.get_user_permissions("ou-xxx")
            permissions = response["permissions"]
            for perm in permissions:
                print(f"{perm['resource']}:{perm['action']}")
        """
        url = f"{self.hub_url}/api/org/users/{user_id}/permissions"

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            data = response.json()
            logger.info(
                f"✅ Got permissions for user: {user_id} - "
                f"{len(data.get('permissions', []))} permissions"
            )

            return data

        except Exception as e:
            logger.exception(f"Failed to get user permissions: {e}")
            raise Exception(f"Failed to get user permissions from Identity Hub: {e}")


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    print("\n=== Identity Hub Client Test ===\n")

    try:
        client = IdentityHubClient()

        print(f"Hub URL: {client.hub_url}")
        print(f"Client ID: {client.client_id}")
        print(f"Redirect URI: {client.redirect_uri}")

        # 测试生成授权URL
        auth_url, state = client.get_authorization_url()
        print(f"\n✅ Authorization URL: {auth_url[:80]}...")
        print(f"✅ State: {state[:32]}...")

        print("\n💡 To test the full OAuth flow:")
        print("   1. Start Identity Hub server:")
        print("      cd /home/jian/code/identity-hub")
        print("      uvicorn backend.main:app --host 0.0.0.0 --port 8000")
        print("   2. Visit the authorization URL in a browser")
        print("   3. Complete the OAuth flow")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
