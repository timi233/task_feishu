"""
统一日志配置模块

特性:
- 环境变量控制日志级别(LOG_LEVEL)
- 支持控制台和文件输出
- 自动日志轮转(每天一个文件,保留30天)
- 可选JSON格式(LOG_FORMAT=json)
- 单一配置入口,避免重复配置

使用方法:
    from utils.logging_config import setup_logging

    # 在应用启动时调用一次
    setup_logging()

    # 然后在各模块中正常使用
    logger = logging.getLogger(__name__)
    logger.info("message")
"""

import os
import sys
import logging
import logging.handlers
import json
from datetime import datetime
from typing import Optional


class JsonFormatter(logging.Formatter):
    """JSON格式日志输出器(用于ELK/Splunk等日志系统)"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    app_name: str = "feishu_task",
    log_dir: Optional[str] = None
) -> None:
    """
    配置应用日志系统

    环境变量:
        LOG_LEVEL: 日志级别(DEBUG/INFO/WARNING/ERROR, 默认INFO)
        LOG_FORMAT: 日志格式(text/json, 默认text)
        LOG_FILE: 是否输出到文件(true/false, 默认false)
        LOG_DIR: 日志文件目录(默认./logs)

    Args:
        app_name: 应用名称,用于日志文件命名
        log_dir: 日志目录,覆盖环境变量LOG_DIR
    """

    # 1. 读取配置
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "text").lower()
    enable_file_log = os.getenv("LOG_FILE", "false").lower() == "true"
    log_dir = log_dir or os.getenv("LOG_DIR", "./logs")

    # 转换日志级别
    log_level = getattr(logging, log_level_str, logging.INFO)

    # 2. 获取根logger(清空已有配置)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # 3. 配置格式化器
    if log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # 4. 配置控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 5. 配置文件输出(可选)
    if enable_file_log:
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f"{app_name}.log")

        # 使用TimedRotatingFileHandler实现日志轮转
        # when='midnight': 每天午夜轮转
        # interval=1: 每1天
        # backupCount=30: 保留30天
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        root_logger.info(f"File logging enabled: {log_file}")

    # 6. 设置第三方库日志级别(避免噪音)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    root_logger.info(
        f"Logging configured: level={log_level_str}, "
        f"format={log_format}, file={enable_file_log}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取logger实例(便捷方法)

    Args:
        name: logger名称,通常使用 __name__

    Returns:
        logging.Logger实例

    使用:
        logger = get_logger(__name__)
        logger.info("message")
    """
    return logging.getLogger(name)


# 测试代码
if __name__ == "__main__":
    # 测试text格式
    print("=== Test 1: Text Format ===")
    setup_logging()
    logger = get_logger(__name__)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # 测试JSON格式
    print("\n=== Test 2: JSON Format ===")
    os.environ["LOG_FORMAT"] = "json"
    logging.getLogger().handlers.clear()
    setup_logging()
    logger = get_logger(__name__)
    logger.info("This is JSON formatted log")

    # 测试文件输出
    print("\n=== Test 3: File Output ===")
    os.environ["LOG_FILE"] = "true"
    os.environ["LOG_FORMAT"] = "text"
    logging.getLogger().handlers.clear()
    setup_logging()
    logger = get_logger(__name__)
    logger.info("This log will be written to file")
    print(f"Check log file: {os.path.abspath('./logs/feishu_task.log')}")
