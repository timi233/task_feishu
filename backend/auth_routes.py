"""OAuth认证路由

提供OAuth 2.0认证端点：
- GET /auth/login - 跳转到Identity Hub登录
- GET /auth/callback - OAuth回调处理
- POST /auth/logout - 登出
- GET /auth/user - 获取当前登录用户
"""

from fastapi import APIRouter, HTTPException, Response, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional
import logging
import os

from auth_identity_hub import IdentityHubClient
from session_manager import session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# 初始化Identity Hub客户端
try:
    identity_hub_client = IdentityHubClient()
    logger.info("✅ Identity Hub client initialized")
except Exception as e:
    logger.exception(f"❌ Failed to initialize Identity Hub client: {e}")
    identity_hub_client = None


@router.get("/login")
async def login(
    response: Response,
    return_url: str = "/"
):
    """登录端点

    生成OAuth授权URL并跳转到Identity Hub登录页面。

    Args:
        return_url: 登录成功后的返回URL（默认: /）

    Returns:
        重定向到Identity Hub授权页面
    """
    if not identity_hub_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity Hub client not configured"
        )

    try:
        # 生成授权URL
        auth_url, state = identity_hub_client.get_authorization_url()

        # 创建session保存state和return_url
        session_id = session_manager.create_session({
            "oauth_state": state,
            "return_url": return_url
        })

        # 设置session cookie（使用task_session_id避免与Identity Hub的session_id冲突）
        response = RedirectResponse(url=auth_url)
        response.set_cookie(
            key="task_session_id",
            value=session_id,
            httponly=True,
            max_age=7200,  # 2小时
            samesite="lax",  # 允许top-level navigation携带cookie
            path="/"  # 确保整个后端都能访问
        )

        logger.info(f"Redirecting to Identity Hub login (state={state[:16]}...)")
        return response

    except Exception as e:
        logger.exception(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate login: {str(e)}"
        )


