"""权限验证装饰器和工具函数

提供基于Identity Hub的细粒度权限控制。

使用方式:
    from auth_permission import require_permission

    @router.post("/api/approvals")
    @require_permission("task:create")
    async def create_approval(request: Request):
        # 用户必须有task:create权限才能访问
        pass

日期: 2025-10-31
阶段: Phase 4.5 - 权限体系集成
"""

import time
import logging
from functools import wraps
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Request, status

from auth_identity_hub import IdentityHubClient
from session_manager import session_manager

logger = logging.getLogger(__name__)

# ============================================
# 权限缓存（内存缓存，30分钟过期）
# ============================================

_permission_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 1800  # 30分钟


def _get_cached_permissions(user_id: str) -> Optional[List[str]]:
    """从缓存获取用户权限列表

    Args:
        user_id: 用户ID

    Returns:
        权限列表，如果缓存不存在或已过期返回None
    """
    cache_key = f"permissions:{user_id}"

    if cache_key in _permission_cache:
        cache_entry = _permission_cache[cache_key]

        # 检查是否过期
        if cache_entry["expires_at"] > time.time():
            logger.debug(f"权限缓存命中: {user_id}")
            return cache_entry["permissions"]
        else:
            # 过期，删除缓存
            del _permission_cache[cache_key]
            logger.debug(f"权限缓存过期: {user_id}")

    return None


def _set_cached_permissions(user_id: str, permissions: List[str]):
    """设置用户权限缓存

    Args:
        user_id: 用户ID
        permissions: 权限列表
    """
    cache_key = f"permissions:{user_id}"

    _permission_cache[cache_key] = {
        "permissions": permissions,
        "expires_at": time.time() + CACHE_TTL
    }

    logger.debug(f"权限已缓存: {user_id} - {len(permissions)}个权限")


def clear_permission_cache(user_id: Optional[str] = None):
    """清除权限缓存

    Args:
        user_id: 用户ID，如果不提供则清除所有缓存
    """
    if user_id:
        cache_key = f"permissions:{user_id}"
        if cache_key in _permission_cache:
            del _permission_cache[cache_key]
            logger.info(f"已清除用户权限缓存: {user_id}")
    else:
        _permission_cache.clear()
        logger.info("已清除所有权限缓存")


# ============================================
# 权限检查函数
# ============================================

def get_user_permissions(user_id: str) -> List[str]:
    """获取用户的所有权限

    Args:
        user_id: 用户ID

    Returns:
        权限列表 ["task:create", "task:update", ...]

    Raises:
        Exception: 如果无法获取权限
    """
    # 1. 尝试从缓存获取
    cached_permissions = _get_cached_permissions(user_id)
    if cached_permissions is not None:
        return cached_permissions

    # 2. 从Identity Hub获取
    try:
        client = IdentityHubClient()
        response = client.get_user_permissions(user_id)

        # 提取权限列表
        permissions = []
        for perm in response.get("permissions", []):
            # 组合resource:action格式
            permission_str = f"{perm['resource']}:{perm['action']}"
            permissions.append(permission_str)

        # 3. 缓存结果
        _set_cached_permissions(user_id, permissions)

        logger.info(f"获取用户权限成功: {user_id} - {len(permissions)}个权限")
        return permissions

    except Exception as e:
        logger.exception(f"获取用户权限失败: {user_id} - {e}")
        raise Exception(f"无法获取用户权限: {str(e)}")


def check_permission(user_id: str, permission: str) -> bool:
    """检查用户是否有指定权限

    Args:
        user_id: 用户ID
        permission: 权限字符串，格式: "resource:action" (如 "task:create")

    Returns:
        bool: True表示有权限，False表示无权限
    """
    try:
        permissions = get_user_permissions(user_id)
        has_perm = permission in permissions

        logger.debug(f"权限检查: {user_id} - {permission} = {has_perm}")
        return has_perm

    except Exception as e:
        logger.warning(f"权限检查失败，默认拒绝: {user_id} - {permission} - {e}")
        return False


# ============================================
# 装饰器
# ============================================

def require_permission(permission: str):
    """权限验证装饰器

    要求用户必须有指定权限才能访问端点。

    Args:
        permission: 权限字符串，格式: "resource:action"

    Raises:
        HTTPException 401: 用户未登录
        HTTPException 403: 用户无权限

    Example:
        @router.post("/api/approvals")
        @require_permission("task:create")
        async def create_approval(request: Request):
            # 只有有task:create权限的用户才能访问
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            # 1. 检查request参数
            if request is None:
                # 从args中查找Request对象
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                logger.error("require_permission装饰器：找不到Request对象")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error: missing request object"
                )

            # 2. 从session获取user_id
            session_id = request.cookies.get("session_id")

            if not session_id:
                logger.warning(f"权限检查失败：未登录 - {permission}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="请先登录"
                )

            session_data = session_manager.get_session(session_id)

            if not session_data or not session_data.get("authenticated"):
                logger.warning(f"权限检查失败：会话无效 - {permission}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="会话已过期，请重新登录"
                )

            user_id = session_data.get("user_id")
            user_name = session_data.get("user_name", "Unknown")

            # 3. 检查权限
            has_perm = check_permission(user_id, permission)

            if not has_perm:
                logger.warning(
                    f"权限拒绝: {user_name}({user_id}) 尝试访问 {permission}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足：需要 {permission} 权限"
                )

            # 4. 权限验证通过，执行函数
            logger.info(
                f"权限验证通过: {user_name}({user_id}) - {permission}"
            )

            return await func(*args, request=request, **kwargs)

        return wrapper
    return decorator


def require_any_permission(*permissions: str):
    """要求用户有任一权限

    Args:
        *permissions: 权限列表

    Example:
        @router.get("/api/approvals")
        @require_any_permission("task:read", "task:admin")
        async def list_approvals(request: Request):
            # 用户有task:read或task:admin任一权限即可访问
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            # 查找Request对象
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error"
                )

            # 获取用户ID
            session_id = request.cookies.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="请先登录"
                )

            session_data = session_manager.get_session(session_id)
            if not session_data or not session_data.get("authenticated"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="会话已过期"
                )

            user_id = session_data.get("user_id")

            # 检查是否有任一权限
            for perm in permissions:
                if check_permission(user_id, perm):
                    logger.info(f"权限验证通过: {user_id} - {perm}")
                    return await func(*args, request=request, **kwargs)

            # 都没有权限
            logger.warning(f"权限拒绝: {user_id} - 需要{permissions}中任一权限")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足：需要以下权限之一：{', '.join(permissions)}"
            )

        return wrapper
    return decorator
