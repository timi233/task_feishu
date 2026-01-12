# Identity Hub 独立迁移部署手册

**版本**: v1.0
**日期**: 2025-11-04
**适用场景**: 将Identity Hub从开发环境迁移到生产环境，作为独立的OAuth认证中心

---

## 📋 目录

1. [迁移概述](#迁移概述)
2. [环境要求](#环境要求)
3. [迁移前准备](#迁移前准备)
4. [创建Docker配置](#创建docker配置)
5. [迁移步骤](#迁移步骤)
6. [数据库迁移](#数据库迁移)
7. [配置修改指南](#配置修改指南)
8. [启动和验证](#启动和验证)
9. [对接客户端系统](#对接客户端系统)
10. [故障排查](#故障排查)
11. [运维管理](#运维管理)

---

## 迁移概述

### 什么是Identity Hub？

Identity Hub是企业统一身份认证中心，提供：
- ✅ **OAuth 2.0 / OpenID Connect** 标准认证服务
- ✅ **单点登录 (SSO)** 能力
- ✅ **多身份源** 支持（飞书、LDAP等）
- ✅ **用户和组织同步**
- ✅ **权限管理**

### 为什么要独立部署？

当前开发环境中，Identity Hub与派工系统运行在同一台服务器上，独立部署有以下优势：

1. **服务隔离** - 认证服务独立运行，不受其他系统影响
2. **多系统复用** - 一个Identity Hub可以服务多个业务系统
3. **安全性提升** - 独立的安全域，减少攻击面
4. **独立扩展** - 可独立升级和扩容

### 迁移架构

**当前开发环境**:
```
10.242.94.9
├── Identity Hub (uvicorn :9000) - 本地进程
└── 派工系统 (Docker :8080)
```

**迁移后生产环境**:
```
Identity Hub服务器 (NEW_IP)           派工系统服务器 (192.168.1.100)
┌─────────────────────────┐          ┌──────────────────────────┐
│ Identity Hub (Docker)   │          │ 派工系统 (Docker)        │
│ :9000                   │ ←─OAuth─→│ :8080                    │
│                         │          │                          │
│ - OAuth认证服务         │          │ - 业务系统               │
│ - 用户管理              │          │ - 依赖Identity Hub登录   │
│ - 组织同步              │          │                          │
└─────────────────────────┘          └──────────────────────────┘
```

### 迁移内容清单

**必须迁移**:
- ✅ Identity Hub后端代码 (~588KB)
- ✅ SQLite数据库 (~232KB)
  - 14张表，包含用户、OAuth客户端、角色权限等
- ✅ 环境配置文件 (.env)

**可选迁移**:
- 前端管理界面 (~20KB)
- 日志文件
- 文档

**总计**: 约1MB（不含日志）

---

## 环境要求

### 最低系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Linux (Ubuntu 20.04+) | Ubuntu 22.04 LTS |
| CPU | 1核 | 2核+ |
| 内存 | 512MB | 1GB+ |
| 磁盘空间 | 2GB可用 | 5GB+可用 |
| Docker | 20.10+ | 最新稳定版 |
| Docker Compose | 1.29+ | 2.x |

**为什么资源要求低？**
- SQLite数据库，无需独立数据库服务
- FastAPI轻量级框架
- 认证服务请求量通常不大

### 软件版本检查

```bash
# 检查Docker版本
docker --version
# 预期: Docker version 20.10.x 或更高

# 检查Docker Compose版本
docker-compose --version
# 预期: docker-compose version 1.29.x 或更高

# 检查磁盘空间
df -h
# 确保至少有2GB可用空间
```

### 网络要求

**端口需求**:
- `9000`: Identity Hub主服务端口（必需）
- 其他端口可选（如需HTTPS则需要443）

**外部服务连通性**:
```bash
# 检查是否能访问飞书API
curl -I https://open.feishu.cn

# 检查客户端系统是否能访问（从派工系统服务器测试）
# 将NEW_IP替换为Identity Hub服务器IP
curl -I http://NEW_IP:9000
```

---

## 迁移前准备

### 步骤1: 备份当前环境

在**旧服务器** (10.242.94.9) 上执行：

```bash
# 进入Identity Hub目录
cd /home/jian/code/identity-hub

# 备份整个项目（推荐）
tar -czf ~/identity-hub-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='*.log' \
  backend/ \
  frontend/ \
  data/ \
  docs/ \
  .env \
  .env.example \
  README.md

# 单独备份数据库（额外保险）
cp data/identity-hub.db data/identity-hub.db.backup-$(date +%Y%m%d-%H%M%S)

# 检查备份文件
ls -lh ~/identity-hub-backup-*.tar.gz
# 预期大小: 约1-2MB
```

### 步骤2: 导出关键配置

**导出OAuth客户端配置**（重要）:

```bash
cd /home/jian/code/identity-hub

# 导出所有OAuth客户端信息
sqlite3 data/identity-hub.db <<EOF
.mode csv
.output ~/oauth_clients_export.csv
SELECT client_id, client_name, client_secret, redirect_uris, scope, created_at
FROM oauth_clients;
.quit
EOF

# 查看导出内容
cat ~/oauth_clients_export.csv
```

**导出用户列表**（可选，用于验证）:

```bash
sqlite3 data/identity-hub.db <<EOF
.mode csv
.output ~/users_export.csv
SELECT user_id, username, email, feishu_user_id, created_at
FROM users LIMIT 100;
.quit
EOF
```

### 步骤3: 记录当前配置

创建配置记录文件：

```bash
cat > ~/identity-hub-migration-info.txt <<EOF
=== Identity Hub迁移配置记录 ===
迁移日期: $(date)
旧服务器IP: 10.242.94.9
新服务器IP: ____________ (待填写)

=== 当前配置 ===
服务端口: 9000
飞书应用ID: $(grep FEISHU_APP_ID .env | cut -d'=' -f2)
飞书回调地址: $(grep FEISHU_REDIRECT_URI .env | cut -d'=' -f2)
数据库大小: $(du -sh data/identity-hub.db)

=== OAuth客户端数量 ===
$(sqlite3 data/identity-hub.db "SELECT COUNT(*) FROM oauth_clients;") 个客户端

=== 用户数量 ===
$(sqlite3 data/identity-hub.db "SELECT COUNT(*) FROM users;") 个用户

=== 部门数量 ===
$(sqlite3 data/identity-hub.db "SELECT COUNT(*) FROM departments;") 个部门
EOF

cat ~/identity-hub-migration-info.txt
```

---

## 创建Docker配置

Identity Hub当前没有Docker配置，我们需要创建Dockerfile和docker-compose.yml。

### 步骤1: 创建Dockerfile

在**旧服务器**上，在Identity Hub项目根目录创建Dockerfile：

```bash
cd /home/jian/code/identity-hub

cat > Dockerfile <<'EOF'
# Identity Hub Dockerfile
# 基于Python 3.11官方镜像

FROM python:3.11-slim

# 设置时区为北京时间
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY backend/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 9000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/health').read()" || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
EOF

echo "✅ Dockerfile创建成功"
```

### 步骤2: 添加健康检查端点

编辑 `backend/main.py`，添加健康检查端点（如果还没有）：

```bash
# 检查是否已有健康检查端点
grep -q "def health" backend/main.py

if [ $? -ne 0 ]; then
  # 如果没有，需要手动添加到main.py
  echo "⚠️  需要在backend/main.py中添加健康检查端点"
  echo "请在FastAPI app创建后添加以下代码："
  cat <<'EOF'

@app.get("/health")
async def health():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "identity-hub",
        "timestamp": time.time()
    }
EOF
else
  echo "✅ 健康检查端点已存在"
fi
```

### 步骤3: 创建docker-compose.yml

```bash
cd /home/jian/code/identity-hub

cat > docker-compose.yml <<'EOF'
# Identity Hub Docker Compose配置

version: '3.8'

services:
  identity-hub:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: identity-hub
    ports:
      - "9000:9000"  # Identity Hub主服务端口
    env_file:
      - .env  # 从.env文件加载环境变量
    environment:
      # Docker环境特定配置（覆盖.env中的配置）
      - HOST=0.0.0.0
      - PORT=9000
    volumes:
      # 持久化数据库文件
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:9000/health').read()"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: unless-stopped

    # 可选: Nginx反向代理（用于HTTPS）
    # 取消注释以下内容启用
    # depends_on:
    #   - nginx

  # nginx:
  #   image: nginx:alpine
  #   container_name: identity-hub-nginx
  #   ports:
  #     - "443:443"
  #   volumes:
  #     - ./nginx.conf:/etc/nginx/nginx.conf:ro
  #     - ./ssl:/etc/nginx/ssl:ro
  #   depends_on:
  #     - identity-hub
  #   restart: unless-stopped
EOF

echo "✅ docker-compose.yml创建成功"
```

### 步骤4: 更新备份包含Docker配置

```bash
cd /home/jian/code/identity-hub

# 重新打包，包含新创建的Docker配置
tar -czf ~/identity-hub-docker-migration-$(date +%Y%m%d).tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='*.log' \
  backend/ \
  data/ \
  .env \
  Dockerfile \
  docker-compose.yml \
  README.md

ls -lh ~/identity-hub-docker-migration-*.tar.gz
# 预期大小: 约1-2MB
```

---

## 迁移步骤

### 步骤1: 传输文件到新服务器

**方式1: 使用scp**

```bash
# 在旧服务器上执行
scp ~/identity-hub-docker-migration-*.tar.gz user@NEW_SERVER_IP:/tmp/
```

**方式2: 使用rsync（推荐，支持断点续传）**

```bash
# 在旧服务器上执行
rsync -avz --progress ~/identity-hub-docker-migration-*.tar.gz user@NEW_SERVER_IP:/tmp/
```

### 步骤2: 在新服务器解压文件

```bash
# SSH登录到新服务器
ssh user@NEW_SERVER_IP

# 创建项目目录
mkdir -p ~/identity-hub
cd ~/identity-hub

# 解压迁移包
tar -xzf /tmp/identity-hub-docker-migration-*.tar.gz

# 检查目录结构
tree -L 2 .
# 预期输出:
# .
# ├── backend/
# ├── data/
# │   └── identity-hub.db
# ├── .env
# ├── Dockerfile
# ├── docker-compose.yml
# └── README.md
```

### 步骤3: 修改配置文件

**必须修改的配置**（详见[配置修改指南](#配置修改指南)）：

```bash
cd ~/identity-hub

# 编辑.env文件
nano .env

# 需要修改的配置项:
# 1. FEISHU_REDIRECT_URI - 飞书回调地址
# 2. ALLOWED_ORIGINS - CORS配置
```

**关键配置修改**:

假设新服务器IP是 `192.168.1.200`

```bash
# 使用sed快速替换
sed -i 's/10.242.94.9/192.168.1.200/g' .env

# 验证修改
grep -E "REDIRECT_URI|ALLOWED_ORIGINS" .env
```

### 步骤4: 构建Docker镜像

```bash
cd ~/identity-hub

# 构建镜像
docker-compose build

# 查看构建的镜像
docker images | grep identity-hub
```

### 步骤5: 启动Identity Hub

```bash
# 启动容器
docker-compose up -d

# 查看容器状态
docker-compose ps

# 查看启动日志
docker-compose logs -f identity-hub
```

**预期日志输出**:

```
identity-hub | 🚀 Starting Identity Hub...
identity-hub | ✅ Database initialized
identity-hub | ✅ Found 1 enabled identity sources
identity-hub |   - 飞书身份源 (feishu)
identity-hub | ✅ Identity Hub started successfully
identity-hub | INFO:     Uvicorn running on http://0.0.0.0:9000
```

---

## 数据库迁移

Identity Hub使用SQLite数据库，数据库文件已包含在迁移包中，无需额外迁移步骤。

### 验证数据库完整性

```bash
# 进入容器
docker exec -it identity-hub bash

# 安装SQLite客户端（如果镜像中没有）
apt-get update && apt-get install -y sqlite3

# 连接数据库
sqlite3 /app/data/identity-hub.db

-- 查看所有表
.tables

-- 验证关键表数据
SELECT COUNT(*) AS user_count FROM users;
SELECT COUNT(*) AS client_count FROM oauth_clients;
SELECT COUNT(*) AS dept_count FROM departments;

-- 查看OAuth客户端列表
SELECT client_id, client_name, redirect_uris FROM oauth_clients;

-- 退出
.quit
```

### 数据库表说明

| 表名 | 用途 | 重要性 | 数据量 |
|------|------|--------|--------|
| `users` | 用户信息 | ⭐⭐⭐⭐⭐ | 24+ |
| `oauth_clients` | OAuth客户端应用 | ⭐⭐⭐⭐⭐ | 1+ |
| `oauth_tokens` | OAuth访问令牌 | ⭐⭐⭐⭐ | 动态 |
| `oauth_authorization_codes` | OAuth授权码 | ⭐⭐⭐ | 动态 |
| `departments` | 部门信息 | ⭐⭐⭐ | 多个 |
| `roles` | 角色定义 | ⭐⭐⭐ | 多个 |
| `permissions` | 权限定义 | ⭐⭐⭐ | 多个 |
| `identity_sources` | 身份源配置 | ⭐⭐⭐⭐⭐ | 1+ |
| `audit_logs` | 审计日志 | ⭐⭐ | 动态 |

### 关键配置验证

**验证OAuth客户端配置**（最重要）:

```bash
docker exec -it identity-hub sqlite3 /app/data/identity-hub.db \
  "SELECT client_id, client_name, redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system';"
```

**预期输出**（派工系统的OAuth配置）:

```
task_feishu_dispatch_system|飞书派工系统|["http://10.242.94.9:8080/auth/callback", ...]
```

⚠️ **重要**: 如果派工系统迁移到新IP，需要更新此处的 `redirect_uris`（见下文）。

---

## 配置修改指南

### 配置修改清单

假设：
- Identity Hub新服务器IP: `192.168.1.200`
- 派工系统服务器IP: `192.168.1.100` (已迁移或待迁移)
- 飞书配置保持不变

| 配置项 | 文件 | 旧值 | 新值 | 是否必改 |
|--------|------|------|------|---------|
| 飞书回调地址 | `.env` | `http://10.242.94.9:9000/callback` | `http://192.168.1.200:9000/callback` | ✅ 必须 |
| CORS来源 | `.env` | `http://10.242.94.9:...` | `http://192.168.1.200:...` | ✅ 必须 |
| 派工系统回调地址 | 数据库 | `http://10.242.94.9:8080/auth/callback` | `http://192.168.1.100:8080/auth/callback` | ✅ 必须 |

### 详细修改步骤

#### 1. 修改 `.env` 文件

```bash
cd ~/identity-hub
nano .env
```

**修改以下配置项**:

```bash
# 飞书回调地址（Identity Hub自己的回调）
FEISHU_REDIRECT_URI=http://192.168.1.200:9000/callback

# CORS配置（允许哪些地址访问）
ALLOWED_ORIGINS=http://192.168.1.200:9000,http://192.168.1.100:8080,http://localhost:3000
```

**快速替换命令**:

```bash
# 替换所有10.242.94.9为新的Identity Hub IP
sed -i 's/10.242.94.9/192.168.1.200/g' .env

# 验证修改
cat .env | grep -E "FEISHU_REDIRECT|ALLOWED_ORIGINS"
```

#### 2. 更新飞书应用配置

登录飞书开放平台更新回调地址：

1. 访问: https://open.feishu.cn/app
2. 找到Identity Hub使用的飞书应用
3. 进入"安全设置" → "重定向URL"
4. 添加新的回调地址: `http://192.168.1.200:9000/callback`
5. 保存配置

#### 3. 更新数据库中的OAuth客户端配置

这是**最关键**的一步，如果派工系统也迁移了，必须更新其回调地址白名单。

```bash
# 进入容器
docker exec -it identity-hub bash

# 使用SQLite更新OAuth客户端配置
sqlite3 /app/data/identity-hub.db

-- 查看当前配置
SELECT client_id, redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system';

-- 更新派工系统的回调地址白名单
-- 将192.168.1.100替换为派工系统的新IP
UPDATE oauth_clients
SET redirect_uris='["http://192.168.1.100:8080/auth/callback", "http://localhost:8080/auth/callback", "http://192.168.1.100:3000/auth/callback", "http://localhost:3000/auth/callback"]'
WHERE client_id='task_feishu_dispatch_system';

-- 验证修改
SELECT client_id, redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system';

-- 退出
.quit
exit
```

#### 4. 重启容器应用配置

```bash
cd ~/identity-hub
docker-compose down
docker-compose up -d
```

### 配置验证

```bash
# 验证环境变量
docker exec identity-hub printenv | grep -E "FEISHU|ALLOWED_ORIGINS"

# 验证数据库配置
docker exec identity-hub sqlite3 /app/data/identity-hub.db \
  "SELECT redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system';"
```

---

## 启动和验证

### 启动服务

```bash
cd ~/identity-hub

# 启动容器（如果还未启动）
docker-compose up -d

# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f identity-hub
```

### 健康检查

#### 1. 容器健康状态

```bash
# 查看容器详细状态
docker inspect identity-hub | grep -A 10 Health

# 手动触发健康检查
docker exec identity-hub python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:9000/health').read())"
```

#### 2. 服务可访问性

```bash
# 从宿主机访问
curl http://localhost:9000/health

# 从外部访问（替换为实际IP）
curl http://192.168.1.200:9000/health

# 预期输出:
# {"status":"healthy","service":"identity-hub","timestamp":1730709600}
```

#### 3. OAuth端点验证

```bash
# 测试OAuth授权端点
curl "http://192.168.1.200:9000/oauth/authorize?client_id=task_feishu_dispatch_system&response_type=code&redirect_uri=http://192.168.1.100:8080/auth/callback&scope=openid+profile&state=test123"

# 应该返回302重定向到飞书登录页面
```

### 浏览器访问测试

1. **访问Identity Hub首页**

```
http://192.168.1.200:9000
```

应该显示Identity Hub登录或欢迎页面。

2. **访问API文档**

```
http://192.168.1.200:9000/docs
```

应该显示FastAPI Swagger文档。

3. **测试OAuth授权流程**

访问（替换参数）:
```
http://192.168.1.200:9000/oauth/authorize?client_id=task_feishu_dispatch_system&response_type=code&redirect_uri=http://192.168.1.100:8080/auth/callback&scope=openid+profile+email&state=test_state_123
```

应该重定向到飞书登录页面。

### 验证清单

- [ ] 容器状态为 `Up (healthy)`
- [ ] 健康检查端点返回200
- [ ] 可以从外部访问服务
- [ ] API文档页面可访问
- [ ] OAuth授权端点工作正常
- [ ] 数据库数据完整（用户、OAuth客户端等）
- [ ] 日志无ERROR级别错误

---

## 对接客户端系统

Identity Hub迁移完成后，需要更新客户端系统（如派工系统）的配置。

### 派工系统配置更新

**在派工系统服务器上**修改配置：

#### 1. 更新 `.env` 文件

```bash
# SSH登录到派工系统服务器
ssh user@DISPATCH_SYSTEM_IP

cd ~/task_feishu  # 或派工系统目录

# 编辑.env文件
nano .env

# 修改Identity Hub相关配置:
IDENTITY_HUB_URL=http://192.168.1.200:9000
IDENTITY_HUB_REDIRECT_URI=http://192.168.1.100:8080/auth/callback
```

**快速替换**:

```bash
# 将旧的Identity Hub地址替换为新地址
sed -i 's|http://10.242.94.9:9000|http://192.168.1.200:9000|g' .env

# 验证
grep IDENTITY_HUB .env
```

#### 2. 更新 docker-compose.yml（如果有覆盖配置）

```bash
# 检查是否在docker-compose.yml中覆盖了环境变量
grep -A 5 "IDENTITY_HUB" docker/docker-compose.yml

# 如果有，需要手动修改
```

#### 3. 重启派工系统

```bash
cd ~/task_feishu/docker
docker-compose down
docker-compose up -d

# 验证环境变量
docker exec docker_app_1 printenv | grep IDENTITY_HUB
```

### 完整OAuth登录流程测试

#### 测试步骤

1. **访问派工系统**

```
http://192.168.1.100:8080
```

2. **点击登录按钮**

应该跳转到:
```
http://192.168.1.200:9000/login?next=/oauth/authorize?client_id=...&redirect_uri=http://192.168.1.100:8080/auth/callback...
```

验证：
- ✅ Identity Hub地址正确 (192.168.1.200)
- ✅ 回调地址正确 (192.168.1.100)

3. **飞书扫码登录**

4. **验证回调和登录**

登录成功后应该：
- ✅ 跳转回派工系统 (192.168.1.100:8080)
- ✅ 显示用户名
- ✅ 可以访问受保护资源

### 其他客户端系统对接

如果有其他系统需要接入Identity Hub：

#### 1. 在Identity Hub中注册OAuth客户端

```bash
# 在Identity Hub服务器上
docker exec -it identity-hub bash

# 使用SQLite插入新客户端
sqlite3 /app/data/identity-hub.db

-- 插入新客户端（示例）
INSERT INTO oauth_clients (
  client_id,
  client_name,
  client_secret,
  redirect_uris,
  scope,
  grant_types,
  created_at
) VALUES (
  'new_app_client_id',
  '新系统名称',
  'generated_secret_key',  -- 使用openssl rand -hex 32生成
  '["http://new-app-ip:port/auth/callback"]',
  'openid profile email',
  '["authorization_code", "refresh_token"]',
  datetime('now')
);

.quit
```

#### 2. 在新系统中配置Identity Hub

参考派工系统的配置方式，在新系统的 `.env` 文件中添加：

```bash
IDENTITY_HUB_URL=http://192.168.1.200:9000
IDENTITY_HUB_CLIENT_ID=new_app_client_id
IDENTITY_HUB_CLIENT_SECRET=generated_secret_key
IDENTITY_HUB_REDIRECT_URI=http://new-app-ip:port/auth/callback
```

---

## 故障排查

### 常见问题速查表

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 容器无法启动 | 端口9000被占用 | `sudo ss -tuln \| grep 9000` |
| 健康检查失败 | 应用启动慢或缺少健康检查端点 | 查看日志，增加 `start_period` |
| OAuth登录失败 | 回调地址白名单未更新 | 更新数据库中的 `redirect_uris` |
| 飞书登录报错 | 飞书应用回调地址未更新 | 在飞书开放平台更新回调地址 |
| 数据库无法读写 | 权限问题或卷挂载错误 | 检查 `data/` 目录权限 |
| CORS错误 | ALLOWED_ORIGINS配置错误 | 检查并更新.env中的CORS配置 |

### 详细排查步骤

#### 1. 端口冲突

```bash
# 检查9000端口是否被占用
sudo ss -tuln | grep 9000

# 如果被占用，查看占用进程
sudo lsof -i :9000

# 停止占用进程或更换端口
```

**更换端口方案**:

```bash
# 修改docker-compose.yml
nano docker-compose.yml

# 修改端口映射（例如改为9001）
ports:
  - "9001:9000"

# 同时修改.env和客户端系统配置
```

#### 2. 数据库问题

```bash
# 检查数据库文件是否存在
docker exec identity-hub ls -la /app/data/

# 检查数据库文件权限
docker exec identity-hub stat /app/data/identity-hub.db

# 测试数据库连接
docker exec identity-hub sqlite3 /app/data/identity-hub.db "SELECT COUNT(*) FROM users;"
```

**权限修复**:

```bash
# 在宿主机上修复权限
cd ~/identity-hub
sudo chown -R 1000:1000 data/
chmod 755 data/
chmod 644 data/identity-hub.db

# 重启容器
docker-compose restart
```

#### 3. OAuth认证失败

**查看日志**:

```bash
# 查看Identity Hub日志
docker logs identity-hub --tail=100 | grep -i oauth

# 查看派工系统日志
ssh user@DISPATCH_SYSTEM_IP
cd ~/task_feishu/docker
docker logs docker_app_1 --tail=100 | grep -i oauth
```

**检查配置一致性**:

```bash
# 在Identity Hub服务器
docker exec identity-hub sqlite3 /app/data/identity-hub.db \
  "SELECT redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system';"

# 在派工系统服务器
grep IDENTITY_HUB_REDIRECT_URI .env

# 两者必须一致
```

#### 4. 飞书回调问题

**检查飞书配置**:

1. 访问飞书开放平台: https://open.feishu.cn/app
2. 找到Identity Hub使用的应用
3. 检查"重定向URL"是否包含: `http://192.168.1.200:9000/callback`
4. 如果不包含，添加并保存

**测试飞书连接**:

```bash
# 在Identity Hub容器中测试
docker exec identity-hub python3 -c "
import requests
import os
app_id = os.getenv('FEISHU_APP_ID')
app_secret = os.getenv('FEISHU_APP_SECRET')
r = requests.post(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    json={'app_id': app_id, 'app_secret': app_secret}
)
print(r.json())
"
```

#### 5. 网络连通性问题

```bash
# 从派工系统测试Identity Hub连通性
ssh user@DISPATCH_SYSTEM_IP
curl -I http://192.168.1.200:9000/health

# 从Identity Hub测试派工系统连通性
ssh user@IDENTITY_HUB_IP
curl -I http://192.168.1.100:8080/health

# 测试飞书API连通性
curl -I https://open.feishu.cn
```

### 日志分析

**关键日志关键词**:

```bash
# 查找所有ERROR
docker logs identity-hub 2>&1 | grep -i error

# 查找OAuth相关
docker logs identity-hub 2>&1 | grep -i oauth

# 查找飞书相关
docker logs identity-hub 2>&1 | grep -i feishu

# 查找数据库相关
docker logs identity-hub 2>&1 | grep -i database
```

### 完全重置

如果以上方法都无法解决：

```bash
cd ~/identity-hub

# 停止并删除容器
docker-compose down -v

# 删除镜像
docker rmi identity-hub_identity-hub

# 备份数据
cp -r data/ data.backup/

# 从头开始
docker-compose build --no-cache
docker-compose up -d
```

---

## 运维管理

### 日常维护

#### 1. 日志管理

```bash
# 查看实时日志
docker logs -f identity-hub

# 查看最近100行
docker logs identity-hub --tail=100

# 导出日志到文件
docker logs identity-hub > identity-hub-$(date +%Y%m%d).log

# 清理日志（重启容器会清空）
docker-compose restart
```

#### 2. 数据库备份

**自动备份脚本**:

```bash
cat > ~/backup-identity-hub.sh <<'EOF'
#!/bin/bash
# Identity Hub数据库备份脚本

BACKUP_DIR=~/identity-hub-backups
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库文件
docker cp identity-hub:/app/data/identity-hub.db \
  $BACKUP_DIR/identity-hub-$TIMESTAMP.db

# 压缩备份
gzip $BACKUP_DIR/identity-hub-$TIMESTAMP.db

# 保留最近30天的备份
find $BACKUP_DIR -name "identity-hub-*.db.gz" -mtime +30 -delete

echo "Backup completed: identity-hub-$TIMESTAMP.db.gz"
EOF

chmod +x ~/backup-identity-hub.sh
```

**设置定时备份**:

```bash
# 添加到crontab（每天凌晨2点备份）
crontab -e

# 添加以下行
0 2 * * * /home/user/backup-identity-hub.sh >> /home/user/backup.log 2>&1
```

#### 3. 监控和告警

**健康检查监控**:

```bash
cat > ~/monitor-identity-hub.sh <<'EOF'
#!/bin/bash
# Identity Hub健康监控

IDENTITY_HUB_URL="http://localhost:9000/health"
ALERT_EMAIL="admin@example.com"  # 替换为实际邮箱

# 检查健康状态
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $IDENTITY_HUB_URL)

if [ "$HTTP_CODE" != "200" ]; then
  echo "Identity Hub health check failed! HTTP code: $HTTP_CODE" | \
    mail -s "Identity Hub Alert" $ALERT_EMAIL
  exit 1
fi

echo "Identity Hub is healthy"
EOF

chmod +x ~/monitor-identity-hub.sh

# 添加到crontab（每5分钟检查一次）
crontab -e
# 添加: */5 * * * * /home/user/monitor-identity-hub.sh
```

#### 4. 性能监控

```bash
# 查看容器资源使用
docker stats identity-hub --no-stream

# 查看数据库大小
docker exec identity-hub du -sh /app/data/

# 查看OAuth token数量（定期清理过期token）
docker exec identity-hub sqlite3 /app/data/identity-hub.db \
  "SELECT COUNT(*) FROM oauth_tokens WHERE expires_at > datetime('now');"
```

### 扩展和优化

#### 1. 使用PostgreSQL（生产环境推荐）

**为什么切换？**
- SQLite适合开发和小规模部署
- PostgreSQL适合生产环境和并发访问

**迁移步骤**（简要）:

```bash
# 1. 安装PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=identity_hub \
  -p 5432:5432 \
  postgres:15-alpine

# 2. 修改.env
DATABASE_URL=postgresql://postgres:password@postgres:5432/identity_hub

# 3. 导出SQLite数据
# 4. 导入到PostgreSQL
# 5. 重启Identity Hub
```

#### 2. 添加HTTPS支持

```bash
# 使用Let's Encrypt获取免费SSL证书
sudo apt-get install certbot

# 生成证书
sudo certbot certonly --standalone -d identity-hub.example.com

# 配置Nginx反向代理（参考docker-compose.yml中的注释）
```

#### 3. 添加Redis缓存

```bash
# 在docker-compose.yml中添加Redis服务
# 缓存OAuth token和session
```

### 升级流程

```bash
# 1. 备份数据
~/backup-identity-hub.sh

# 2. 拉取新代码
cd ~/identity-hub
# 从源拷贝新版本文件

# 3. 重新构建镜像
docker-compose build --no-cache

# 4. 停止旧容器
docker-compose down

# 5. 启动新容器
docker-compose up -d

# 6. 验证
docker logs identity-hub
curl http://localhost:9000/health
```

---

## 附录

### A. 数据库Schema

**主要表结构**:

```sql
-- 用户表
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  user_id TEXT UNIQUE NOT NULL,
  username TEXT,
  email TEXT,
  feishu_user_id TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- OAuth客户端表
CREATE TABLE oauth_clients (
  id INTEGER PRIMARY KEY,
  client_id TEXT UNIQUE NOT NULL,
  client_name TEXT,
  client_secret TEXT,
  redirect_uris TEXT,  -- JSON数组
  scope TEXT,
  grant_types TEXT,    -- JSON数组
  created_at TIMESTAMP
);

-- OAuth令牌表
CREATE TABLE oauth_tokens (
  id INTEGER PRIMARY KEY,
  access_token TEXT UNIQUE NOT NULL,
  refresh_token TEXT,
  client_id TEXT,
  user_id TEXT,
  scope TEXT,
  expires_at TIMESTAMP,
  created_at TIMESTAMP
);
```

### B. OAuth端点说明

| 端点 | 方法 | 用途 | 示例 |
|------|------|------|------|
| `/oauth/authorize` | GET | 授权请求 | 用户登录授权 |
| `/oauth/token` | POST | 获取token | code换取access_token |
| `/oauth/userinfo` | GET | 获取用户信息 | 使用access_token |
| `/oauth/revoke` | POST | 撤销token | 登出 |
| `/login` | GET | 登录页面 | 显示飞书扫码 |
| `/callback` | GET | 飞书回调 | 接收飞书授权码 |

### C. 环境变量完整说明

```bash
# === 安全配置 ===
SECRET_KEY                # JWT签名密钥（必需，使用openssl rand -hex 32生成）

# === 飞书配置 ===
FEISHU_APP_ID             # 飞书应用ID（必需）
FEISHU_APP_SECRET         # 飞书应用密钥（必需）
FEISHU_REDIRECT_URI       # 飞书登录回调地址（必需，迁移时必改）

# === 数据库配置 ===
DATABASE_URL              # 数据库连接URL（默认SQLite）

# === 服务器配置 ===
HOST                      # 监听地址（默认0.0.0.0）
PORT                      # 监听端口（默认9000）

# === CORS配置 ===
ALLOWED_ORIGINS           # 允许跨域的来源（逗号分隔，迁移时必改）

# === 日志配置 ===
LOG_LEVEL                 # 日志级别（DEBUG/INFO/WARNING/ERROR）
```

### D. 快速命令参考

```bash
# === 容器管理 ===
docker-compose up -d              # 启动
docker-compose down               # 停止
docker-compose restart            # 重启
docker-compose logs -f            # 查看日志
docker-compose ps                 # 查看状态

# === 数据库操作 ===
docker exec -it identity-hub sqlite3 /app/data/identity-hub.db
# 进入SQLite命令行

# === 备份恢复 ===
docker cp identity-hub:/app/data/identity-hub.db ./backup.db  # 备份
docker cp ./backup.db identity-hub:/app/data/identity-hub.db  # 恢复

# === 健康检查 ===
curl http://localhost:9000/health                   # 本地检查
curl http://IDENTITY_HUB_IP:9000/health            # 远程检查
docker inspect identity-hub | grep -A 10 Health    # 容器健康状态
```

### E. 迁移完成检查清单

完成迁移后，请确认以下所有项目：

**Identity Hub服务器**:
- [ ] Docker容器状态为 `Up (healthy)`
- [ ] 可以从外部访问 `http://NEW_IP:9000/health`
- [ ] API文档可访问 `http://NEW_IP:9000/docs`
- [ ] 数据库数据完整（用户、OAuth客户端、部门等）
- [ ] 飞书回调地址已更新（.env和飞书开放平台）
- [ ] 日志无ERROR级别错误

**派工系统服务器**:
- [ ] `.env` 中的 `IDENTITY_HUB_URL` 已更新
- [ ] `.env` 中的 `IDENTITY_HUB_REDIRECT_URI` 已更新
- [ ] Docker容器已重启
- [ ] 环境变量正确加载

**Identity Hub数据库**:
- [ ] OAuth客户端 `redirect_uris` 已更新派工系统新地址
- [ ] 用户数据完整
- [ ] 角色权限配置正确

**完整功能测试**:
- [ ] 可以访问派工系统前端
- [ ] 点击登录跳转到新的Identity Hub
- [ ] 飞书扫码登录成功
- [ ] 登录后正确跳转回派工系统
- [ ] 显示用户信息和权限
- [ ] 可以访问受保护资源

**全部✅后，迁移完成！** 🎉

---

**文档版本**: v1.0
**最后更新**: 2025-11-04
**维护者**: Identity Hub Team

---

## 支持和反馈

如遇到问题，请按以下顺序排查：

1. **查看日志**: `docker logs identity-hub`
2. **检查配置**: 参考 [配置修改指南](#配置修改指南)
3. **故障排查**: 参考 [故障排查](#故障排查) 章节
4. **数据库检查**: 验证数据完整性
5. **网络测试**: 确认服务间可连通

如仍无法解决，请联系技术支持并提供：
- 错误日志
- 配置文件（脱敏后）
- 环境信息
- 复现步骤
