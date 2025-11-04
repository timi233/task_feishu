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
from fastapi import HTTPException, Request, status, Depends

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

    优先从本地roles表获取权限，如果用户没有分配角色，则从Identity Hub获取。

    Args:
        user_id: 用户ID

    Returns:
        权限列表 ["task:create", "task:update", ...]

    Raises:
        Exception: 如果无法获取权限
    """
    import json
    from task_db import get_db_connection

    # 1. 尝试从缓存获取
    cached_permissions = _get_cached_permissions(user_id)
    if cached_permissions is not None:
        return cached_permissions

    # 2. 优先从本地数据库获取权限
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 获取用户的所有角色及权限
            cursor.execute("""
                SELECT DISTINCT r.permissions
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = ?
            """, (user_id,))

            rows = cursor.fetchall()

            logger.info(f"[DEBUG] 查询角色权限结果: user_id={user_id}, rows={len(rows) if rows else 0}")

            if rows:
                # 合并所有角色的权限
                all_permissions = set()
                for i, row in enumerate(rows):
                    perm_str = row['permissions']
                    logger.info(f"[DEBUG]   角色[{i}] permissions字段: {perm_str[:100] if perm_str else 'None'}...")
                    if row["permissions"]:
                        try:
                            role_perms = json.loads(row["permissions"])
                            logger.info(f"[DEBUG]   角色[{i}] 解析后权限数: {len(role_perms)}, 内容: {role_perms}")
                            all_permissions.update(role_perms)
                        except json.JSONDecodeError as je:
                            logger.error(f"[DEBUG]   角色[{i}] JSON解析失败: {je}")

                permissions = list(all_permissions)
                logger.info(f"[DEBUG] 合并后总权限数: {len(permissions)}, 内容: {permissions}")

                # 缓存结果
                _set_cached_permissions(user_id, permissions)

                logger.info(f"从本地数据库获取用户权限成功: {user_id} - {len(permissions)}个权限")
                return permissions
            else:
                logger.info(f"[DEBUG] 用户 {user_id} 没有分配任何角色")

    except Exception as e:
        logger.warning(f"从本地数据库获取权限失败，尝试从Identity Hub获取: {user_id} - {e}")

    # 3. 如果本地没有角色，从Identity Hub获取
    try:
        client = IdentityHubClient()
        response = client.get_user_permissions(user_id)

        # 提取权限列表
        permissions = []
        for perm in response.get("permissions", []):
            # 组合resource:action格式
            permission_str = f"{perm['resource']}:{perm['action']}"
            permissions.append(permission_str)

        # 缓存结果
        _set_cached_permissions(user_id, permissions)

        logger.info(f"从Identity Hub获取用户权限成功: {user_id} - {len(permissions)}个权限")
        return permissions

    except Exception as e:
        logger.exception(f"获取用户权限失败: {user_id} - {e}")
        # 返回空权限列表而不是抛出异常
        return []


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
# FastAPI依赖函数
# ============================================

async def get_current_user(request: Request) -> Dict[str, Any]:
    """获取当前登录用户（FastAPI依赖）

    Args:
        request: FastAPI Request对象

    Returns:
        用户信息字典，包含user_id, user_name等

    Raises:
        HTTPException 401: 用户未登录
    """
    # 使用task_session_id避免与Identity Hub的session_id冲突
    session_id = request.cookies.get("task_session_id")

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    session_data = session_manager.get_session(session_id)

    if not session_data or not session_data.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话已过期，请重新登录"
        )

    return session_data


async def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """获取当前登录用户（可选，未登录时返回None）

    Args:
        request: FastAPI Request对象

    Returns:
        用户信息字典，如果未登录返回None
    """
    session_id = request.cookies.get("task_session_id")

    if not session_id:
        return None

    session_data = session_manager.get_session(session_id)

    if not session_data or not session_data.get("authenticated"):
        return None

    return session_data


def get_user_data_scope(user_id: str) -> str:
    """获取用户的数据范围

    Args:
        user_id: 用户ID

    Returns:
        数据范围: "all" 或 "self"
    """
    from task_db import get_db_connection

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 查询用户角色的数据范围
            cursor.execute("""
                SELECT r.data_scope
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = ?
                ORDER BY
                    CASE r.data_scope
                        WHEN 'all' THEN 1
                        WHEN 'department' THEN 2
                        WHEN 'self' THEN 3
                        ELSE 4
                    END
                LIMIT 1
            """, (user_id,))

            row = cursor.fetchone()

            if row:
                return row['data_scope']

            # 如果没有角色，默认返回self
            return "self"

    except Exception as e:
        logger.exception(f"获取用户数据范围失败: {e}")
        return "self"  # 出错时默认返回最严格的权限


def require_permission(permission: str):
    """创建一个权限检查依赖（FastAPI依赖）

    Args:
        permission: 权限字符串，格式: "resource:action"

    Returns:
        FastAPI依赖函数

    Example:
        @router.get("/api/roles")
        async def get_roles(
            current_user: Dict = Depends(require_permission("role:assign"))
        ):
            # 只有有role:assign权限的用户才能访问
            pass
    """
    async def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        """检查用户是否有指定权限"""
        user_id = current_user.get("user_id")
        user_name = current_user.get("user_name", "Unknown")

        # 检查权限
        has_perm = check_permission(user_id, permission)

        if not has_perm:
            logger.warning(
                f"权限拒绝: {user_name}({user_id}) 尝试访问 {permission}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足：需要 {permission} 权限"
            )

        # 权限验证通过，返回用户信息
        logger.info(
            f"权限验证通过: {user_name}({user_id}) - {permission}"
        )
        return current_user

    return permission_checker


# ============================================
# 旧装饰器已移除，请统一使用FastAPI依赖注入方式
# ============================================
