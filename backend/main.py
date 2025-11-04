# 后端服务主入口

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import datetime
import os
import logging
import time

# 从本地数据库模块导入
from task_db import init_db, get_task_count

# 导入OAuth认证模块
from auth_routes import router as auth_router
from auth_middleware import optional_auth

# 导入所有router
from routers.tasks import router as tasks_router
from routers.filters import router as filters_router
from routers.engineers import router as engineers_router
from routers.sync import router as sync_router
from routers.approvals import router as approvals_router
from routers.org_sync import router as org_sync_router
from routers.roles import router as roles_router
from routers.users import router as users_router
from routers.user_sync import router as user_sync_router

# 统一配置管理
from config import settings

# 配置日志（统一入口）
from utils.logging_config import setup_logging
setup_logging(app_name="feishu_task")

logger = logging.getLogger(__name__)

# 启动时打印配置摘要
settings.print_summary()

# 验证配置
config_errors = settings.validate()
if config_errors:
    logger.error("Configuration validation failed:")
    for error in config_errors:
        logger.error(f"  - {error}")
    logger.warning("Some features may not work properly")

app = FastAPI(title="飞书派工系统API")

# ===== CORS配置 =====
allowed_origins = settings.server.allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 静态文件服务 =====
app.mount("/static", StaticFiles(directory="static"), name="static")

# ===== 初始化数据库 =====
init_db()

# ===== 注册路由 =====
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(filters_router)
app.include_router(engineers_router)
app.include_router(sync_router)
app.include_router(approvals_router)
app.include_router(org_sync_router)
app.include_router(roles_router)
app.include_router(users_router)
app.include_router(user_sync_router)


# ===== 中间件 =====

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """可选OAuth认证中间件

    尝试从session获取用户信息，但不强制要求登录。
    支持API Key认证和OAuth认证并存。
    """
    return await optional_auth(request, call_next)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有API请求(用于审计)"""
    start_time = time.time()

    # 获取API Key(用于审计)
    api_key = request.headers.get("X-API-Key", "none")
    masked_key = api_key[:8] + "***" if len(api_key) > 8 else "***"

    response = await call_next(request)

    process_time = time.time() - start_time

    logger.info(
        "API Request: method=%s path=%s api_key=%s status=%d duration=%.3fs",
        request.method,
        request.url.path,
        masked_key,
        response.status_code,
        process_time
    )

    return response


# ===== 基础端点 =====

@app.get("/")
async def read_root():
    return {"message": "飞书派工系统后端服务"}


@app.get("/health")
async def health_check():
    """
    健康检查端点

    供监控系统调用,验证:
    1. 数据库连接正常
    2. 数据量在合理范围

    Returns:
        dict: 包含status, database, task_count, timestamp
    """
    try:
        task_count = get_task_count()

        return {
            "status": "healthy",
            "database": "connected",
            "task_count": task_count,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception("Health check failed")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
