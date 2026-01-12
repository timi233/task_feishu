#!/usr/bin/env python3
"""
角色管理API路由

提供角色查询相关的API端点
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

router = APIRouter(prefix="/api/roles", tags=["roles"])


# ========== Pydantic Models ==========

class RoleResponse(BaseModel):
    """角色响应模型"""
    id: int
    role_key: str
    role_name: str
    description: str | None
    permissions: List[str]
    data_scope: str
    is_system: bool
    user_count: int  # 拥有该角色的用户数量


class RoleDetailResponse(RoleResponse):
    """角色详情响应模型（包含用户列表）"""
    users: List[Dict[str, Any]]  # 拥有该角色的用户列表


# ========== API Endpoints ==========

@router.get("", response_model=List[RoleResponse])
async def get_roles(
    current_user: Dict[str, Any] = Depends(require_permission("role:assign"))
):
    """
    获取所有角色列表

    需要权限: role:assign (系统管理员)

    返回:
        角色列表，包含每个角色的用户数量
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    r.id,
                    r.role_key,
                    r.role_name,
                    r.description,
                    r.permissions,
                    r.data_scope,
                    r.is_system,
                    COUNT(ur.id) as user_count
                FROM roles r
                LEFT JOIN user_roles ur ON r.id = ur.role_id
                GROUP BY r.id
                ORDER BY r.id
            """)

            rows = cursor.fetchall()

            roles = []
            for row in rows:
                # 解析permissions JSON
                permissions = json.loads(row["permissions"]) if row["permissions"] else []

                roles.append(RoleResponse(
                    id=row["id"],
                    role_key=row["role_key"],
                    role_name=row["role_name"],
                    description=row["description"],
                    permissions=permissions,
                    data_scope=row["data_scope"],
                    is_system=bool(row["is_system"]),
                    user_count=row["user_count"]
                ))

            logger.info(f"获取角色列表成功: {len(roles)}个角色")
            return roles

    except Exception as e:
        logger.exception(f"获取角色列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取角色列表失败: {str(e)}")


@router.get("/{role_id}", response_model=RoleDetailResponse)
async def get_role_detail(
    role_id: int,
    current_user: Dict[str, Any] = Depends(require_permission("role:assign"))
):
    """
    获取角色详情（包含用户列表）

    需要权限: role:assign (系统管理员)

    参数:
        role_id: 角色ID

    返回:
        角色详情，包含拥有该角色的用户列表
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 获取角色基本信息
            cursor.execute("""
                SELECT id, role_key, role_name, description, permissions, data_scope, is_system
                FROM roles
                WHERE id = ?
            """, (role_id,))

            role_row = cursor.fetchone()
            if not role_row:
                raise HTTPException(status_code=404, detail=f"角色不存在: {role_id}")

            # 解析permissions JSON
            permissions = json.loads(role_row["permissions"]) if role_row["permissions"] else []

            # 获取拥有该角色的用户列表
            cursor.execute("""
                SELECT
                    ur.user_id,
                    ur.assigned_by,
                    ur.assigned_at,
                    e.name as user_name,
                    e.email as user_email
                FROM user_roles ur
                LEFT JOIN engineers e ON ur.user_id = e.user_id
                WHERE ur.role_id = ?
                ORDER BY ur.assigned_at DESC
            """, (role_id,))

            user_rows = cursor.fetchall()

            users = []
            for user_row in user_rows:
                users.append({
                    "user_id": user_row["user_id"],
                    "user_name": user_row["user_name"],
                    "user_email": user_row["user_email"],
                    "assigned_by": user_row["assigned_by"],
                    "assigned_at": user_row["assigned_at"]
                })

            logger.info(f"获取角色详情成功: {role_row['role_name']} - {len(users)}个用户")

            return RoleDetailResponse(
                id=role_row["id"],
                role_key=role_row["role_key"],
                role_name=role_row["role_name"],
                description=role_row["description"],
                permissions=permissions,
                data_scope=role_row["data_scope"],
                is_system=bool(role_row["is_system"]),
                user_count=len(users),
                users=users
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取角色详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取角色详情失败: {str(e)}")
