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

import os
from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta
from typing import Dict, List


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
# 可以通过环境变量配置限额
MAX_REQUESTS_PER_MINUTE = int(os.getenv("API_RATE_LIMIT", "100"))
rate_limiter = RateLimiter(max_requests=MAX_REQUESTS_PER_MINUTE, window_seconds=60)


async def check_rate_limit(request: Request, api_key: str):
    """
    限流检查依赖(用于FastAPI endpoint)

    使用方法:
    @app.get("/api/tasks", dependencies=[Depends(verify_api_key), Depends(check_rate_limit)])
    async def get_tasks(api_key: str = Depends(verify_api_key)):
        ...

    Args:
        request: FastAPI请求对象
        api_key: 已验证的API密钥

    Raises:
        HTTPException: 429 如果超过限流
    """
    if not await rate_limiter.check(api_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {MAX_REQUESTS_PER_MINUTE} requests per minute."
        )
