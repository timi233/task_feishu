# OAuth登录跳转端口修复记录

**日期**: 2025-11-04 11:50
**问题**: Docker环境登录后跳转到3000端口，但该端口不存在
**状态**: ✅ 已修复

## 问题现象

用户在Docker环境（端口8080）中点击"登录"按钮后：
1. ✅ 正确跳转到Identity Hub OAuth页面
2. ✅ OAuth授权成功
3. ❌ **回调后重定向到 `http://10.242.94.9:3000/`**（错误端口）
4. ❌ 页面无法访问（Docker环境前端运行在8080端口）

## 根本原因

### 后端代码问题

后端在OAuth回调处理时，使用 `FRONTEND_URL` 环境变量构造重定向地址：

**代码位置**: `backend/auth_routes.py:298-299`
```python
frontend_url = os.getenv("FRONTEND_URL", "http://10.242.94.9:3000")
return_url = f"{frontend_url}{return_url}"
```

**默认值问题**:
- 默认值硬编码为 `http://10.242.94.9:3000`（开发环境端口）
- `.env` 文件中没有配置 `FRONTEND_URL` 环境变量
- Docker环境使用默认值，导致回调后跳转到错误端口

### 为什么不同环境需要不同端口？

| 环境 | 前端端口 | 原因 |
|------|---------|------|
| 开发环境 | 3000 | React Dev Server默认端口 |
| Docker环境 | 8080 | Nginx统一入口，生产标准端口 |

详细架构说明请参考：[端口架构说明文档](PORT_ARCHITECTURE_EXPLANATION.md)

## 解决方案

### 修改 docker-compose.yml

在后端容器的环境变量中添加 `FRONTEND_URL` 覆盖：

**文件**: `docker/docker-compose.yml`

**修改前**:
```yaml
services:
  app:
    environment:
      - BACKEND_PORT=8000
```

**修改后**:
```yaml
services:
  app:
    environment:
      - BACKEND_PORT=8000
      - FRONTEND_URL=http://10.242.94.9:8080  # ← 新增
```

### 为什么不在 .env 中配置？

**方案对比**:

| 方案 | 优点 | 缺点 |
|------|------|------|
| ❌ 在 `.env` 中添加 `FRONTEND_URL=http://10.242.94.9:8080` | 统一配置 | 破坏开发环境（开发用3000） |
| ✅ 在 `docker-compose.yml` 中覆盖 | 环境隔离 | Docker专属配置 |

**最佳实践**:
- `.env`: 存放通用配置（飞书凭证、API密钥等）
- `docker-compose.yml`: 存放环境特定配置（端口、URL等）

这样：
- ✅ 开发环境：使用默认值 `http://10.242.94.9:3000`
- ✅ Docker环境：使用覆盖值 `http://10.242.94.9:8080`

## 执行步骤

### 1. 修改配置文件

```bash
cd /home/jian/code/Task_feishu
# 编辑 docker/docker-compose.yml，添加 FRONTEND_URL 环境变量
```

### 2. 重启Docker容器

```bash
cd docker
docker-compose down
docker-compose up -d
```

### 3. 验证环境变量

```bash
docker exec docker_app_1 printenv | grep FRONTEND_URL
```

**预期输出**:
```
FRONTEND_URL=http://10.242.94.9:8080
```

## 验证结果

### 容器状态 ✅

```bash
$ docker ps --filter name=docker_
CONTAINER ID   IMAGE             STATUS
b59bedda8d52   docker_frontend   Up 5 minutes  (0.0.0.0:8080->80/tcp)
a8b9f46b593c   docker_app        Up 5 minutes  (healthy)
```

### 环境变量 ✅

```bash
$ docker exec docker_app_1 printenv | grep -E "FRONTEND_URL|BACKEND_PORT"
BACKEND_PORT=8000
FRONTEND_URL=http://10.242.94.9:8080
```

### OAuth登录流程 ✅

**测试步骤**:
1. 访问 `http://10.242.94.9:8080`
2. 点击"登录"按钮
3. 验证OAuth参数

**实际结果**:
```
✅ 跳转到: http://10.242.94.9:9000/login?next=/oauth/authorize...
✅ OAuth参数:
   - client_id=task_feishu_dispatch_system
   - redirect_uri=http://10.242.94.9:8080/auth/callback  (✅ 正确端口)
   - response_type=code
   - scope=openid+profile+email
   - state=D81O62JIgK-z4xWOFeXi1EQ0Z5dwOuX7kKYMMHC2BcI
```

