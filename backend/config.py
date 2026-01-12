"""
应用配置模块

集中管理所有环境变量，提供类型安全的配置访问。

特性:
- 类型注解和验证
- 默认值处理
- 配置分组（飞书/数据库/认证/日志等）
- 环境变量文档化

使用:
    from config import settings

    # 访问配置
    app_id = settings.feishu.app_id
    db_file = settings.database.file_path
    log_level = settings.logging.level
"""

import os
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class FeishuConfig:
    """飞书API配置"""

    # 基础配置
    app_id: str
    app_secret: str

    # 旧配置（保留向后兼容）
    app_token: str
    table_id: str

    # 新的多数据源配置
    dispatch_base_id: str           # 派工单多维表格ID
    company_dispatch_table_id: str  # 公司派单表ID
    eisoo_dispatch_table_id: str    # 厂家派工表ID
    field_dispatch_table_id: str    # 外勤申请表ID

    # 审批配置
    approval_code_daily_work: str  # 公司日常工单
    approval_code_eisoo: str       # 爱数原厂派单
    approval_admin_user_id: str    # 默认审批发起人ID

    @classmethod
    def from_env(cls) -> "FeishuConfig":
        """从环境变量加载"""
        return cls(
            app_id=os.getenv("FEISHU_APP_ID") or "",
            app_secret=os.getenv("FEISHU_APP_SECRET") or "",
            # 旧配置（向后兼容）
            app_token=os.getenv("FEISHU_APP_TOKEN") or "",
            table_id=os.getenv("FEISHU_TABLE_ID") or "",
            # 新的多数据源配置
            dispatch_base_id=os.getenv("FEISHU_DISPATCH_BASE_ID") or "U7eAb65luaX1zKscoOzcgcednlh",
            company_dispatch_table_id=os.getenv("FEISHU_WORK_ORDER_TABLE_ID") or "tbl6CuEM97ybgRri",
            eisoo_dispatch_table_id=os.getenv("FEISHU_EISOO_DISPATCH_TABLE_ID") or "tbl8DESrT22JYvfS",
            field_dispatch_table_id=os.getenv("FEISHU_FIELD_DISPATCH_TABLE_ID") or "tblC8B2jvybfbdVM",
            approval_code_daily_work=os.getenv(
                "FEISHU_APPROVAL_CODE",
                "4202AD96-9EC1-4284-9C48-B923CDC4F30B"
            ),
            approval_code_eisoo=os.getenv(
                "FEISHU_APPROVAL_CODE_EISOO",
                "1258F9D1-FFEB-4C1F-A0ED-200A7807261A"
            ),
            approval_admin_user_id=os.getenv(
                "FEISHU_APPROVAL_ADMIN_USER_ID",
                "f7cb567e"
            ),
        )


@dataclass
class DatabaseConfig:
    """数据库配置"""

    # SQLite配置
    type: str          # sqlite | mysql
    file_path: str     # SQLite文件路径

    # MySQL配置（可选）
    mysql_host: Optional[str] = None
    mysql_port: int = 3306
    mysql_user: Optional[str] = None
    mysql_password: Optional[str] = None
    mysql_database: Optional[str] = None

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """从环境变量加载"""
        return cls(
            type=os.getenv("DB_TYPE", "sqlite"),
            file_path=os.getenv("DB_FILE", "./data/db/tasks.db"),
            mysql_host=os.getenv("MYSQL_HOST"),
            mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
            mysql_user=os.getenv("MYSQL_USER"),
            mysql_password=os.getenv("MYSQL_PASSWORD"),
            mysql_database=os.getenv("MYSQL_DATABASE"),
        )


@dataclass
class AuthConfig:
    """认证和鉴权配置"""

    # API Key认证
    api_keys: List[str]           # 管理员密钥（读写权限）
    readonly_api_keys: List[str]  # 只读密钥

    # OAuth认证（Identity Hub）
    identity_hub_url: Optional[str] = None
    identity_hub_client_id: Optional[str] = None
    identity_hub_client_secret: Optional[str] = None
    identity_hub_redirect_uri: Optional[str] = None

    # 速率限制
    rate_limit: int = 100  # 每分钟请求数

    @classmethod
    def from_env(cls) -> "AuthConfig":
        """从环境变量加载

        🔒 安全修复 (P2-9): 移除默认开发密钥
        - 生产环境必须显式配置API_KEYS
        - 如果未设置，validate()会报错但不阻止启动
        - 只读密钥可以为空（使用管理员密钥）
        """
        # API Keys（逗号分隔）
        # 🔒 不再提供默认值，强制配置
        api_keys_str = os.getenv("API_KEYS", "")
        readonly_keys_str = os.getenv("READONLY_API_KEYS", "")

        return cls(
            api_keys=[k.strip() for k in api_keys_str.split(",") if k.strip()],
            readonly_api_keys=[k.strip() for k in readonly_keys_str.split(",") if k.strip()],
            identity_hub_url=os.getenv("IDENTITY_HUB_URL"),
            identity_hub_client_id=os.getenv("IDENTITY_HUB_CLIENT_ID"),
            identity_hub_client_secret=os.getenv("IDENTITY_HUB_CLIENT_SECRET"),
            identity_hub_redirect_uri=os.getenv("IDENTITY_HUB_REDIRECT_URI"),
            rate_limit=int(os.getenv("API_RATE_LIMIT", "100")),
        )


