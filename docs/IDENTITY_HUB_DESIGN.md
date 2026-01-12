# Identity Hub - 统一身份认证平台技术设计方案

**版本**: v1.0
**日期**: 2025-10-30
**作者**: Claude Code
**状态**: 设计阶段

---

## 目录

1. [项目概述](#项目概述)
2. [核心架构](#核心架构)
3. [数据库设计](#数据库设计)
4. [核心模块](#核心模块)
5. [API设计](#api设计)
6. [安全设计](#安全设计)
7. [部署方案](#部署方案)
8. [实施路线图](#实施路线图)

---

## 项目概述

### 背景

当前公司内部有多个业务系统（派工系统、报表系统等），每个系统都需要实现用户认证功能。这导致：
- 重复开发认证模块
- 用户体验不一致（每个系统单独登录）
- 账号管理分散，维护成本高
- 安全策略不统一

### 目标

设计并实现一个**独立的、可扩展的统一身份认证平台（Identity Hub）**，作为公司内所有系统的SSO（Single Sign-On）中心。

### 核心特性

- ✅ **统一登录**: 一次登录，全系统通用
- ✅ **标准协议**: 完全遵循OAuth 2.0 / OpenID Connect标准
- ✅ **多身份源**: 支持飞书、LDAP、钉钉等多种身份提供商
- ✅ **可扩展**: 插件式架构，易于接入新的IdP
- ✅ **高安全**: PKCE、Token撤销、审计日志
- ✅ **易集成**: 提供标准OAuth客户端SDK

---

## 核心架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                   Identity Hub (统一认证平台)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  身份源同步  │  │  OAuth服务器 │  │  用户管理    │      │
│  │  Sync Engine │  │  (RFC 6749)  │  │  Admin Panel │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                  ↑                  ↑              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          核心数据层 (Users, Clients, Tokens)         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
       ↑                              ↓
       │ 定时同步                     │ OAuth 2.0
┌──────┴──────┐               ┌───────┴─────────────┐
│   飞书API   │               │  客户端系统         │
│ (钉钉/LDAP) │               │ • 派工系统          │
└─────────────┘               │ • 报表系统          │
                              │ • 其他业务系统      │
                              └─────────────────────┘
```

### 数据流

```
1. 用户同步: 飞书API → Identity Hub → users表
2. 用户登录: 客户端 → Identity Hub → 飞书OAuth → 返回code → 换token
3. 资源访问: 客户端携带token → Identity Hub验证 → 返回用户信息
4. Token刷新: 客户端 → refresh_token → 换新access_token
```

### 技术栈

| 组件 | 技术选型 | 原因 |
|------|---------|------|
| 后端框架 | FastAPI | 高性能、异步支持、自动生成API文档 |
| 数据库 | SQLite/PostgreSQL | 开发用SQLite，生产用PostgreSQL |
| 缓存 | Redis | Token缓存、Session存储 |
| 前端 | React | 管理后台界面 |
| 协议 | OAuth 2.0 + OIDC | 业界标准，兼容性好 |
| 部署 | Docker + Docker Compose | 容器化，易于部署 |

---

## 数据库设计

### ER图

```
┌────────────────┐       ┌────────────────┐       ┌────────────────┐
│identity_sources│──────▶│     users      │◀──────│ oauth_tokens   │
└────────────────┘       └────────────────┘       └────────────────┘
                                 ▲                         ▲
                                 │                         │
                                 │                         │
                         ┌───────┴────────┐       ┌───────┴────────┐
                         │oauth_clients   │──────▶│authorization   │
                         │                │       │     codes      │
                         └────────────────┘       └────────────────┘
```

### 核心表结构

#### 1. identity_sources（身份源表）

```sql
CREATE TABLE identity_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,           -- 'feishu-main', 'ldap-corp'
    type TEXT NOT NULL,                  -- 'feishu', 'ldap', 'dingtalk'
    config TEXT NOT NULL,                -- JSON配置
    enabled BOOLEAN DEFAULT 1,
    priority INTEGER DEFAULT 0,          -- 优先级
    last_sync_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**字段说明**:
- `type`: 身份源类型，支持feishu/ldap/dingtalk等
- `config`: JSON格式配置，如`{"app_id": "xxx", "app_secret": "yyy"}`
- `priority`: 用于用户去重和合并

#### 2. users（用户表）

```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,            -- UUID格式
    source_id INTEGER NOT NULL,          -- 来自哪个身份源
    source_user_id TEXT NOT NULL,        -- 在源系统中的ID

    -- 基础信息
    username TEXT UNIQUE,
    email TEXT,
    mobile TEXT,
    name TEXT NOT NULL,
    avatar_url TEXT,

    -- 组织信息
    department_ids TEXT,                 -- JSON数组
    title TEXT,

    -- 状态
    status INTEGER DEFAULT 1,            -- 1=active, 0=inactive
    is_admin BOOLEAN DEFAULT 0,

    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync_at TIMESTAMP,
    last_login_at TIMESTAMP,

    FOREIGN KEY (source_id) REFERENCES identity_sources(id),
    UNIQUE(source_id, source_user_id)
);
```

#### 3. oauth_clients（OAuth客户端应用表）

```sql
CREATE TABLE oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret TEXT NOT NULL,         -- 加密存储

    name TEXT NOT NULL,
    description TEXT,
    logo_url TEXT,

    redirect_uris TEXT NOT NULL,         -- JSON数组
    allowed_scopes TEXT DEFAULT 'openid profile email',

    is_trusted BOOLEAN DEFAULT 0,        -- 是否信任（跳过授权页）
    is_public BOOLEAN DEFAULT 0,         -- 是否公开客户端（PKCE）

    token_lifetime INTEGER DEFAULT 7200,
    refresh_token_lifetime INTEGER DEFAULT 2592000,

    owner_user_id TEXT,
    status INTEGER DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (owner_user_id) REFERENCES users(user_id)
);
```

#### 4. oauth_authorization_codes（授权码表）

```sql
CREATE TABLE oauth_authorization_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    scope TEXT NOT NULL,
    code_challenge TEXT,                 -- PKCE
    code_challenge_method TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

#### 5. oauth_tokens（Token表）

```sql
CREATE TABLE oauth_tokens (
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
```

#### 6. user_consents（用户授权记录表）

```sql
CREATE TABLE user_consents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                -- NULL表示永久授权

    UNIQUE(user_id, client_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
);
```

#### 7. cross_app_permissions（跨应用权限表）

```sql
CREATE TABLE cross_app_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    client_id TEXT,                      -- NULL表示全局权限
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    permission TEXT NOT NULL,            -- 'read', 'write', 'admin'
    granted_by TEXT,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
);
```

#### 8. audit_logs（审计日志表）

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    client_id TEXT,
    action TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    metadata TEXT,                       -- JSON

    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
);
```

---

## 核心模块

### 1. 身份源模块（identity_sources/）

#### 基类设计

```python
class IdentitySourceBase(ABC):
    """所有身份源必须继承此基类"""

    @abstractmethod
    def sync_users(self) -> List[Dict]:
        """同步用户列表"""
        pass

    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """获取OAuth授权URL"""
        pass

    @abstractmethod
    def handle_callback(self, code: str, state: str) -> Dict:
        """处理OAuth回调"""
        pass
```

#### 飞书身份源实现

```python
class FeishuIdentitySource(IdentitySourceBase):
    """飞书身份源"""

    def sync_users(self):
        # 1. 获取tenant_access_token
        # 2. 调用通讯录API获取用户列表
        # 3. 转换为标准用户格式
        # 4. 返回用户列表
        pass
```

### 2. OAuth 2.0服务器模块（oauth/）

#### 核心流程

```
1. Authorization Code Flow:
   用户 → /oauth/authorize → 登录验证 → 生成code → 跳转客户端
   客户端 → /oauth/token + code → 验证 → 返回access_token

2. Token Refresh:
   客户端 → /oauth/token + refresh_token → 验证 → 新access_token

3. Token Validation:
   客户端 → /oauth/userinfo + access_token → 用户信息

4. Token Revocation:
   客户端 → /oauth/revoke + token → 撤销token
```

#### 安全特性

- **PKCE支持**: 防止授权码劫持（RFC 7636）
- **State参数**: 防止CSRF攻击
- **Token加密**: 使用secrets.token_urlsafe生成随机token
- **授权码限时**: 10分钟有效期
- **Token限时**: access_token默认2小时，refresh_token默认30天

### 3. 同步引擎（sync/）

#### 同步策略

```python
# 定时同步（每小时）
scheduler = BackgroundScheduler()
scheduler.add_job(
    sync_all_sources,
    'interval',
    hours=1,
    id='sync_identity_sources'
)
```

#### 用户合并逻辑

当多个身份源有相同用户时（如飞书+LDAP），根据`priority`字段合并：
- 高优先级身份源的数据覆盖低优先级
- 保留最早创建时间的user_id

---

## API设计

### OAuth 2.0标准端点

#### 1. 授权端点

```http
GET /oauth/authorize
  ?client_id=xxx
  &redirect_uri=http://10.242.94.9:8080/callback
  &response_type=code
  &scope=openid profile email
  &state=random_string
  &code_challenge=xxx          # PKCE
  &code_challenge_method=S256

Response:
- 302 重定向到 redirect_uri?code=xxx&state=xxx
```

#### 2. Token端点

```http
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=xxx
&redirect_uri=http://10.242.94.9:8080/callback
&client_id=xxx
&client_secret=xxx
&code_verifier=xxx           # PKCE

Response:
{
  "access_token": "xxx",
  "token_type": "Bearer",
  "expires_in": 7200,
  "refresh_token": "xxx",
  "scope": "openid profile email"
}
```

#### 3. UserInfo端点

```http
GET /oauth/userinfo
Authorization: Bearer access_token

Response:
{
  "sub": "user-uuid",
  "name": "张三",
  "email": "zhangsan@company.com",
  "phone_number": "13800138000"
}
```

#### 4. Token撤销端点

```http
POST /oauth/revoke
Content-Type: application/x-www-form-urlencoded

token=xxx
&token_type_hint=access_token

Response:
{"message": "Token revoked"}
```

### 管理后台API

#### 用户管理

```http
GET /admin/users?page=1&per_page=20&search=张三
POST /admin/users
PUT /admin/users/{user_id}
DELETE /admin/users/{user_id}
```

#### 客户端管理

```http
GET /admin/oauth-clients
POST /admin/oauth-clients
PUT /admin/oauth-clients/{client_id}
DELETE /admin/oauth-clients/{client_id}
```

#### 身份源管理

```http
GET /admin/identity-sources
POST /admin/identity-sources
POST /admin/identity-sources/{id}/sync  # 手动触发同步
```

---

## 安全设计

### 1. Token安全

- **随机性**: 使用`secrets.token_urlsafe(48)`生成token（384位熵）
- **短生命周期**: access_token默认2小时
- **刷新机制**: refresh_token用于无感刷新
- **撤销机制**: 支持主动撤销token

### 2. 密钥存储

- `client_secret`使用bcrypt加密存储
- 数据库连接字符串使用环境变量
- 敏感配置不提交到Git

### 3. PKCE（Proof Key for Code Exchange）

防止授权码劫持攻击：

```python
# 客户端生成
code_verifier = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).decode().rstrip("=")

# 授权时发送code_challenge
# Token换取时发送code_verifier进行验证
```

### 4. 审计日志

记录所有敏感操作：
- 用户登录/登出
- Token签发/撤销
- 权限变更
- 管理员操作

---

## 部署方案

### 开发环境

```bash
# 1. 克隆代码
git clone <repo>
cd identity-hub

# 2. 配置环境变量
cp .env.example .env
# 编辑.env，填入飞书配置

# 3. 启动服务
docker-compose up -d

# 访问
# - Identity Hub: http://10.242.94.9:9000
# - 管理后台: http://10.242.94.9:9000/admin
```

### 生产环境

#### Docker Compose配置

```yaml
version: '3.8'

services:
  identity-hub:
    image: identity-hub:latest
    container_name: identity-hub-prod
    restart: always
    ports:
      - "9000:9000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/identity_hub
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    restart: always
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=identity_hub
      - POSTGRES_USER=identity_hub
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis-data:/data

volumes:
  postgres-data:
  redis-data:
```

#### 高可用方案

1. **多实例部署**: 使用Nginx做负载均衡
2. **数据库主从**: PostgreSQL主从复制
3. **Redis集群**: Redis Sentinel或Cluster
4. **监控告警**: Prometheus + Grafana

---

## 实施路线图

### Phase 1: 基础设施（1周）

- [x] 项目目录结构
- [x] 数据库schema设计
- [x] Docker开发环境
- [ ] 配置管理模块
- [ ] 数据库migration脚本

### Phase 2: 核心功能（1周）

- [ ] 身份源基类实现
- [ ] 飞书身份源实现
- [ ] 用户同步引擎
- [ ] OAuth 2.0服务器核心
- [ ] OAuth标准端点

### Phase 3: 客户端对接（2-3天）

- [ ] 派工系统改造
- [ ] OAuth客户端SDK
- [ ] 集成测试

### Phase 4: 管理后台（3-4天）

- [ ] 用户管理界面
- [ ] 客户端管理界面
- [ ] 身份源管理界面
- [ ] 审计日志查看

### Phase 5: 高级功能（1周）

- [ ] PKCE支持
- [ ] 跨应用权限
- [ ] Redis缓存
- [ ] Token自动刷新

### Phase 6: 部署上线（2-3天）

- [ ] 生产环境配置
- [ ] 性能测试
- [ ] 安全测试
- [ ] 监控告警
- [ ] 文档完善

**预计总工期**: 3-4周

---

## 附录

### A. 相关RFC文档

- [RFC 6749: OAuth 2.0 Authorization Framework](https://tools.ietf.org/html/rfc6749)
- [RFC 7636: PKCE](https://tools.ietf.org/html/rfc7636)
- [RFC 7009: Token Revocation](https://tools.ietf.org/html/rfc7009)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)

### B. 飞书API文档

- [飞书开放平台](https://open.feishu.cn/)
- [网页应用登录](https://open.feishu.cn/document/common-capabilities/sso/web-application-sso/web-app-overview)
- [通讯录API](https://open.feishu.cn/document/server-docs/contact-v3/user/list)

### C. 术语表

| 术语 | 说明 |
|------|------|
| IdP | Identity Provider，身份提供商 |
| SSO | Single Sign-On，单点登录 |
| OAuth | 开放授权协议 |
| OIDC | OpenID Connect，基于OAuth 2.0的身份认证层 |
| PKCE | Proof Key for Code Exchange，授权码交换证明密钥 |
| JWT | JSON Web Token |

---

**文档维护**:
- 更新日期: 2025-10-30
- 下次审查: 开发完成后
- 负责人: 开发团队
