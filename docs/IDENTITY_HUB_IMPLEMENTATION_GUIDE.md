# Identity Hub 实施指南

**版本**: v1.0
**日期**: 2025-10-30
**目标**: 从零开始搭建Identity Hub统一认证平台

---

## 目录

1. [前置准备](#前置准备)
2. [Phase 1: 项目初始化](#phase-1-项目初始化)
3. [Phase 2: 核心功能开发](#phase-2-核心功能开发)
4. [Phase 3: 派工系统对接](#phase-3-派工系统对接)
5. [Phase 4: 管理后台](#phase-4-管理后台)
6. [Phase 5: 生产部署](#phase-5-生产部署)
7. [常见问题](#常见问题)

---

## 前置准备

### 1. 开发环境要求

- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- Git

### 2. 飞书配置

登录 https://open.feishu.cn/app 创建应用并配置权限：

**必需权限**:
- `contact:user:read` (获取通讯录用户信息)
- `authen:v1` (身份验证)

**回调地址**:
```
http://10.242.94.9:9000/oauth/feishu/callback
```

### 3. 环境变量准备

```bash
# 飞书凭证
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx

# 数据库（开发环境用SQLite）
DATABASE_URL=/app/data/identity-hub.db

# 密钥（生成随机密钥）
SECRET_KEY=$(openssl rand -hex 32)

# 服务配置
HOST=0.0.0.0
PORT=9000
ALLOWED_ORIGINS=http://10.242.94.9:3000,http://10.242.94.9:8080,http://10.242.94.9:9000
```

---

## Phase 1: 项目初始化

### 1.1 创建项目目录

```bash
# 在Task_feishu同级目录创建identity-hub项目
cd /home/jian/code
mkdir identity-hub
cd identity-hub

# 创建完整目录结构
mkdir -p backend/{identity_sources,oauth,sync,admin,utils,migrations}
mkdir -p frontend/src/{pages,components,utils}
mkdir -p data docs tests

# 创建__init__.py
touch backend/__init__.py
touch backend/identity_sources/__init__.py
touch backend/oauth/__init__.py
touch backend/sync/__init__.py
touch backend/admin/__init__.py
touch backend/utils/__init__.py
```

### 1.2 初始化Git

```bash
git init
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
venv/
.env

# 数据库
*.db
*.db-journal
data/

# IDE
.vscode/
.idea/
*.swp

# Docker
.dockerignore

# 日志
*.log
EOF

git add .
git commit -m "feat: initialize Identity Hub project structure"
```

### 1.3 创建requirements.txt

```bash
cat > backend/requirements.txt << 'EOF'
# Web框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# 数据库
databases==0.8.0
aiosqlite==0.19.0
alembic==1.12.1

# HTTP客户端
requests==2.31.0
httpx==0.25.1

# 安全
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0

# 工具
pydantic==2.5.0
pydantic-settings==2.1.0
apscheduler==3.10.4

# 可选(生产环境)
# psycopg2-binary==2.9.9
# redis==5.0.1
EOF
```

### 1.4 创建数据库Migration脚本

```bash
cat > backend/migrations/001_init_schema.sql << 'EOF'
-- Identity Hub数据库初始化脚本
-- 版本: v1.0
-- 日期: 2025-10-30

-- 1. 身份源表
CREATE TABLE IF NOT EXISTS identity_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    config TEXT NOT NULL,
    enabled BOOLEAN DEFAULT 1,
    priority INTEGER DEFAULT 0,
    last_sync_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    source_id INTEGER NOT NULL,
    source_user_id TEXT NOT NULL,

    username TEXT UNIQUE,
    email TEXT,
    mobile TEXT,
    name TEXT NOT NULL,
    avatar_url TEXT,

    department_ids TEXT,
    title TEXT,

    status INTEGER DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync_at TIMESTAMP,
    last_login_at TIMESTAMP,

    FOREIGN KEY (source_id) REFERENCES identity_sources(id),
    UNIQUE(source_id, source_user_id)
);

CREATE INDEX IF NOT EXISTS idx_users_source ON users(source_id, source_user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

-- 3. OAuth客户端表
CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret TEXT NOT NULL,

    name TEXT NOT NULL,
    description TEXT,
    logo_url TEXT,

    redirect_uris TEXT NOT NULL,
    allowed_scopes TEXT DEFAULT 'openid profile email',

    is_trusted BOOLEAN DEFAULT 0,
    is_public BOOLEAN DEFAULT 0,

    token_lifetime INTEGER DEFAULT 7200,
    refresh_token_lifetime INTEGER DEFAULT 2592000,

    owner_user_id TEXT,
    status INTEGER DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (owner_user_id) REFERENCES users(user_id)
);

-- 4. OAuth授权码表
CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    scope TEXT NOT NULL,
    code_challenge TEXT,
    code_challenge_method TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_codes_expires ON oauth_authorization_codes(expires_at);

-- 5. OAuth Token表
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    access_token TEXT UNIQUE NOT NULL,
    refresh_token TEXT UNIQUE,

    client_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    scope TEXT NOT NULL,

    access_token_expires_at TIMESTAMP NOT NULL,
    refresh_token_expires_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_tokens_access ON oauth_tokens(access_token);
CREATE INDEX IF NOT EXISTS idx_tokens_refresh ON oauth_tokens(refresh_token);
CREATE INDEX IF NOT EXISTS idx_tokens_expires ON oauth_tokens(access_token_expires_at);

-- 6. 用户授权记录表
CREATE TABLE IF NOT EXISTS user_consents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,

    UNIQUE(user_id, client_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
);

-- 7. 跨应用权限表
CREATE TABLE IF NOT EXISTS cross_app_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    client_id TEXT,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    permission TEXT NOT NULL,
    granted_by TEXT,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
);

CREATE INDEX IF NOT EXISTS idx_permissions_user ON cross_app_permissions(user_id);

-- 8. 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    client_id TEXT,
    action TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    metadata TEXT,

    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);

-- 初始化默认身份源（飞书）
INSERT OR IGNORE INTO identity_sources (id, name, type, config, enabled, priority)
VALUES (1, 'feishu-main', 'feishu', '{}', 1, 100);

COMMIT;
EOF
```

### 1.5 创建配置文件

```bash
cat > backend/config.py << 'EOF'
"""配置管理模块"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "Identity Hub"
    VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 9000

    # 数据库
    DATABASE_URL: str = "sqlite:///./data/identity-hub.db"

    # 安全
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # 飞书配置
    FEISHU_APP_ID: str
    FEISHU_APP_SECRET: str

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://10.242.94.9:3000",
        "http://10.242.94.9:8080",
        "http://10.242.94.9:9000"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
EOF
```

### 1.6 创建数据库连接模块

```bash
cat > backend/database.py << 'EOF'
"""数据库连接模块"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DB_FILE = "./data/identity-hub.db"

def init_db():
    """初始化数据库"""
    # 确保data目录存在
    Path(DB_FILE).parent.mkdir(parents=True, exist_ok=True)

    # 执行migration脚本
    migration_file = Path(__file__).parent / "migrations" / "001_init_schema.sql"

    if not migration_file.exists():
        logger.warning(f"Migration file not found: {migration_file}")
        return

    with open(migration_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = sqlite3.connect(DB_FILE)
    conn.executescript(schema_sql)
    conn.close()

    logger.info("Database initialized successfully")

@contextmanager
def get_db_connection():
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()
EOF
```

### 1.7 运行数据库初始化

```bash
cd backend
python << 'EOF'
from database import init_db
init_db()
print("✅ Database initialized successfully!")
EOF
```

---

## Phase 2: 核心功能开发

详见 `docs/IDENTITY_HUB_TODOLIST.md` 中的具体任务。

核心模块实现顺序：
1. 身份源基类和飞书实现
2. OAuth 2.0服务器
3. 同步引擎
4. FastAPI主应用

---

## Phase 3: 派工系统对接

### 3.1 在Identity Hub注册派工系统

```bash
# 使用Python脚本注册
python << 'EOF'
import secrets
import json
from database import get_db_connection

client_id = "dispatch_system_" + secrets.token_hex(8)
client_secret = secrets.token_urlsafe(32)

redirect_uris = json.dumps([
    "http://10.242.94.9:8080/auth/callback",
    "http://10.242.94.9:3000/auth/callback"
])

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO oauth_clients
        (client_id, client_secret, name, redirect_uris, is_trusted)
        VALUES (?, ?, ?, ?, 1)
    """, (client_id, client_secret, "派工系统", redirect_uris))

print(f"✅ Client registered successfully!")
print(f"Client ID: {client_id}")
print(f"Client Secret: {client_secret}")
print(f"\nAdd to Task_feishu/.env:")
print(f"IDENTITY_HUB_CLIENT_ID={client_id}")
print(f"IDENTITY_HUB_CLIENT_SECRET={client_secret}")
EOF
```

### 3.2 修改派工系统环境变量

```bash
cd /home/jian/code/Task_feishu

# 追加Identity Hub配置
cat >> .env << 'EOF'

# Identity Hub配置
IDENTITY_HUB_CLIENT_ID=<从上一步获取>
IDENTITY_HUB_CLIENT_SECRET=<从上一步获取>
IDENTITY_HUB_URL=http://10.242.94.9:9000
IDENTITY_HUB_REDIRECT_URI=http://10.242.94.9:8080/auth/callback
EOF
```

### 3.3 实现派工系统认证客户端

创建 `backend/auth_identity_hub.py`（代码见技术方案文档）

### 3.4 修改派工系统API端点

修改 `backend/main.py`，添加Identity Hub认证逻辑（代码见技术方案文档）

---

## Phase 4: 管理后台

### 4.1 创建React项目

```bash
cd /home/jian/code/identity-hub/frontend
npx create-react-app . --template typescript
```

### 4.2 实现管理页面

- 用户列表页
- OAuth客户端管理页
- 身份源配置页
- 审计日志页

---

## Phase 5: 生产部署

### 5.1 创建Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
```

### 5.2 创建Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  identity-hub:
    build: ./backend
    container_name: identity-hub
    ports:
      - "9000:9000"
    environment:
      - DATABASE_URL=/app/data/identity-hub.db
      - SECRET_KEY=${SECRET_KEY}
      - FEISHU_APP_ID=${FEISHU_APP_ID}
      - FEISHU_APP_SECRET=${FEISHU_APP_SECRET}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### 5.3 启动服务

```bash
docker-compose up -d
docker-compose logs -f
```

---

## 常见问题

### Q1: 数据库连接失败

**问题**: `sqlite3.OperationalError: unable to open database file`

**解决**:
```bash
# 确保data目录存在且有写权限
mkdir -p data
chmod 755 data
```

### Q2: 飞书回调失败

**问题**: 飞书OAuth回调返回`redirect_uri_mismatch`

**解决**:
1. 检查飞书开放平台配置的回调地址
2. 确保完全匹配（包括http/https和端口）
3. 重新保存配置

### Q3: Token验证失败

**问题**: `/oauth/userinfo`返回401

**解决**:
```bash
# 检查token是否过期
# 检查Authorization头格式: Bearer <token>
# 查看数据库中token的expires_at字段
```

### Q4: CORS错误

**问题**: 前端请求被CORS拦截

**解决**:
```python
# 确保main.py中配置了正确的CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://10.242.94.9:3000",
        "http://10.242.94.9:8080"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 下一步

阅读 `docs/IDENTITY_HUB_TODOLIST.md` 查看详细的任务清单，开始逐个实现功能模块。

---

**维护信息**:
- 文档版本: v1.0
- 最后更新: 2025-10-30
- 负责人: 开发团队