@dataclass
class LoggingConfig:
    """日志配置"""

    level: str = "INFO"          # DEBUG/INFO/WARNING/ERROR
    format: str = "text"         # text/json
    file_enabled: bool = False   # 是否输出到文件
    dir: str = "./logs"          # 日志目录

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """从环境变量加载"""
        return cls(
            level=os.getenv("LOG_LEVEL", "INFO").upper(),
            format=os.getenv("LOG_FORMAT", "text").lower(),
            file_enabled=os.getenv("LOG_FILE", "false").lower() == "true",
            dir=os.getenv("LOG_DIR", "./logs"),
        )


@dataclass
class ServerConfig:
    """服务器配置"""

    # CORS配置
    allowed_origins: List[str]

    # 前端URL（用于重定向）
    frontend_url: str

    # 同步间隔（分钟）
    sync_interval_minutes: int = 60

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """从环境变量加载"""
        origins_str = os.getenv("ALLOWED_ORIGINS") or "http://localhost:3000,http://localhost:8080"

        return cls(
            allowed_origins=[o.strip() for o in origins_str.split(",") if o.strip()],
            frontend_url=os.getenv("FRONTEND_URL", "http://localhost:3000"),
            sync_interval_minutes=int(os.getenv("SYNC_INTERVAL_MINUTES", "60")),
        )


class Settings:
    """
    应用配置单例

    统一访问入口：
        from config import settings
        print(settings.feishu.app_id)
        print(settings.database.file_path)
        print(settings.auth.api_keys)
    """

    def __init__(self):
        self.feishu = FeishuConfig.from_env()
        self.database = DatabaseConfig.from_env()
        self.auth = AuthConfig.from_env()
        self.logging = LoggingConfig.from_env()
        self.server = ServerConfig.from_env()

    def validate(self) -> List[str]:
        """
        验证配置完整性

        Returns:
            错误列表（空列表表示验证通过）
        """
        errors = []

        # 飞书配置验证
        if not self.feishu.app_id:
            errors.append("FEISHU_APP_ID is required")
        if not self.feishu.app_secret:
            errors.append("FEISHU_APP_SECRET is required")
        if not self.feishu.app_token:
            errors.append("FEISHU_APP_TOKEN is required")
        if not self.feishu.table_id:
            errors.append("FEISHU_TABLE_ID is required")

        # 数据库配置验证
        if self.database.type == "mysql":
            if not self.database.mysql_host:
                errors.append("MYSQL_HOST is required when DB_TYPE=mysql")
            if not self.database.mysql_user:
                errors.append("MYSQL_USER is required when DB_TYPE=mysql")
            if not self.database.mysql_password:
                errors.append("MYSQL_PASSWORD is required when DB_TYPE=mysql")
            if not self.database.mysql_database:
                errors.append("MYSQL_DATABASE is required when DB_TYPE=mysql")

        # 认证配置验证（P2-9增强）
        if not self.auth.api_keys:
            errors.append(
                "API_KEYS is required (at least one admin key). "
                "Set API_KEYS environment variable before starting the application."
            )

        # 警告：如果API Key看起来像默认值
        for key in self.auth.api_keys:
            if "default" in key.lower() or "dev" in key.lower() or "test" in key.lower():
                errors.append(
                    f"API Key '{key[:10]}...' looks like a development key. "
                    "Please use strong, unique keys in production."
                )

        return errors

    def print_summary(self) -> None:
        """打印配置摘要（用于启动日志）"""
        print("=" * 60)
        print("Configuration Summary")
        print("=" * 60)
        print(f"Feishu App ID: {self.feishu.app_id[:8]}..." if self.feishu.app_id else "Feishu App ID: NOT SET")
        print(f"Database Type: {self.database.type}")
        print(f"Database Path: {self.database.file_path}")
        print(f"API Keys Count: {len(self.auth.api_keys)}")
        print(f"Readonly Keys Count: {len(self.auth.readonly_api_keys)}")
        print(f"Rate Limit: {self.auth.rate_limit} req/min")
        print(f"Log Level: {self.logging.level}")
        print(f"Log Format: {self.logging.format}")
        print(f"CORS Origins: {', '.join(self.server.allowed_origins)}")
        print(f"Sync Interval: {self.server.sync_interval_minutes} minutes")
        print("=" * 60)


# 全局配置实例
settings = Settings()


# 测试代码
if __name__ == "__main__":
    # 打印配置摘要
    settings.print_summary()

    # 验证配置
    errors = settings.validate()
    if errors:
        print("\n⚠️  Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ Configuration is valid")

    # 访问示例
    print("\n" + "=" * 60)
    print("Usage Examples")
    print("=" * 60)
    print(f"settings.feishu.app_id: {settings.feishu.app_id[:8]}..." if settings.feishu.app_id else "settings.feishu.app_id: NOT SET")
    print(f"settings.database.file_path: {settings.database.file_path}")
    print(f"settings.auth.api_keys: {settings.auth.api_keys}")
    print(f"settings.logging.level: {settings.logging.level}")
    print(f"settings.server.allowed_origins: {settings.server.allowed_origins}")