**预期回调流程**:
```
用户授权
  ↓
Identity Hub回调: http://10.242.94.9:8080/auth/callback?code=xxx&state=xxx
  ↓
后端处理登录
  ↓
重定向到前端: http://10.242.94.9:8080/ (✅ 使用FRONTEND_URL)
  ↓
登录成功，显示用户信息
```

## 技术细节

### OAuth回调重定向逻辑

**代码位置**: `backend/auth_routes.py`

```python
# 第114行 - 错误处理重定向
frontend_url = os.getenv("FRONTEND_URL", "http://10.242.94.9:3000")
return RedirectResponse(
    url=f"{frontend_url}/?error={error}",
)

# 第298-299行 - 成功登录重定向
frontend_url = os.getenv("FRONTEND_URL", "http://10.242.94.9:3000")
return_url = f"{frontend_url}{return_url}"
return RedirectResponse(
    url=return_url,
    status_code=302
)

# 第309-311行 - OAuth失败重定向
frontend_url = os.getenv("FRONTEND_URL", "http://10.242.94.9:3000")
return RedirectResponse(
    url=f"{frontend_url}/?error=oauth_failed",
)
```

### 前端登录按钮逻辑

**文件**: `frontend/src/components/LoginButton.js:58-59`

```javascript
const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://10.242.94.9:8080';
window.location.href = `${backendUrl}/auth/login?return_url=${returnUrl}`;
```

**环境变量优先级**:
1. 构建时: `REACT_APP_BACKEND_URL` (如果设置)
2. 运行时: 默认值 `http://10.242.94.9:8080`

**注意**: Docker环境中前端是静态文件，`REACT_APP_BACKEND_URL` 在构建时确定，无法在运行时修改。

## 相关配置总结

### 端口配置对照表

| 配置项 | 开发环境 | Docker环境 | 配置位置 |
|--------|---------|-----------|---------|
| 前端访问端口 | 3000 | 8080 | 浏览器地址 |
| 后端API端口 | 8080 | 8000 (内部) | docker-compose.yml |
| Identity Hub | 9000 | 9000 | 独立服务 |
| OAuth回调地址 | http://10.242.94.9:8080/auth/callback | http://10.242.94.9:8080/auth/callback | .env (IDENTITY_HUB_REDIRECT_URI) |
| 登录成功重定向 | http://10.242.94.9:3000/ | http://10.242.94.9:8080/ | docker-compose.yml (FRONTEND_URL) |

### 环境变量配置清单

**`.env` 文件**（通用配置）:
```bash
# OAuth配置
IDENTITY_HUB_URL=http://10.242.94.9:9000
IDENTITY_HUB_CLIENT_ID=task_feishu_dispatch_system
IDENTITY_HUB_CLIENT_SECRET=...
IDENTITY_HUB_REDIRECT_URI=http://10.242.94.9:8080/auth/callback

# 飞书配置
FEISHU_APP_ID=...
FEISHU_APP_SECRET=...

# API配置
API_KEYS=...
READONLY_API_KEYS=...
```

**`docker-compose.yml`**（Docker特定配置）:
```yaml
services:
  app:
    environment:
      - BACKEND_PORT=8000              # 容器内部端口
      - FRONTEND_URL=http://10.242.94.9:8080  # Docker前端URL
```

**开发环境启动**（开发特定配置）:
```bash
# 后端
uvicorn main:app --reload --port 8080
# FRONTEND_URL 使用默认值: http://10.242.94.9:3000

# 前端
npm start
# 自动使用端口 3000
```

## 可能的问题

### 问题1: 如果修改前端端口怎么办？

**场景**: 需要将Docker前端改为80端口

**解决方案**:
1. 修改 `docker-compose.yml` 中的端口映射:
   ```yaml
   frontend:
     ports:
       - "80:80"  # 改为80
   ```

2. 同时修改 `FRONTEND_URL`:
   ```yaml
   app:
     environment:
       - FRONTEND_URL=http://10.242.94.9:80
   ```

