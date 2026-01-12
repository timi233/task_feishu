"""API限流模块

防止API被滥用,保护系统稳定性。

简单内存限流器实现:
- 每个API Key独立计数
- 滑动窗口算法
- 默认限制: 100次/分钟

生产环境建议:
- 使用Redis实现分布式限流
- 支持不同端点配置不同限额
"""

from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta
from typing import Dict, List
from config import settings


class RateLimiter:
    """简单内存限流器(基于滑动窗口)"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        初始化限流器

        Args:
            max_requests: 窗口期内最大请求数
            window_seconds: 窗口期长度(秒)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = {}  # {api_key: [timestamp, ...]}

    async def check(self, api_key: str) -> bool:
        """
        检查API Key是否超过限流

        Args:
            api_key: 需要检查的API密钥

        Returns:
            bool: True表示通过,False表示超过限流
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # 初始化或清理过期记录
        if api_key not in self.requests:
            self.requests[api_key] = []
        else:
            # 只保留窗口期内的请求记录
            self.requests[api_key] = [
                ts for ts in self.requests[api_key] if ts > cutoff
            ]

        # 检查是否超限
        if len(self.requests[api_key]) >= self.max_requests:
            return False

        # 记录本次请求
        self.requests[api_key].append(now)
        return True

    def reset(self, api_key: str):
        """重置指定API Key的限流计数(测试用)"""
        if api_key in self.requests:
            del self.requests[api_key]


# 全局限流器实例
# 通过统一配置管理限额
rate_limiter = RateLimiter(max_requests=settings.auth.rate_limit, window_seconds=60)


async def check_rate_limit(request: Request, api_key: str = None):
    """
    限流检查依赖(用于FastAPI endpoint)

    🔒 安全修复: 支持在dependencies中直接使用，从Header提取API Key

    使用方法:
    @app.get("/api/tasks", dependencies=[Depends(verify_readonly_api_key), Depends(check_rate_limit)])
    async def get_tasks(...):
        ...

    Args:
        request: FastAPI请求对象
        api_key: API密钥（可选，如果为None则从Header中提取）

    Raises:
        HTTPException: 429 如果超过限流
    """
    # 如果没有传入api_key，从Header中提取
    if api_key is None:
        from fastapi.security import APIKeyHeader
        from auth import api_key_header
        api_key = request.headers.get("X-API-Key")

    # 如果还是没有API Key，跳过限流检查（因为verify_readonly_api_key会处理认证）
    if not api_key:
        return

    if not await rate_limiter.check(api_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {settings.auth.rate_limit} requests per minute."
        )
