"""API认证模块

提供API Key认证中间件,支持:
1. 管理员API Key(读写权限)
2. 只读API Key(供其他系统使用)
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

# 加载.env文件
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# 从环境变量读取API密钥
# API_KEYS: 管理员密钥,拥有读写权限
# READONLY_API_KEYS: 只读密钥,供其他系统查询使用
API_KEYS = os.getenv("API_KEYS", "default-dev-key").split(",")
API_KEYS = [key.strip() for key in API_KEYS if key.strip()]

READONLY_API_KEYS = os.getenv("READONLY_API_KEYS", "").split(",")
READONLY_API_KEYS = [key.strip() for key in READONLY_API_KEYS if key.strip()]

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    验证管理员API Key(读写权限)

    使用方法:
    @app.post("/api/tasks", dependencies=[Depends(verify_api_key)])
    async def create_task(...):
        ...

    Args:
        api_key: 从HTTP Header X-API-Key中提取的密钥

    Raises:
        HTTPException: 403 如果API Key缺失或无效

    Returns:
        str: 验证通过的API Key
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API Key. Please provide X-API-Key header."
        )

    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )

    return api_key


async def verify_readonly_api_key(api_key: str = Security(api_key_header)):
    """
    验证只读API Key(查询权限)

    接受两种密钥:
    1. 管理员API Key(API_KEYS)
    2. 只读API Key(READONLY_API_KEYS)

    使用方法:
    @app.get("/api/tasks", dependencies=[Depends(verify_readonly_api_key)])
    async def get_tasks(...):
        ...

    Args:
        api_key: 从HTTP Header X-API-Key中提取的密钥

    Raises:
        HTTPException: 403 如果API Key缺失或无效

    Returns:
        str: 验证通过的API Key
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API Key. Please provide X-API-Key header."
        )

    # 检查是否在管理员密钥或只读密钥列表中
    if api_key not in API_KEYS and api_key not in READONLY_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )

    return api_key
