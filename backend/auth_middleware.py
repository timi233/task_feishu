"""认证中间件

提供可选的OAuth认证中间件，用于保护需要登录的API端点。
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Callable, Optional
import logging

from session_manager import session_manager

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Optional[dict]:
    """从session获取当前登录用户

    Args:
        request: FastAPI请求对象

    Returns:
        Optional[dict]: 用户信息，如果未登录返回None
    """
    session_id = request.cookies.get("session_id")

    if not session_id:
        return None

    session_data = session_manager.get_session(session_id)

    if not session_data or not session_data.get("authenticated"):
        return None

    return {
        "user_id": session_data.get("user_id"),
        "name": session_data.get("user_name"),
        "email": session_data.get("user_email"),
        "mobile": session_data.get("user_mobile")
    }


async def require_auth(request: Request, call_next: Callable):
    """认证中间件（强制要求登录）

    如果用户未登录，返回401错误。

    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器

    Returns:
        响应对象
    """
    # 白名单路径（不需要认证）
    whitelist_paths = [
        "/auth/login",
        "/auth/callback",
        "/auth/status",
        "/docs",
        "/openapi.json",
        "/static",
        "/health"
    ]

    # 检查是否在白名单中
    for path in whitelist_paths:
        if request.url.path.startswith(path):
            return await call_next(request)

    # 获取当前用户
    user = await get_current_user(request)

    if not user:
        # 如果是API请求，返回401
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Not authenticated. Please login via /auth/login",
                    "login_url": "/auth/login"
                }
            )

        # 如果是页面请求，重定向到登录
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "Not authenticated",
                "login_url": f"/auth/login?return_url={request.url.path}"
            }
        )

    # 将用户信息添加到请求状态
    request.state.user = user

    return await call_next(request)


async def optional_auth(request: Request, call_next: Callable):
    """可选认证中间件

    尝试获取当前用户，但不强制要求登录。
    如果用户已登录，将用户信息添加到request.state.user。

    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器

    Returns:
        响应对象
    """
    user = await get_current_user(request)

    if user:
        request.state.user = user
        logger.debug(f"Authenticated user: {user['name']}")
    else:
        request.state.user = None

    return await call_next(request)


def get_user_from_request(request: Request) -> Optional[dict]:
    """从请求中获取用户信息

    便捷函数，用于在路由处理器中获取当前用户。

    Args:
        request: FastAPI请求对象

    Returns:
        Optional[dict]: 用户信息，如果未登录返回None

    Example:
        @app.get("/api/my-tasks")
        async def get_my_tasks(request: Request):
            user = get_user_from_request(request)
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")

            # 获取用户的任务
            tasks = get_tasks_for_user(user["user_id"])
            return tasks
    """
    return getattr(request.state, "user", None)


def require_user(request: Request) -> dict:
    """要求用户已登录（Depends依赖项）

    Args:
        request: FastAPI请求对象

    Returns:
        dict: 用户信息

    Raises:
        HTTPException: 如果用户未登录

    Example:
        from fastapi import Depends

        @app.get("/api/profile")
        async def get_profile(user: dict = Depends(require_user)):
            return {
                "name": user["name"],
                "email": user["email"]
            }
    """
    user = get_user_from_request(request)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    return user