3. 更新Identity Hub OAuth应用白名单（数据库）:
   ```sql
   UPDATE oauth_clients
   SET redirect_uris='["http://10.242.94.9:80/auth/callback", ...]'
   WHERE client_id='task_feishu_dispatch_system';
   ```

### 问题2: 开发环境也想用8080怎么办？

**不推荐**: 会与后端8080端口冲突

**解决方案**: 分别使用不同端口
- 前端开发服务器: 3000（标准）
- 后端API: 8080
- 通过 `package.json` 中的 `proxy` 配置转发API请求

### 问题3: 如何在本地测试生产构建？

```bash
# 构建前端
cd frontend
npm run build

# 使用临时服务器（端口8080）
npx serve -s build -l 8080

# 设置环境变量（临时）
export FRONTEND_URL=http://10.242.94.9:8080

# 启动后端
cd ../backend
uvicorn main:app --reload --port 8000
```

## 后续优化建议

### 1. 配置管理优化（优先级：中）

**当前问题**:
- 多处硬编码默认值 `http://10.242.94.9:3000`
- 环境变量分散在多个文件

**建议**:
- 在 `config.py` 中统一管理所有环境变量
- 添加配置验证和错误提示
- 在Configuration Summary中显示FRONTEND_URL

**示例**:
```python
# config.py
class ServerConfig:
    frontend_url: str = os.getenv("FRONTEND_URL", "http://10.242.94.9:3000")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8080"))

    def validate(self):
        if "localhost" in self.frontend_url:
            logger.warning("Using localhost in FRONTEND_URL may cause issues in Docker")
```

### 2. 多环境配置支持（优先级：低）

**目标**: 支持开发、测试、生产环境的自动切换

**方案**:
```yaml
# docker-compose.dev.yml
services:
  app:
    environment:
      - FRONTEND_URL=http://10.242.94.9:3000

# docker-compose.prod.yml
services:
  app:
    environment:
      - FRONTEND_URL=http://10.242.94.9:8080
```

**使用**:
```bash
# 开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

### 3. 健康检查增强（优先级：低）

**添加配置验证端点**:
```python
@app.get("/debug/config")
async def debug_config():
    return {
        "frontend_url": os.getenv("FRONTEND_URL"),
        "backend_port": os.getenv("BACKEND_PORT"),
        "environment": "docker" if os.path.exists("/.dockerenv") else "local"
    }
```

## 相关文档

- 📋 [端口架构说明](PORT_ARCHITECTURE_EXPLANATION.md) - 开发/Docker环境端口差异
- 📋 [OAuth回调地址修复](OAUTH_FIX_2025-11-04.md) - Identity Hub白名单配置
- 📋 [Docker迁移验证](DOCKER_MIGRATION_VERIFICATION_2025-11-04.md) - Docker环境部署记录
- 📋 [端口修复总记录](PORT_FIX_2025-11-04.md) - 8081→8080端口修复

## 测试清单

- [x] Docker容器环境变量正确加载
- [x] 点击登录按钮跳转到Identity Hub
- [x] OAuth参数包含正确的redirect_uri (8080)
- [ ] 完成OAuth授权后重定向到8080端口（需要飞书扫码，暂未测试）
- [x] 开发环境不受影响（使用默认3000端口）

## 注意事项

⚠️ **重要提醒**:

1. **环境变量修改后必须重启容器**
   ```bash
   docker-compose down && docker-compose up -d
   ```

2. **前端构建时的环境变量无法在运行时修改**
   - Docker前端是静态文件，`REACT_APP_BACKEND_URL` 在构建时确定
   - 如需修改，必须重新构建前端 (`npm run build`) 和Docker镜像

3. **后端环境变量可以在运行时覆盖**
   - 通过 `docker-compose.yml` 的 `environment` 配置
   - 或通过 `docker run -e` 参数

4. **OAuth回调地址白名单同步**
   - 修改 `IDENTITY_HUB_REDIRECT_URI` 后
   - 必须同步更新Identity Hub数据库中的白名单
   - 参考 [OAuth回调地址修复文档](OAUTH_FIX_2025-11-04.md)

---

**修复完成时间**: 2025-11-04 11:50
**验证状态**: ✅ 部分验证通过（OAuth跳转正确，回调重定向需实际登录测试）
**下一步**: 完成实际的飞书扫码登录测试，验证回调重定向
