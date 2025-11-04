#!/usr/bin/env python3
"""
用户角色管理API路由

提供用户角色分配、撤销相关的API端点
需要系统管理员权限
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import json

from task_db import get_db_connection
from auth_permission import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


# ========== Pydantic Models ==========

class UserRoleInfo(BaseModel):
    """用户角色信息"""
    role_id: int
    role_key: str
    role_name: str
    data_scope: str
    assigned_at: str
    assigned_by: str | None


class UserResponse(BaseModel):
    """用户响应模型"""
    user_id: str
    name: str | None
    email: str | None
    roles: List[UserRoleInfo]


class AssignRoleRequest(BaseModel):
    """分配角色请求"""
    role_id: int


class AssignRoleResponse(BaseModel):
    """分配角色响应"""
    success: bool
    message: str
    user_id: str
    role_id: int


# ========== API Endpoints ==========

@router.get("", response_model=List[UserResponse])
async def get_users(
    current_user: Dict[str, Any] = Depends(require_permission("role:assign"))
):
    """
    获取所有用户及其角色

    需要权限: role:assign (系统管理员)

    返回:
        用户列表，包含每个用户的角色信息
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 获取所有在engineers表中的用户
            cursor.execute("""
                SELECT DISTINCT user_id, name, email
                FROM engineers
                ORDER BY name
            """)

            user_rows = cursor.fetchall()

            users = []
            for user_row in user_rows:
                user_id = user_row["user_id"]

                # 获取用户的角色
                cursor.execute("""
                    SELECT
                        r.id as role_id,
                        r.role_key,
                        r.role_name,
                        r.data_scope,
                        ur.assigned_at,
                        ur.assigned_by
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = ?
                    ORDER BY ur.assigned_at DESC
                """, (user_id,))

                role_rows = cursor.fetchall()

                roles = []
                for role_row in role_rows:
                    roles.append(UserRoleInfo(
                        role_id=role_row["role_id"],
                        role_key=role_row["role_key"],
                        role_name=role_row["role_name"],
                        data_scope=role_row["data_scope"],
                        assigned_at=role_row["assigned_at"],
                        assigned_by=role_row["assigned_by"]
                    ))

                users.append(UserResponse(
                    user_id=user_id,
                    name=user_row["name"],
                    email=user_row["email"],
                    roles=roles
                ))

            logger.info(f"获取用户列表成功: {len(users)}个用户")
            return users

    except Exception as e:
        logger.exception(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_detail(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_permission("role:assign"))
):
    """
    获取用户详情及其角色

    需要权限: role:assign (系统管理员)

    参数:
        user_id: 用户ID

    返回:
        用户详情，包含角色列表
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 获取用户基本信息
            cursor.execute("""
                SELECT user_id, name, email
                FROM engineers
                WHERE user_id = ?
            """, (user_id,))

            user_row = cursor.fetchone()
            if not user_row:
                raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

            # 获取用户的角色
            cursor.execute("""
                SELECT
                    r.id as role_id,
                    r.role_key,
                    r.role_name,
                    r.data_scope,
                    ur.assigned_at,
                    ur.assigned_by
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = ?
                ORDER BY ur.assigned_at DESC
            """, (user_id,))

            role_rows = cursor.fetchall()

            roles = []
            for role_row in role_rows:
                roles.append(UserRoleInfo(
                    role_id=role_row["role_id"],
                    role_key=role_row["role_key"],
                    role_name=role_row["role_name"],
                    data_scope=role_row["data_scope"],
                    assigned_at=role_row["assigned_at"],
                    assigned_by=role_row["assigned_by"]
                ))

            logger.info(f"获取用户详情成功: {user_row['name']} - {len(roles)}个角色")

            return UserResponse(
                user_id=user_row["user_id"],
                name=user_row["name"],
                email=user_row["email"],
                roles=roles
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取用户详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户详情失败: {str(e)}")


@router.post("/{user_id}/roles", response_model=AssignRoleResponse)
async def assign_role(
    user_id: str,
    request: AssignRoleRequest,
    current_user: Dict[str, Any] = Depends(require_permission("role:assign"))
):
    """
    为用户分配角色

    需要权限: role:assign (系统管理员)

    参数:
        user_id: 用户ID
        request: 包含role_id的请求体

    返回:
        分配结果
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 验证用户是否存在
            cursor.execute("SELECT user_id FROM engineers WHERE user_id = ?", (user_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

            # 验证角色是否存在
            cursor.execute("SELECT id, role_name FROM roles WHERE id = ?", (request.role_id,))
            role_row = cursor.fetchone()
            if not role_row:
                raise HTTPException(status_code=404, detail=f"角色不存在: {request.role_id}")

            # 检查是否已分配该角色
            cursor.execute("""
                SELECT id FROM user_roles
                WHERE user_id = ? AND role_id = ?
            """, (user_id, request.role_id))

            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户已拥有该角色")

            # 分配角色
            cursor.execute("""
                INSERT INTO user_roles (user_id, role_id, assigned_by)
                VALUES (?, ?, ?)
            """, (user_id, request.role_id, current_user["user_id"]))

            conn.commit()

            logger.info(f"分配角色成功: 用户={user_id}, 角色={role_row['role_name']}, 操作人={current_user.get('name', 'unknown')}")

            return AssignRoleResponse(
                success=True,
                message=f"成功为用户分配角色: {role_row['role_name']}",
                user_id=user_id,
                role_id=request.role_id
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"分配角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"分配角色失败: {str(e)}")


@router.delete("/{user_id}/roles/{role_id}")
async def revoke_role(
    user_id: str,
    role_id: int,
    current_user: Dict[str, Any] = Depends(require_permission("role:assign"))
):
    """
    撤销用户角色

    需要权限: role:assign (系统管理员)

    参数:
        user_id: 用户ID
        role_id: 角色ID

    返回:
        撤销结果
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 验证用户角色是否存在
            cursor.execute("""
                SELECT ur.id, r.role_name
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = ? AND ur.role_id = ?
            """, (user_id, role_id))

            user_role_row = cursor.fetchone()
            if not user_role_row:
                raise HTTPException(status_code=404, detail="用户未拥有该角色")

            # 撤销角色
            cursor.execute("""
                DELETE FROM user_roles
                WHERE user_id = ? AND role_id = ?
            """, (user_id, role_id))

            conn.commit()

            logger.info(f"撤销角色成功: 用户={user_id}, 角色={user_role_row['role_name']}, 操作人={current_user.get('name', 'unknown')}")

            return {
                "success": True,
                "message": f"成功撤销角色: {user_role_row['role_name']}",
                "user_id": user_id,
                "role_id": role_id
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"撤销角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"撤销角色失败: {str(e)}")
