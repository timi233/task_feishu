# 飞书派工系统 Docker环境迁移手册

**版本**: v1.0
**日期**: 2025-11-04
**适用场景**: 将Docker环境从一台服务器迁移到另一台服务器

---

## 📋 目录

1. [迁移前准备](#迁移前准备)
2. [环境要求](#环境要求)
3. [迁移方式选择](#迁移方式选择)
4. [方式A: 完整源码迁移（推荐）](#方式a-完整源码迁移推荐)
5. [方式B: 镜像导出迁移（快速）](#方式b-镜像导出迁移快速)
6. [方式C: 轻量化迁移（高级）](#方式c-轻量化迁移高级)
7. [配置修改指南](#配置修改指南)
8. [启动和验证](#启动和验证)
9. [数据迁移](#数据迁移)
10. [故障排查](#故障排查)
11. [回滚方案](#回滚方案)

---

## 迁移前准备

### 📝 迁移前检查清单

在开始迁移前，请确认：

- [ ] 已在新服务器上安装Docker和Docker Compose
- [ ] 已获取新服务器的IP地址
- [ ] 已确认Identity Hub服务可从新服务器访问
- [ ] 已确认飞书API可从新服务器访问
- [ ] 已备份当前服务器的数据库文件（如需保留历史数据）
- [ ] 已记录当前环境的访问地址和端口

### 🔍 当前环境信息记录

在旧服务器上记录以下信息：

```bash
# 当前服务器IP地址
当前IP: 10.242.94.9

# 当前访问地址
前端访问: http://10.242.94.9:8080
Identity Hub: http://10.242.94.9:9000

# 当前数据库大小
ls -lh data/db/tasks.db
```

### 📦 新服务器信息准备

记录新服务器信息（后续需要替换配置）：

```
新服务器IP: ________________
前端访问地址: http://________:8080
Identity Hub地址: http://________:9000  (如果也迁移)
```

---

## 环境要求

### 最低系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Linux (Ubuntu 20.04+, CentOS 7+) | Ubuntu 22.04 LTS |
| CPU | 1核 | 2核+ |
| 内存 | 1GB | 2GB+ |
| 磁盘空间 | 5GB可用 | 10GB+可用 |
| Docker | 20.10+ | 最新稳定版 |
| Docker Compose | 1.29+ | 2.x |

### 软件版本检查

在新服务器上运行以下命令检查环境：

```bash
# 检查Docker版本
docker --version
# 预期输出: Docker version 20.10.x 或更高

# 检查Docker Compose版本
docker-compose --version
# 预期输出: docker-compose version 1.29.x 或更高

# 检查Docker服务状态
sudo systemctl status docker
# 预期输出: active (running)

# 检查磁盘空间
df -h
# 确保至少有5GB可用空间
```

### 如果未安装Docker

**Ubuntu/Debian系统**:
```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 将当前用户添加到docker组（避免每次sudo）
sudo usermod -aG docker $USER
newgrp docker

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker
```

### 网络要求

**端口检查**:
```bash
# 检查8080端口是否被占用
sudo ss -tuln | grep 8080
# 如果有输出，说明端口被占用，需要更换端口或停止占用进程

# 检查端口是否可以监听（预检）
nc -l 8080 &
netstat -tuln | grep 8080
kill %1  # 停止测试
```

**外部服务连通性检查**:
```bash
# 检查是否能访问飞书API
curl -I https://open.feishu.cn

# 检查是否能访问Identity Hub（替换为实际地址）
curl -I http://IDENTITY_HUB_IP:9000

# 如果Identity Hub也部署在新服务器，需要先部署Identity Hub
```

---

## 迁移方式选择

根据你的场景选择合适的迁移方式：

| 迁移方式 | 传输大小 | 迁移时间 | 适用场景 | 难度 |
|---------|---------|---------|---------|------|
| **方式A: 完整源码迁移** | ~3.5MB | 15-20分钟 | 生产环境、需要审查代码 | ⭐⭐ 简单 |
| **方式B: 镜像导出迁移** | ~500MB | 10-15分钟 | 离线部署、快速迁移 | ⭐ 最简单 |
| **方式C: 轻量化迁移** | ~2MB | 20-30分钟 | 带宽受限、多次部署 | ⭐⭐⭐ 复杂 |

**推荐选择**:
- 🥇 **首次迁移**: 使用方式A（完整源码迁移）
- 🥈 **快速部署**: 使用方式B（镜像导出迁移）
- 🥉 **高级用户**: 使用方式C（轻量化迁移）

---

## 方式A: 完整源码迁移（推荐）

这是**最推荐的迁移方式**，包含所有源码，便于后续维护和二次开发。

### 步骤1: 在旧服务器打包文件

```bash
# 进入项目目录
cd /home/jian/code/Task_feishu

# 创建迁移包（排除不必要的文件）
tar -czf ~/task_feishu_docker_migration.tar.gz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='frontend/node_modules' \
  --exclude='frontend/src' \
  --exclude='frontend/public' \
  --exclude='frontend/package*.json' \
  --exclude='data/db/tasks.db' \
  docker/ \
  backend/ \
  frontend/build/ \
  scripts/ \
  .env

# 如果需要迁移历史数据，单独打包数据库
tar -czf ~/task_feishu_data.tar.gz data/db/

# 检查打包文件大小
ls -lh ~/task_feishu_docker_migration.tar.gz
# 预期大小: 约2-4MB
```

**打包文件说明**:
- `task_feishu_docker_migration.tar.gz`: 主程序包（必需）
- `task_feishu_data.tar.gz`: 数据库包（可选，仅在需要保留历史数据时使用）

### 步骤2: 传输文件到新服务器

**方式1: 使用scp（服务器间直传）**
```bash
# 在旧服务器上执行
scp ~/task_feishu_docker_migration.tar.gz user@NEW_SERVER_IP:/tmp/
scp ~/task_feishu_data.tar.gz user@NEW_SERVER_IP:/tmp/  # 可选
```

**方式2: 通过中转（如个人电脑）**
```bash
# 1. 从旧服务器下载到本地
scp user@OLD_SERVER_IP:~/task_feishu_docker_migration.tar.gz ~/Downloads/

# 2. 从本地上传到新服务器
scp ~/Downloads/task_feishu_docker_migration.tar.gz user@NEW_SERVER_IP:/tmp/
```

**方式3: 使用rsync（增量传输，适合多次迁移）**
```bash
# 在旧服务器上执行
rsync -avz --progress ~/task_feishu_docker_migration.tar.gz user@NEW_SERVER_IP:/tmp/
```

### 步骤3: 在新服务器解压文件

```bash
# SSH登录到新服务器
ssh user@NEW_SERVER_IP

# 创建项目目录
mkdir -p ~/task_feishu
cd ~/task_feishu

# 解压主程序包
tar -xzf /tmp/task_feishu_docker_migration.tar.gz

# 解压数据包（可选）
tar -xzf /tmp/task_feishu_data.tar.gz

# 检查目录结构
tree -L 2 -d .
# 预期输出:
# .
# ├── backend
# ├── docker
# │   └── nginx
# ├── frontend
# │   └── build
# ├── scripts
# └── data (如果解压了数据包)
#     └── db
```

### 步骤4: 修改配置文件

**必须修改的配置** (详见[配置修改指南](#配置修改指南)):

1. 编辑 `.env` 文件：
```bash
cd ~/task_feishu
nano .env

# 修改以下配置项（将10.242.94.9替换为新服务器IP）
IDENTITY_HUB_URL=http://NEW_SERVER_IP:9000
IDENTITY_HUB_REDIRECT_URI=http://NEW_SERVER_IP:8080/auth/callback
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,http://NEW_SERVER_IP:8080
```

2. 编辑 `docker/docker-compose.yml`：
```bash
nano docker/docker-compose.yml

# 修改FRONTEND_URL（第18行）
environment:
  - BACKEND_PORT=8000
  - FRONTEND_URL=http://NEW_SERVER_IP:8080
```

### 步骤5: 构建并启动Docker容器

```bash
# 进入docker目录
cd ~/task_feishu/docker

# 构建Docker镜像（首次需要3-5分钟）
docker-compose build --no-cache

# 启动容器
docker-compose up -d

# 查看容器状态
docker-compose ps
# 预期输出:
#      Name                    Command               State           Ports
# ---------------------------------------------------------------------------------
# docker_app_1        /app/start.sh                Up      8000/tcp
# docker_frontend_1   nginx -g daemon off;         Up      0.0.0.0:8080->80/tcp
```

### 步骤6: 验证服务

跳转到 [启动和验证](#启动和验证) 章节。

---

## 方式B: 镜像导出迁移（快速）

这种方式最快速，但传输文件较大（约500MB）。适合**快速迁移**或**离线部署**。

### 步骤1: 在旧服务器导出Docker镜像

```bash
# 查看当前镜像
docker images | grep docker_

# 导出后端镜像
docker save docker_app:latest -o ~/docker_app.tar

# 导出前端镜像
docker save docker_frontend:latest -o ~/docker_frontend.tar

# 打包配置文件和数据（可选）
tar -czf ~/docker_config.tar.gz .env docker/docker-compose.yml

# 打包数据库（可选）
tar -czf ~/docker_data.tar.gz data/db/

# 检查文件大小
ls -lh ~/*.tar ~/*.tar.gz
# docker_app.tar: 约300MB
# docker_frontend.tar: 约50MB
# docker_config.tar.gz: 约1KB
```

### 步骤2: 传输文件到新服务器

```bash
# 使用scp传输（可能需要较长时间）
scp ~/docker_app.tar user@NEW_SERVER_IP:/tmp/
scp ~/docker_frontend.tar user@NEW_SERVER_IP:/tmp/
scp ~/docker_config.tar.gz user@NEW_SERVER_IP:/tmp/
scp ~/docker_data.tar.gz user@NEW_SERVER_IP:/tmp/  # 可选

# 或者使用rsync显示进度
rsync -avz --progress ~/docker_*.tar ~/docker_*.tar.gz user@NEW_SERVER_IP:/tmp/
```

### 步骤3: 在新服务器导入镜像

```bash
# SSH登录到新服务器
ssh user@NEW_SERVER_IP

# 导入Docker镜像
docker load -i /tmp/docker_app.tar
docker load -i /tmp/docker_frontend.tar

# 验证镜像导入成功
docker images | grep docker_
# 预期输出:
# docker_app         latest    ...   300MB
# docker_frontend    latest    ...   50MB

# 创建项目目录并解压配置
mkdir -p ~/task_feishu
cd ~/task_feishu
tar -xzf /tmp/docker_config.tar.gz

# 解压数据（可选）
tar -xzf /tmp/docker_data.tar.gz
```

### 步骤4: 修改配置文件

参考 [配置修改指南](#配置修改指南)，修改 `.env` 和 `docker-compose.yml`。

### 步骤5: 启动容器

```bash
cd ~/task_feishu/docker
docker-compose up -d
```

### 步骤6: 验证服务

跳转到 [启动和验证](#启动和验证) 章节。

---

## 方式C: 轻量化迁移（高级）

这种方式传输文件最小，但需要在新服务器上重新构建前端。适合**带宽受限**或**多次部署**场景。

### 步骤1: 准备最小文件包

```bash
# 在旧服务器上仅打包源码（不包含前端构建产物）
cd /home/jian/code/Task_feishu

tar -czf ~/task_feishu_minimal.tar.gz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='frontend/build' \
  --exclude='frontend/node_modules' \
  --exclude='data' \
  docker/ \
  backend/ \
  frontend/src/ \
  frontend/public/ \
  frontend/package.json \
  frontend/package-lock.json \
  scripts/ \
  .env

# 检查大小（约1-2MB）
ls -lh ~/task_feishu_minimal.tar.gz
```

### 步骤2: 传输并解压

```bash
# 传输
scp ~/task_feishu_minimal.tar.gz user@NEW_SERVER_IP:/tmp/

# 在新服务器解压
ssh user@NEW_SERVER_IP
mkdir -p ~/task_feishu
cd ~/task_feishu
tar -xzf /tmp/task_feishu_minimal.tar.gz
```

### 步骤3: 在新服务器构建前端

```bash
# 安装Node.js（如果未安装）
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 构建前端
cd ~/task_feishu/frontend
npm install
npm run build

# 验证构建产物
ls -lh build/
```

### 步骤4-6: 修改配置、启动、验证

与方式A相同，参考对应章节。

---

## 配置修改指南

这是**最关键的步骤**，配置错误会导致服务无法启动或OAuth认证失败。

### 配置修改清单

假设：
- 旧服务器IP: `10.242.94.9`
- 新服务器IP: `192.168.1.100` （示例，请替换为实际IP）

| 配置项 | 文件位置 | 旧值 | 新值 |
|--------|---------|------|------|
| Identity Hub URL | `.env` | `http://10.242.94.9:9000` | `http://192.168.1.100:9000` |
| OAuth回调地址 | `.env` | `http://10.242.94.9:8080/auth/callback` | `http://192.168.1.100:8080/auth/callback` |
| CORS来源 | `.env` | `...10.242.94.9:8080...` | `...192.168.1.100:8080...` |
| 前端URL | `docker-compose.yml` | `http://10.242.94.9:8080` | `http://192.168.1.100:8080` |

### 详细修改步骤

#### 1. 修改 `.env` 文件

```bash
cd ~/task_feishu
nano .env
```

**需要修改的行**:

```bash
# 第24行 - Identity Hub地址
IDENTITY_HUB_URL=http://192.168.1.100:9000

# 第27行 - OAuth回调地址
IDENTITY_HUB_REDIRECT_URI=http://192.168.1.100:8080/auth/callback

# 第21行 - CORS配置（添加新IP，保留localhost用于开发）
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,http://192.168.1.100:8080
```

**快速替换命令** (使用sed):
```bash
# 替换所有10.242.94.9为新IP
sed -i 's/10.242.94.9/192.168.1.100/g' .env

# 验证修改
grep "192.168.1.100" .env
```

#### 2. 修改 `docker/docker-compose.yml`

```bash
nano docker/docker-compose.yml
```

**需要修改的行** (第18行):

```yaml
environment:
  - BACKEND_PORT=8000
  - FRONTEND_URL=http://192.168.1.100:8080  # ← 修改这里
```

**快速替换命令**:
```bash
sed -i 's/10.242.94.9/192.168.1.100/g' docker/docker-compose.yml

# 验证修改
grep "FRONTEND_URL" docker/docker-compose.yml
```

#### 3. 修改端口（可选）

如果需要使用不同端口（例如改为80端口）：

**修改 `docker/docker-compose.yml`**:
```yaml
frontend:
  ports:
    - "80:80"  # 改为80端口（需要root权限）
```

**同时修改以下配置**:
- `.env` 中的 `IDENTITY_HUB_REDIRECT_URI`: `http://192.168.1.100:80/auth/callback`
- `.env` 中的 `ALLOWED_ORIGINS`: `http://192.168.1.100:80`
- `docker-compose.yml` 中的 `FRONTEND_URL`: `http://192.168.1.100:80`

### ⚠️ 重要: 同步Identity Hub OAuth白名单

**问题**: 即使修改了上述配置，OAuth登录仍会失败，因为Identity Hub的OAuth应用白名单中没有新服务器的回调地址。

**解决方案**: 需要在Identity Hub服务器上修改OAuth应用的回调地址白名单。

#### 方式1: 通过SQLite直接修改（推荐）

如果你能访问Identity Hub服务器：

```bash
# SSH登录到Identity Hub服务器
ssh user@IDENTITY_HUB_SERVER

# 备份数据库
cp /path/to/identity-hub/data/identity-hub.db /path/to/identity-hub/data/identity-hub.db.backup

# 修改OAuth白名单
sqlite3 /path/to/identity-hub/data/identity-hub.db

-- 查看当前配置
SELECT client_id, redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system';

-- 更新白名单（添加新服务器地址）
UPDATE oauth_clients
SET redirect_uris='["http://192.168.1.100:8080/auth/callback", "http://localhost:8080/auth/callback", "http://192.168.1.100:3000/auth/callback", "http://localhost:3000/auth/callback"]'
WHERE client_id='task_feishu_dispatch_system';

-- 验证修改
SELECT redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system';

-- 退出
.exit
```

#### 方式2: 通过Identity Hub管理界面（如果有）

如果Identity Hub提供了管理界面，可通过界面修改OAuth应用配置。

#### 方式3: 重新创建OAuth应用

如果无法修改，可以在Identity Hub中创建新的OAuth应用，并更新 `.env` 中的 `IDENTITY_HUB_CLIENT_ID` 和 `IDENTITY_HUB_CLIENT_SECRET`。

### 配置验证

修改完成后，验证配置是否正确：

```bash
# 检查.env文件中的IP地址
grep -E "IDENTITY_HUB|ALLOWED_ORIGINS|REDIRECT" .env

# 检查docker-compose.yml中的FRONTEND_URL
grep "FRONTEND_URL" docker/docker-compose.yml

# 确保没有遗漏旧IP
grep -r "10.242.94.9" .env docker/docker-compose.yml
# 如果有输出，说明还有遗漏的配置
```

---

## 启动和验证

### 启动Docker容器

```bash
# 进入docker目录
cd ~/task_feishu/docker

# 启动容器（后台运行）
docker-compose up -d

# 查看容器状态
docker-compose ps
```

**预期输出**:
```
      Name                    Command               State           Ports
---------------------------------------------------------------------------------
docker_app_1        /app/start.sh                Up      8000/tcp
docker_frontend_1   nginx -g daemon off;         Up      0.0.0.0:8080->80/tcp
```

**状态说明**:
- `State: Up` - 容器正在运行 ✅
- `State: Up (healthy)` - 容器健康检查通过 ✅
- `State: Restarting` - 容器反复重启 ❌ 查看日志排查问题

### 查看容器日志

```bash
# 查看后端日志
docker-compose logs -f app

# 查看前端日志
docker-compose logs -f frontend

# 查看所有日志
docker-compose logs -f

# 查看最近50行日志
docker-compose logs --tail=50 app
```

**健康的日志输出**:

**后端日志**:
```
Starting application setup...
Running data sync at Mon Nov  4 12:00:00 CST 2025
[SYNC] Starting one-time data synchronization...
[SUCCESS] Successfully obtained tenant_access_token
[SUCCESS] Finished fetching all records. Total: 210
[SYNC] One-time data synchronization completed successfully.
Starting backend service...
INFO:     Started server process [1]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**前端日志**:
```
(Nginx日志通常较少，无错误即正常)
```

### 健康检查

#### 1. 容器健康检查

```bash
# 查看容器详细状态
docker inspect docker_app_1 | grep -A 5 Health

# 手动触发健康检查
docker exec docker_app_1 python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"
```

#### 2. 网络连通性检查

```bash
# 从宿主机访问后端（通过Nginx代理）
curl http://localhost:8080/health

# 从宿主机访问前端
curl -I http://localhost:8080

# 从外部访问（替换为新服务器IP）
curl http://192.168.1.100:8080
```

**预期输出**:
```html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"/>...
```

#### 3. 浏览器访问测试

打开浏览器访问: `http://192.168.1.100:8080`

**验证清单**:

- [ ] 页面正常加载，显示"派工管理系统"标题
- [ ] 显示"登录"按钮
- [ ] 显示周视图（周一到周五）
- [ ] 点击"登录"按钮跳转到Identity Hub
- [ ] OAuth授权后正确跳转回8080端口（不是3000）
- [ ] 登录成功后显示用户名
- [ ] 任务数据正常加载（如果有数据）

### 功能验证清单

#### 基础功能

```bash
# 1. 健康检查端点
curl http://192.168.1.100:8080/health
# 预期: 返回HTML页面

# 2. 认证状态检查
curl http://192.168.1.100:8080/auth/status
# 预期: {"authenticated":false,"user_name":null,...}

# 3. 任务列表API
curl http://192.168.1.100:8080/api/tasks
# 预期: 返回JSON数据
```

#### OAuth登录流程（手动测试）

1. **访问前端**: `http://192.168.1.100:8080`
2. **点击登录按钮**: 应跳转到 `http://IDENTITY_HUB_IP:9000/login?next=...`
3. **查看URL参数**:
   - `redirect_uri` 应为 `http://192.168.1.100:8080/auth/callback`
   - 如果是 `http://10.242.94.9:...` 说明配置未正确修改
4. **使用飞书扫码登录**
5. **登录成功后**: 应自动跳转回 `http://192.168.1.100:8080/`
6. **验证登录状态**: 页面右上角应显示用户名

#### 数据同步测试

```bash
# 查看同步日志
docker logs docker_app_1 | grep SYNC

# 预期输出:
# [SYNC] Starting one-time data synchronization...
# [SYNC] One-time data synchronization completed successfully.

# 手动触发同步（API调用）
curl -X POST http://192.168.1.100:8080/api/sync

# 查看数据库是否有数据
docker exec docker_app_1 ls -lh /app/db/
```

### 性能检查

```bash
# 容器资源使用
docker stats docker_app_1 docker_frontend_1 --no-stream

# 预期输出:
# CONTAINER      CPU %     MEM USAGE / LIMIT     MEM %
# docker_app_1    1-5%     100-200MB / 1GB       10-20%
# docker_frontend_1  0-1%   10-20MB / 1GB        1-2%
```

### 常见启动问题

#### 问题1: 容器反复重启

```bash
# 查看详细日志
docker-compose logs --tail=100 app

# 常见原因:
# - 环境变量配置错误（飞书凭证）
# - 端口被占用
# - 数据库权限问题
```

**解决方案**:
```bash
# 检查环境变量是否正确加载
docker exec docker_app_1 printenv | grep FEISHU

# 检查端口占用
sudo ss -tuln | grep 8080
```

#### 问题2: 前端容器无法启动

```bash
# 查看错误信息
docker logs docker_frontend_1

# 常见原因:
# - 前端构建产物缺失
# - Nginx配置错误
```

**解决方案**:
```bash
# 检查前端构建产物是否存在
ls -la frontend/build/

# 如果缺失，重新构建前端
cd frontend
npm run build
```

#### 问题3: OAuth登录失败

**现象**: 点击登录后跳转到Identity Hub，授权后返回错误页面

**排查步骤**:
```bash
# 1. 检查OAuth回调地址配置
grep REDIRECT .env
docker exec docker_app_1 printenv | grep REDIRECT

# 2. 检查前端URL配置
grep FRONTEND_URL docker/docker-compose.yml

# 3. 查看后端日志中的OAuth相关错误
docker logs docker_app_1 | grep -i oauth
```

**解决方案**: 参考 [配置修改指南](#配置修改指南) 检查所有IP地址配置。

---

## 数据迁移

如果需要保留旧服务器的历史数据，按以下步骤操作。

### 步骤1: 备份旧服务器数据

```bash
# 在旧服务器上
cd /home/jian/code/Task_feishu

# 停止Docker容器（确保数据一致性）
cd docker
docker-compose down

# 备份数据库
tar -czf ~/task_feishu_data_backup_$(date +%Y%m%d).tar.gz data/db/

# 重新启动容器
docker-compose up -d

# 传输数据到新服务器
scp ~/task_feishu_data_backup_*.tar.gz user@NEW_SERVER_IP:/tmp/
```

### 步骤2: 在新服务器恢复数据

```bash
# SSH登录到新服务器
ssh user@NEW_SERVER_IP

# 停止新服务器的Docker容器
cd ~/task_feishu/docker
docker-compose down

# 备份新服务器当前数据（如果有）
tar -czf ~/new_server_data_backup.tar.gz ../data/db/

# 删除新数据并恢复旧数据
rm -rf ../data/db/*
tar -xzf /tmp/task_feishu_data_backup_*.tar.gz -C ../

# 检查数据文件权限
ls -la ../data/db/
# 确保tasks.db文件存在且可读

# 重新启动容器
docker-compose up -d

# 验证数据恢复
docker logs docker_app_1 | grep "Successfully loaded"
```

### 步骤3: 验证数据完整性

```bash
# 检查数据库文件大小
docker exec docker_app_1 ls -lh /app/db/tasks.db

# 查看数据库中的记录数
docker exec docker_app_1 python3 -c "
import sqlite3
conn = sqlite3.connect('/app/db/tasks.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM tasks')
print('Total tasks:', cursor.fetchone()[0])
conn.close()
"

# 通过API查看任务数据
curl http://192.168.1.100:8080/api/tasks | jq '.data | length'
```

### SQLite数据库直接操作（高级）

如果需要手动检查或修复数据库：

```bash
# 进入容器
docker exec -it docker_app_1 bash

# 使用SQLite CLI
apt-get update && apt-get install -y sqlite3
sqlite3 /app/db/tasks.db

-- 查看所有表
.tables

-- 查看tasks表结构
.schema tasks

-- 查询最近10条记录
SELECT record_id, customer_name, date FROM tasks ORDER BY date DESC LIMIT 10;

-- 统计总记录数
SELECT COUNT(*) FROM tasks;

-- 退出
.exit
```

---

## 故障排查

### 常见问题速查表

| 问题现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| 容器无法启动 | 端口被占用 | `sudo ss -tuln \| grep 8080` 检查端口 |
| 无法访问前端 | 防火墙阻止 | `sudo ufw allow 8080` 或检查云服务器安全组 |
| OAuth登录失败 | 回调地址未更新 | 检查Identity Hub白名单配置 |
| 数据为空 | 飞书API凭证错误 | 检查 `.env` 中的飞书配置 |
| 登录后跳转3000端口 | FRONTEND_URL未配置 | 检查 `docker-compose.yml` |
| 502 Bad Gateway | 后端容器未启动 | `docker logs docker_app_1` 查看错误 |

### 详细排查步骤

#### 1. 端口冲突

**检查**:
```bash
sudo ss -tuln | grep 8080
```

**解决**:
```bash
# 方案1: 停止占用进程
sudo lsof -i :8080
sudo kill -9 <PID>

# 方案2: 修改Docker端口
# 编辑 docker/docker-compose.yml
frontend:
  ports:
    - "8888:80"  # 改用8888端口
```

#### 2. 防火墙问题

**检查**:
```bash
# Ubuntu/Debian
sudo ufw status

# CentOS/RHEL
sudo firewall-cmd --list-ports
```

**解决**:
```bash
# Ubuntu/Debian
sudo ufw allow 8080/tcp
sudo ufw reload

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload

# 云服务器（AWS/阿里云/腾讯云）
# 需要在控制台的安全组中添加8080端口入站规则
```

#### 3. DNS/网络问题

**检查**:
```bash
# 从容器内访问外部服务
docker exec docker_app_1 ping -c 3 open.feishu.cn
docker exec docker_app_1 curl -I https://open.feishu.cn
```

**解决**:
```bash
# 检查DNS配置
cat /etc/resolv.conf

# 添加公共DNS（Google/阿里云）
echo "nameserver 8.8.8.8" | sudo tee -a /etc/resolv.conf
```

#### 4. 日志分析

**查找错误关键词**:
```bash
# 查找所有ERROR日志
docker logs docker_app_1 2>&1 | grep -i error

# 查找身份认证相关错误
docker logs docker_app_1 2>&1 | grep -i "auth\|oauth\|identity"

# 查找飞书API相关错误
docker logs docker_app_1 2>&1 | grep -i "feishu\|tenant_access_token"
```

#### 5. 环境变量检查

```bash
# 检查容器内的环境变量
docker exec docker_app_1 printenv | sort

# 检查关键配置
docker exec docker_app_1 printenv | grep -E "FEISHU|IDENTITY_HUB|FRONTEND_URL|BACKEND_PORT"

# 如果环境变量缺失，检查.env文件和docker-compose.yml
cat .env
cat docker/docker-compose.yml
```

### 完全重置（最后手段）

如果以上方法都无法解决，可以完全重置环境：

```bash
# 停止并删除所有容器
cd ~/task_feishu/docker
docker-compose down -v

# 删除所有相关镜像
docker rmi docker_app docker_frontend

# 清理Docker缓存
docker system prune -a

# 重新开始迁移流程
# 从 方式A步骤3 开始
```

---

## 回滚方案

如果新服务器部署失败，可以快速回滚到旧服务器。

### 情况1: 新服务器无法启动

**操作**: 直接继续使用旧服务器，无需回滚。

### 情况2: 已将流量切换到新服务器

如果已修改DNS或负载均衡指向新服务器，但新服务器出现问题：

#### 快速回滚步骤

1. **切换流量回旧服务器**
```bash
# 方法1: 修改DNS
# 将域名解析改回旧服务器IP

# 方法2: 修改负载均衡
# 在负载均衡器中移除新服务器，保留旧服务器

# 方法3: 通知用户
# 发送通知，告知用户临时使用旧地址
```

2. **验证旧服务器状态**
```bash
# SSH登录到旧服务器
ssh user@OLD_SERVER_IP

# 检查容器状态
cd ~/task_feishu/docker
docker-compose ps

# 如果容器未运行，启动容器
docker-compose up -d

# 验证服务可用
curl http://OLD_SERVER_IP:8080
```

3. **分析新服务器问题**

在旧服务器稳定运行的情况下，有充足时间排查新服务器问题。

### 情况3: 数据已迁移到新服务器

如果已将数据库迁移到新服务器，需要恢复数据：

```bash
# 在新服务器上重新备份数据
ssh user@NEW_SERVER_IP
cd ~/task_feishu
tar -czf ~/new_server_data_final.tar.gz data/db/

# 传输回旧服务器
scp ~/new_server_data_final.tar.gz user@OLD_SERVER_IP:/tmp/

# 在旧服务器上恢复数据
ssh user@OLD_SERVER_IP
cd ~/task_feishu/docker
docker-compose down
tar -xzf /tmp/new_server_data_final.tar.gz -C ../
docker-compose up -d
```

### 回滚后检查清单

- [ ] 旧服务器Docker容器正常运行
- [ ] 旧服务器可以通过浏览器访问
- [ ] OAuth登录功能正常
- [ ] 数据完整无丢失
- [ ] 用户可以正常使用系统

---

## 附录

### A. 完整文件清单

**必需文件**（约3.5MB）:
```
task_feishu/
├── .env                          # 环境变量配置 (1KB)
├── docker/
│   ├── docker-compose.yml        # Docker编排文件 (2KB)
│   ├── Dockerfile                # 后端镜像构建文件 (2KB)
│   └── nginx/
│       ├── Dockerfile.frontend   # 前端镜像构建文件 (1KB)
│       └── nginx.frontend.conf   # Nginx配置 (2KB)
├── backend/                      # 后端Python代码 (1.8MB)
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── routers/
│   ├── auth*.py
│   └── ...
├── frontend/build/               # 前端构建产物 (908KB)
│   ├── index.html
│   ├── static/
│   │   ├── js/
│   │   └── css/
│   └── ...
└── scripts/
    └── start.sh                  # 启动脚本 (1KB)
```

**可选文件**:
```
task_feishu/
└── data/db/
    └── tasks.db                  # SQLite数据库 (356KB)
```

### B. 端口说明

| 端口 | 服务 | 说明 | 是否必需 |
|------|------|------|---------|
| 8080 | 前端Nginx | 主要访问端口 | ✅ 必需 |
| 8000 | 后端FastAPI | 容器内部端口，不直接暴露 | ✅ 必需 |
| 9000 | Identity Hub | OAuth认证服务（外部依赖） | ✅ 必需 |

### C. 环境变量完整说明

`.env` 文件中的所有环境变量：

```bash
# === 飞书多维表格配置 ===
FEISHU_APP_ID           # 飞书应用ID
FEISHU_APP_SECRET       # 飞书应用密钥
FEISHU_APP_TOKEN        # 多维表格App Token
FEISHU_TABLE_ID         # 表格ID

# === 飞书审批配置 ===
FEISHU_APPROVAL_CODE            # 公司日常工单审批Code
FEISHU_APPROVAL_CODE_EISOO      # 爱数原厂派单审批Code

# === API认证配置 ===
API_KEYS                # 管理员API密钥（逗号分隔）
READONLY_API_KEYS       # 只读API密钥（逗号分隔）
API_RATE_LIMIT          # API限流（次/分钟）

# === CORS配置 ===
ALLOWED_ORIGINS         # 允许跨域的来源（逗号分隔）
                        # ⚠️ 迁移时需要添加新服务器IP

# === Identity Hub OAuth配置 ===
IDENTITY_HUB_URL                # Identity Hub地址
                                # ⚠️ 迁移时需要修改
IDENTITY_HUB_CLIENT_ID          # OAuth客户端ID
IDENTITY_HUB_CLIENT_SECRET      # OAuth客户端密钥
IDENTITY_HUB_REDIRECT_URI       # OAuth回调地址
                                # ⚠️ 迁移时需要修改
```

### D. Docker命令速查

```bash
# === 容器管理 ===
docker-compose up -d              # 启动容器（后台）
docker-compose down               # 停止并删除容器
docker-compose restart            # 重启容器
docker-compose ps                 # 查看容器状态
docker-compose logs -f app        # 查看实时日志

# === 镜像管理 ===
docker images                     # 查看所有镜像
docker rmi <image_id>            # 删除镜像
docker-compose build --no-cache  # 重新构建镜像（不使用缓存）

# === 容器操作 ===
docker exec -it docker_app_1 bash         # 进入容器
docker exec docker_app_1 <command>        # 在容器中执行命令
docker cp <file> docker_app_1:/app/       # 复制文件到容器

# === 清理 ===
docker system prune -a            # 清理所有未使用的资源
docker volume prune               # 清理未使用的卷
```

### E. 快速参考

**新服务器快速启动流程**（已完成迁移和配置修改）:

```bash
# 1. 解压文件
cd ~ && mkdir task_feishu && cd task_feishu
tar -xzf /path/to/task_feishu_docker_migration.tar.gz

# 2. 修改配置（使用sed快速替换）
sed -i 's/OLD_SERVER_IP/NEW_SERVER_IP/g' .env docker/docker-compose.yml

# 3. 启动服务
cd docker && docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 验证服务
curl http://NEW_SERVER_IP:8080
```

**完整健康检查命令**:

```bash
# 一键检查脚本
cat > ~/check_service.sh <<'EOF'
#!/bin/bash
echo "=== 容器状态 ==="
docker-compose ps

echo -e "\n=== 后端健康检查 ==="
curl -s http://localhost:8080/health | head -c 100

echo -e "\n\n=== 认证状态 ==="
curl -s http://localhost:8080/auth/status | jq '.'

echo -e "\n=== 环境变量检查 ==="
docker exec docker_app_1 printenv | grep -E "FRONTEND_URL|BACKEND_PORT"

echo -e "\n=== 数据库文件 ==="
docker exec docker_app_1 ls -lh /app/db/

echo -e "\n=== 容器资源使用 ==="
docker stats --no-stream docker_app_1 docker_frontend_1
EOF

chmod +x ~/check_service.sh
~/check_service.sh
```

---

## 联系和支持

如果在迁移过程中遇到问题：

1. **查看日志**: `docker-compose logs -f app`
2. **检查配置**: 按照 [配置修改指南](#配置修改指南) 检查所有配置项
3. **参考文档**:
   - [Docker迁移验证报告](DOCKER_MIGRATION_VERIFICATION_2025-11-04.md)
   - [OAuth回调地址修复](OAUTH_FIX_2025-11-04.md)
   - [端口架构说明](PORT_ARCHITECTURE_EXPLANATION.md)
   - [前端URL修复记录](FRONTEND_URL_FIX_2025-11-04.md)

---

**文档版本**: v1.0
**最后更新**: 2025-11-04
**适用系统版本**: Docker环境 (2025-11-04)

---

## ✅ 迁移完成检查清单

迁移完成后，请确认以下所有项目：

- [ ] Docker容器状态为 `Up (healthy)`
- [ ] 可以通过浏览器访问前端 `http://NEW_SERVER_IP:8080`
- [ ] 点击登录按钮跳转到Identity Hub
- [ ] OAuth登录成功后跳转回8080端口（非3000）
- [ ] 登录后显示用户信息
- [ ] 任务数据正常加载
- [ ] 数据同步功能正常（如查看日志）
- [ ] 性能正常（容器CPU/内存使用率合理）
- [ ] 所有配置中的旧IP已替换为新IP
- [ ] Identity Hub OAuth白名单已更新

**全部✅后，迁移完成！** 🎉
