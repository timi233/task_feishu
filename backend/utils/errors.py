"""统一错误处理模块

使用FastAPI的exception_handler机制，而非装饰器:
- 更符合Linus的"扁平化"原则
- 不增加函数嵌套层次
- 集中管理异常到HTTP响应的映射
"""

import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ===== 全局异常处理器 =====

async def approval_api_error_handler(request: Request, exc: Exception):
    """
    处理ApprovalAPIError异常

    所有审批相关端点的API错误统一返回502 Bad Gateway
    """
    logger.exception(
        "Approval API error at %s %s: %s",
        request.method,
        request.url.path,
        exc
    )

    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": str(exc),
            "error_type": "approval_api_error"
        }
    )


async def validation_error_handler(request: Request, exc: ValueError):
    """
    处理ValueError异常（业务逻辑验证错误）

    返回400 Bad Request
    """
    logger.warning(
        "Validation error at %s %s: %s",
        request.method,
        request.url.path,
        exc
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": str(exc),
            "error_type": "validation_error"
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    处理未捕获的通用异常

    返回500 Internal Server Error

    注意: 这是最后的保底handler，具体端点应该有自己的try-except
    """
    logger.exception(
        "Unexpected error at %s %s: %s",
        request.method,
        request.url.path,
        exc
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_type": "unexpected_error"
        }
    )


def register_exception_handlers(app):
    """
    注册所有exception handlers到FastAPI app

    使用方法（在main.py中）:
    ```python
    from utils.errors import register_exception_handlers
    from feishu_approval import ApprovalAPIError

    app = FastAPI()
    register_exception_handlers(app)
    ```

    注意: ApprovalAPIError定义在feishu_approval.py中，需要在调用此函数前导入
    """
    from feishu_approval import ApprovalAPIError
    app.add_exception_handler(ApprovalAPIError, approval_api_error_handler)
    app.add_exception_handler(ValueError, validation_error_handler)
    # 可选: 添加通用异常处理器（但建议端点自行处理）
    # app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered")
