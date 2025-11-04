#!/usr/bin/env python3
"""
用户同步API路由

提供用户同步相关的API端点
需要系统管理员权限
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth_permission import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users/sync", tags=["user-sync"])


class SyncResponse(BaseModel):
    """同步响应模型"""
    success: bool
    message: str
    total_users: int
    created: int
    updated: int
    errors: list


@router.post("/identity-hub", response_model=SyncResponse)
async def sync_from_identity_hub(
    current_user: Dict[str, Any] = Depends(require_permission("role:assign"))
):
    """
    从Identity Hub同步用户

    需要权限: role:assign (系统管理员)

    返回:
        同步结果统计
    """
    try:
        from sync_engineers_from_hub import sync_engineers_from_identity_hub

        result = sync_engineers_from_identity_hub()

        return SyncResponse(
            success=result["success"],
            message=f"同步完成: 新增{result['created']}，更新{result['updated']}",
            total_users=result["total_users"],
            created=result["created"],
            updated=result["updated"],
            errors=result["errors"]
        )

    except Exception as e:
        logger.exception(f"从Identity Hub同步用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/feishu", response_model=SyncResponse)
async def sync_from_feishu(
    current_user: Dict[str, Any] = Depends(require_permission("role:assign"))
):
    """
    从飞书组织架构同步所有用户

    需要权限: role:assign (系统管理员)
    需要配置: 飞书应用需要开通通讯录权限

    功能: 遍历整个组织架构，获取所有部门的所有用户

    返回:
        同步结果统计
    """
    try:
        from sync_users_from_feishu_full import sync_users_from_feishu_org

        result = sync_users_from_feishu_org()

        if not result["success"] and result["errors"]:
            # 如果同步失败，返回错误信息
            raise HTTPException(
                status_code=400,
                detail=f"同步失败: {', '.join(result['errors'])}"
            )

        return SyncResponse(
            success=result["success"],
            message=f"同步完成: 新增{result['created']}，更新{result['updated']}",
            total_users=result["total_users"],
            created=result["created"],
            updated=result["updated"],
            errors=result["errors"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"从飞书组织架构同步用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/tasks", response_model=SyncResponse)
async def sync_from_tasks(
    current_user: Dict[str, Any] = Depends(require_permission("role:assign"))
):
    """
    从任务数据同步工程师

    需要权限: role:assign (系统管理员)
    用途: 当无法从Identity Hub或飞书通讯录同步时，从任务的派工人员字段提取工程师信息

    返回:
        同步结果统计
    """
    try:
        from sync_engineers_from_tasks import sync_engineers_from_tasks

        result = sync_engineers_from_tasks()

        return SyncResponse(
            success=result["success"],
            message=f"同步完成: 新增{result['created']}，跳过{result['skipped']}",
            total_users=result["total_engineers"],
            created=result["created"],
            updated=0,
            errors=result["errors"]
        )

    except Exception as e:
        logger.exception(f"从任务数据同步工程师失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/cleanup")
async def cleanup_duplicate_users(
    current_user: Dict[str, Any] = Depends(require_permission("role:assign"))
):
    """
    清理重复用户数据

    需要权限: role:assign (系统管理员)
    功能: 删除临时用户（task_开头）和Identity Hub用户，只保留飞书同步的用户

    返回:
        清理结果统计
    """
    try:
        from task_db import get_db_connection

        stats = {
            "task_users_deleted": 0,
            "identity_hub_users_deleted": 0,
            "feishu_users_kept": 0,
            "admin_role_transferred": False
        }

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. 查找系统管理员角色
            cursor.execute("SELECT id FROM roles WHERE role_key = 'system_admin'")
            admin_role = cursor.fetchone()
            admin_role_id = admin_role['id'] if admin_role else None

            # 2. 查找飞书的张健账户并分配管理员角色
            if admin_role_id:
                cursor.execute("""
                    SELECT user_id, name
                    FROM engineers
                    WHERE name = '张健'
                    AND user_id NOT LIKE 'task_%'
                    AND user_id NOT LIKE 'ou_%'
                    AND user_id NOT LIKE '%-%-%-%-%'
                    LIMIT 1
                """)
                feishu_zhangjian = cursor.fetchone()

                if feishu_zhangjian:
                    feishu_user_id = feishu_zhangjian['user_id']
                    logger.info(f"找到飞书张健账户: {feishu_user_id}")

                    # 检查是否已有管理员角色
                    cursor.execute("""
                        SELECT id FROM user_roles
                        WHERE user_id = ? AND role_id = ?
                    """, (feishu_user_id, admin_role_id))

                    if not cursor.fetchone():
                        # 分配管理员角色
                        cursor.execute("""
                            INSERT INTO user_roles (user_id, role_id, assigned_by)
                            VALUES (?, ?, ?)
                        """, (feishu_user_id, admin_role_id, current_user["user_id"]))
                        stats["admin_role_transferred"] = True
                        logger.info(f"✅ 已将系统管理员角色分配给飞书账户: {feishu_user_id}")

            # 3. 删除task_开头的临时用户
            cursor.execute("DELETE FROM user_roles WHERE user_id LIKE 'task_%'")
            cursor.execute("DELETE FROM engineers WHERE user_id LIKE 'task_%'")
            stats["task_users_deleted"] = cursor.rowcount
            logger.info(f"删除 {stats['task_users_deleted']} 个临时用户")

            # 4. 删除Identity Hub用户
            cursor.execute("DELETE FROM user_roles WHERE user_id LIKE 'ou_%'")
            cursor.execute("DELETE FROM engineers WHERE user_id LIKE 'ou_%'")
            ou_deleted = cursor.rowcount

            cursor.execute("DELETE FROM user_roles WHERE user_id LIKE '%-%-%-%-%'")
            cursor.execute("DELETE FROM engineers WHERE user_id LIKE '%-%-%-%-%'")
            uuid_deleted = cursor.rowcount

            stats["identity_hub_users_deleted"] = ou_deleted + uuid_deleted
            logger.info(f"删除 {stats['identity_hub_users_deleted']} 个Identity Hub用户")

            # 5. 统计保留的飞书用户
            cursor.execute("SELECT COUNT(*) as count FROM engineers")
            stats["feishu_users_kept"] = cursor.fetchone()['count']

            conn.commit()

        logger.info(f"✅ 清理完成: 保留{stats['feishu_users_kept']}个飞书用户")

        return {
            "success": True,
            "message": f"清理完成: 删除{stats['task_users_deleted'] + stats['identity_hub_users_deleted']}个重复用户，保留{stats['feishu_users_kept']}个飞书用户",
            "stats": stats
        }

    except Exception as e:
        logger.exception(f"清理用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")
