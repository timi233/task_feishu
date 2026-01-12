# 开发环境与Docker环境端口架构说明

**日期**: 2025-11-04
**问题**: 为什么开发环境用3000端口访问，Docker环境用8080端口？

## 架构对比

### 开发环境架构

```
浏览器 (http://10.242.94.9:3000)
   ↓
React Dev Server (webpack-dev-server, port 3000)
   ├─ 静态资源: 直接提供（热重载）
   └─ API请求: proxy转发 ↓
                         ↓
                    FastAPI (Uvicorn, port 8080)
                         ↓
                    SQLite Database
```

**特点**:
- 前端：React开发服务器（`npm start`）- **端口3000**
- 后端：FastAPI/Uvicorn（`uvicorn main:app`）- **端口8080**
- 代理配置：`frontend/package.json` 中的 `"proxy": "http://10.242.94.9:8080"`
- 热重载：修改代码自动刷新浏览器

**访问方式**:
```bash
# 前端界面
http://10.242.94.9:3000

# API直接访问
http://10.242.94.9:8080/api/tasks
http://10.242.94.9:8080/docs
```

### Docker生产环境架构

```
浏览器 (http://10.242.94.9:8080)
   ↓
Nginx (port 80, 映射到主机8080)
   ├─ 静态资源: /usr/share/nginx/html/
   └─ API请求 (/api/*, /auth/*, /health): 反向代理 ↓
                                                    ↓
                                            FastAPI (Uvicorn, 容器内port 8000)
                                                    ↓
                                            SQLite Database (挂载卷)
```

**特点**:
- 前端：Nginx托管静态文件（React构建产物）- **主机端口8080**
- 后端：FastAPI/Uvicorn - **容器内部端口8000**（不直接暴露）
- 反向代理：Nginx将API请求转发到后端容器
- 生产优化：静态资源压缩、缓存、负载均衡

**访问方式**:
```bash
# 前端界面（Nginx提供）
http://10.242.94.9:8080

# API请求（Nginx代理到后端）
http://10.242.94.9:8080/api/tasks
http://10.242.94.9:8080/docs
```

## 为什么端口不同？

### 1. 开发环境使用3000端口

**原因**:
- React开发服务器（Create React App）的**默认端口是3000**
- 这是前端开发的行业标准端口
- 便于快速启动，无需复杂配置

**优点**:
- ✅ 热重载（Hot Module Replacement）
- ✅ 开发工具支持（Source Maps）
- ✅ 详细的错误信息
- ✅ 快速启动和重启

**为什么不用8080**:
- 8080被后端占用
- 前后端分离开发，各自使用独立端口

### 2. Docker环境使用8080端口

**原因**:
- 生产环境通常使用**统一入口**（单一端口）
- Nginx作为反向代理，同时处理静态资源和API请求
- 避免CORS问题（所有请求来自同一域名和端口）

**为什么不用3000**:
- 3000端口通常用于开发环境
- 生产环境惯例使用80（HTTP）或8080（非root用户）

**为什么不用80**:
- 80端口需要root权限
- 8080是常用的非特权端口（>1024）
- 避免与主机其他服务冲突

## 配置文件对比

### 开发环境配置

**前端** (`frontend/package.json`):
```json
{
  "proxy": "http://10.242.94.9:8080",
  "scripts": {
    "start": "react-scripts start"  // 默认启动在3000端口
  }
}
```

**后端启动**:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### Docker环境配置

**docker-compose.yml**:
```yaml
services:
  frontend:
    ports:
      - "8080:80"  # 主机8080 → 容器80（Nginx）

  app:  # 后端
    # ports: (不暴露端口，仅内部访问)
    environment:
      - BACKEND_PORT=8000
```

**Nginx配置** (`docker/nginx/nginx.frontend.conf`):
```nginx
server {
    listen 80;  # 容器内部监听80

    # 静态资源
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location ~ ^/(api|auth|health|docs|openapi.json) {
        proxy_pass http://app:8000;  # 转发到后端容器
    }
}
```

## 端口映射详解

### 开发环境端口映射

| 服务 | 容器/进程端口 | 主机端口 | 访问地址 |
|------|--------------|---------|---------|
| React Dev Server | 3000 | 3000 | http://10.242.94.9:3000 |
| FastAPI Backend | 8080 | 8080 | http://10.242.94.9:8080 |
| Identity Hub | 9000 | 9000 | http://10.242.94.9:9000 |

### Docker环境端口映射