@router.get("/callback")
async def callback(
    request: Request,
    response: Response,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """OAuth回调端点

    处理Identity Hub的OAuth回调，交换授权码为token。

    Args:
        code: 授权码
        state: CSRF防护token
        error: 错误信息（如果授权失败）

    Returns:
        重定向到return_url或前端首页
    """
    if not identity_hub_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity Hub client not configured"
        )

    # 检查是否有错误
    if error:
        logger.error(f"OAuth callback error: {error}")
        frontend_url = os.getenv("FRONTEND_URL", "http://10.242.94.9:3000")
        return RedirectResponse(
            url=f"{frontend_url}/?error={error}",
            status_code=status.HTTP_302_FOUND
        )

    # 验证参数
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter"
        )

    # 获取session（使用task_session_id避免与Identity Hub的session_id冲突）
    session_id = request.cookies.get("task_session_id")
    logger.info(f"Callback received: session_id={session_id[:16] if session_id else 'None'}..., code={code[:16] if code else 'None'}..., state={state[:16] if state else 'None'}...")

    if not session_id:
        logger.error(f"Missing task_session_id cookie. All cookies: {request.cookies}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing session cookie"
        )

    session_data = session_manager.get_session(session_id)
    if not session_data:
        logger.error(f"Invalid or expired session: session_id={session_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired session"
        )

    # 验证state
    if state != session_data.get("oauth_state"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter (CSRF protection)"
        )

    try:
        # 用授权码换取token
        token_data = identity_hub_client.exchange_code_for_token(code, state)

        # 获取用户信息
        user_info = identity_hub_client.get_user_info(token_data["access_token"])

        # 获取用户权限
        user_permissions = []
        user_roles = []
        try:
            permissions_response = identity_hub_client.get_user_permissions(user_info["sub"])
            user_permissions = [
                f"{perm['resource']}:{perm['action']}"
                for perm in permissions_response.get("permissions", [])
            ]
            user_roles = permissions_response.get("roles", [])
            logger.info(f"获取用户权限成功: {len(user_permissions)}个权限, {len(user_roles)}个角色")
        except Exception as perm_error:
            logger.warning(f"获取用户权限失败，使用默认权限: {perm_error}")
            user_permissions = ["task:read"]  # 默认只读权限

        # 更新session
        session_manager.update_session(session_id, {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "user_id": user_info["sub"],
            "user_name": user_info["name"],
            "user_email": user_info.get("email"),
            "user_mobile": user_info.get("mobile"),
            "user_permissions": user_permissions,
            "user_roles": user_roles,
            "authenticated": True
        })

        logger.info(f"✅ User logged in: {user_info['name']} ({user_info['sub']})")

        # === 新增：同步当前登录用户信息到本地engineers表 ===
        try:
            user_id = user_info["sub"]

            # 从Identity Hub获取用户详情（包含部门信息）
            user_detail = identity_hub_client.get_user_detail(user_id)

            # 提取主部门名称
            primary_dept = user_detail.get("primary_department", {})
            department_name = primary_dept.get("name") if primary_dept else None

            # 更新或插入到engineers表
            from task_db import get_db_connection

            with get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO engineers
                    (user_id, name, email, mobile, department_name, status, synced_at)
                    VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET
                        name = excluded.name,
                        email = excluded.email,
                        mobile = excluded.mobile,
                        department_name = excluded.department_name,
                        synced_at = CURRENT_TIMESTAMP
                """, (
                    user_id,
                    user_info["name"],
                    user_info.get("email"),
                    user_info.get("mobile"),
                    department_name
                ))

                conn.commit()

            logger.info(f"✅ 已同步用户信息到本地: {user_info['name']} - {department_name}")

        except Exception as sync_error:
            # 同步失败不应阻止登录流程
            logger.warning(f"同步用户信息失败（不影响登录）: {sync_error}")

        # 获取返回URL
        return_url = session_data.get("return_url", "/")

        # 如果是相对路径，转换为前端完整URL
        if return_url.startswith("/"):
            frontend_url = os.getenv("FRONTEND_URL", "http://10.242.94.9:3000")
            return_url = f"{frontend_url}{return_url}"

        # 重定向回原页面
        return RedirectResponse(
            url=return_url,
            status_code=status.HTTP_302_FOUND
        )

    except Exception as e:
        logger.exception(f"OAuth callback failed: {e}")
        frontend_url = os.getenv("FRONTEND_URL", "http://10.242.94.9:3000")
        return RedirectResponse(
            url=f"{frontend_url}/?error=oauth_failed",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """登出端点

    撤销token并清除session。

    Returns:
        成功消息
    """
    session_id = request.cookies.get("task_session_id")

    if session_id:
        session_data = session_manager.get_session(session_id)

        if session_data and identity_hub_client:
            # 撤销token
            access_token = session_data.get("access_token")
            refresh_token = session_data.get("refresh_token")

            if access_token:
                try:
                    identity_hub_client.revoke_token(access_token, "access_token")
                except Exception as e:
                    logger.warning(f"Failed to revoke access_token: {e}")

            if refresh_token:
                try:
                    identity_hub_client.revoke_token(refresh_token, "refresh_token")
                except Exception as e:
                    logger.warning(f"Failed to revoke refresh_token: {e}")

        # 删除session
        session_manager.delete_session(session_id)

        logger.info("✅ User logged out")

    # 清除cookie
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie(key="task_session_id")

    return response


@router.get("/user")
async def get_current_user(request: Request):
    """获取当前登录用户

    返回当前登录用户的信息。

    Returns:
        用户信息或401错误
    """
    session_id = request.cookies.get("task_session_id")

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    session_data = session_manager.get_session(session_id)

    if not session_data or not session_data.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    return {
        "user_id": session_data.get("user_id"),
        "name": session_data.get("user_name"),
        "email": session_data.get("user_email"),
        "mobile": session_data.get("user_mobile"),
        "permissions": session_data.get("user_permissions", []),
        "roles": session_data.get("user_roles", []),
        "authenticated": True
    }


@router.get("/status")
async def auth_status(request: Request):
    """检查认证状态

    Returns:
        认证状态信息
    """
    session_id = request.cookies.get("task_session_id")

    if not session_id:
        return {
            "authenticated": False,
            "identity_hub_available": identity_hub_client is not None
        }

    session_data = session_manager.get_session(session_id)

    if not session_data or not session_data.get("authenticated"):
        return {
            "authenticated": False,
            "identity_hub_available": identity_hub_client is not None
        }

    return {
        "authenticated": True,
        "user_name": session_data.get("user_name"),
        "identity_hub_available": True
    }