| 服务 | 容器内部端口 | 主机端口 | 访问地址 | 说明 |
|------|-------------|---------|---------|------|
| Nginx (前端) | 80 | 8080 | http://10.242.94.9:8080 | 唯一入口 |
| FastAPI (后端) | 8000 | - | (内部) | 不直接暴露 |
| Identity Hub | 9000 | 9000 | http://10.242.94.9:9000 | OAuth Provider |

## 反向代理的好处

Docker环境使用Nginx反向代理有以下优势：

1. **统一入口** ✅
   - 前端和后端使用同一个域名和端口
   - 避免CORS跨域问题
   - 简化客户端配置

2. **安全性** ✅
   - 后端不直接暴露给外部
   - Nginx可以添加安全头（CORS、CSP等）
   - 隐藏后端实现细节

3. **性能优化** ✅
   - 静态资源缓存
   - Gzip压缩
   - HTTP/2支持
   - 负载均衡（多个后端实例）

4. **灵活性** ✅
   - 可以轻松添加SSL/TLS（HTTPS）
   - 路径重写和URL美化
   - A/B测试和灰度发布

## 常见场景

### 场景1: 本地开发（前端调试）

```bash
# 启动后端
cd backend
uvicorn main:app --reload --port 8080

# 启动前端（另一个终端）
cd frontend
npm start  # 自动打开 http://localhost:3000
```

**访问**: `http://10.242.94.9:3000` → 前端通过proxy访问后端8080

### 场景2: 生产部署（Docker）

```bash
# 启动所有服务
cd docker
docker-compose up -d
```

**访问**: `http://10.242.94.9:8080` → Nginx同时提供前端和API

### 场景3: 前端生产构建测试

如果想在本地测试生产构建，可以临时启动Nginx：

```bash
cd frontend
npm run build

# 使用临时HTTP服务器（端口8080）
npx serve -s build -l 8080
```

## OAuth回调配置

这也是为什么OAuth回调地址不同：

**开发环境**:
```env
IDENTITY_HUB_REDIRECT_URI=http://10.242.94.9:3000/auth/callback
```
但实际上，我们配置的是后端的回调地址：
```env
IDENTITY_HUB_REDIRECT_URI=http://10.242.94.9:8080/auth/callback
```
因为OAuth流程由后端处理。

**Docker环境**:
```env
IDENTITY_HUB_REDIRECT_URI=http://10.242.94.9:8080/auth/callback
```
前端和后端都在8080端口下（Nginx代理）。

## 技术决策总结

| 方面 | 开发环境 | Docker环境 | 理由 |
|------|---------|-----------|------|
| 前端端口 | 3000 | 8080 | 开发便利 vs 生产统一 |
| 后端端口 | 8080 | 8000(内部) | 直接访问 vs 代理隔离 |
| 反向代理 | ❌ (前端proxy) | ✅ (Nginx) | 开发速度 vs 生产性能 |
| 静态资源 | Dev Server | Nginx | 热重载 vs 高性能缓存 |
| API访问 | 直连后端8080 | Nginx代理 | 简单直接 vs 安全统一 |

## 最佳实践建议

### 当前配置（推荐保持）

✅ **开发环境**:
- 前端 3000（React Dev Server）
- 后端 8080（FastAPI）

✅ **Docker环境**:
- 统一入口 8080（Nginx）
- 后端内部 8000（不暴露）

### 可选优化方案

**方案A: 生产环境使用80端口（需要root权限）**
```yaml
# docker-compose.yml
frontend:
  ports:
    - "80:80"
```

**方案B: 使用环境变量控制端口**
```yaml
frontend:
  ports:
    - "${FRONTEND_PORT:-8080}:80"
```

**方案C: 开发环境也使用8080（不推荐）**
```json
// package.json
"scripts": {
  "start": "PORT=8080 react-scripts start"
}
```
❌ 缺点：与后端端口冲突

## 常见问题

### Q: 能否统一使用同一个端口？

A: 理论上可以，但不推荐：
- 开发环境：前端8080会与后端8080冲突
- Docker环境：已经是统一端口（8080），通过Nginx代理

### Q: 为什么不让Docker也用3000端口？

A: 可以，但违反惯例：
- 3000通常表示"开发环境"
- 8080表示"生产环境/HTTP代理"
- 统一使用8080便于运维识别环境类型

### Q: Identity Hub为什么用9000端口？

A:
- 独立服务，不需要与前端统一
- 9000避免与常用端口冲突（3000/8000/8080）
- OAuth Provider通常使用独立域名和端口

---

**总结**: 端口选择遵循"开发便利性"和"生产标准化"的平衡原则，这是行业最佳实践。
