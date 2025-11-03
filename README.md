# 派工管理系统

飞书派工系统 - 从飞书多维表格同步任务数据,提供多视图展示和自动同步功能。

## 核心功能

- 🔐 **统一身份认证**: 集成Identity Hub,支持OAuth 2.0 + OpenID Connect
  - 飞书扫码登录,无需记忆密码
  - 基于角色的权限控制(RBAC)
  - 安全的会话管理和Token刷新
- 🔄 **智能同步**: 页面打开时自动同步,之后每小时自动同步一次
- 📊 **多视图展示**: 周视图、月视图、按日期/工程师视图
- ⚡ **手动控制**: 随时手动同步,可开启/关闭自动同步
- 🎯 **任务筛选**: 支持优先级、状态等多维度筛选
- 📈 **实时统计**: 动态统计不同优先级任务数量
- 🔌 **API接口**: 完整的RESTful API供其他系统集成

## 快速开始

### 使用Docker部署(推荐)

```bash
# 1. 克隆项目
git clone <repository_url> Task_feishu
cd Task_feishu

# 2. 配置环境变量
cp .env.example .env
nano .env  # 填写飞书凭证和Identity Hub配置

# 3. 一键部署
chmod +x deploy.sh
./deploy.sh

# 4. 访问系统
# 前端: http://localhost:8080
# 后端: http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 手动部署

详见 [快速部署指南](README_DEPLOY.md) 或 [详细部署文档](docs/DEPLOYMENT_GUIDE.md)

## 文档索引

📑 **[完整文档索引](DOCUMENTATION_INDEX.md)** - 查看所有文档和按场景查找指南

**快速访问**:
- 📖 [快速部署指南](README_DEPLOY.md) - 最快速的部署流程
- 📚 [详细部署文档](docs/DEPLOYMENT_GUIDE.md) - 完整的部署步骤
- 🔐 [身份认证集成指南](docs/PHASE3_OAUTH_INTEGRATION_GUIDE.md) - OAuth认证配置说明
- 🔧 [登录问题解决记录](docs/LOGIN_ISSUE_RESOLUTION_2025-11-03.md) - 问题排查参考
- 🎨 [功能说明文档](docs/FEATURES.md) - 系统功能详细介绍
- 🔧 [API使用文档](docs/API_USAGE_GUIDE.md) - API接口详细说明
- 📝 [更新日志](CHANGELOG.md) - 版本更新记录
- 💻 [开发文档](CLAUDE.md) - 开发者指南

## 技术栈

**后端**:
- FastAPI (Python 3.9+) - RESTful API服务
- SQLite/MySQL - 数据持久化
- OAuth 2.0 + OpenID Connect - 身份认证协议
- Identity Hub - 统一身份认证中心

**前端**:
- React 18 - UI框架
- Tailwind CSS - 样式框架
- OAuth Client - 认证客户端

**部署**: Docker + Docker Compose

## 身份认证

本系统集成了Identity Hub统一身份认证中心,支持飞书扫码登录。

### 登录流程

1. **访问系统**: 打开 http://10.242.94.9:3000
2. **点击登录**: 点击右上角"登录"按钮
3. **扫码授权**: 使用飞书App扫描二维码
4. **自动跳转**: 授权成功后自动跳转回系统,显示用户信息

### 技术特性

- ✅ **OAuth 2.0标准**: 完全符合OAuth 2.0 + OpenID Connect规范
- ✅ **安全会话**: 使用httponly cookie,防止XSS攻击
- ✅ **CSRF保护**: state参数验证,防止跨站请求伪造
- ✅ **Token刷新**: 支持refresh_token自动续期
- ✅ **权限控制**: 集成RBAC权限系统

### 关键配置

登录功能需要以下环境变量配置:

```bash
# Identity Hub配置
IDENTITY_HUB_URL=http://10.242.94.9:9000
IDENTITY_HUB_CLIENT_ID=task_feishu_dispatch_system
IDENTITY_HUB_CLIENT_SECRET=task_secret_key_2024
IDENTITY_HUB_REDIRECT_URI=http://10.242.94.9:8081/auth/callback
FRONTEND_URL=http://10.242.94.9:3000
```

### 故障排查

如遇登录问题,请参考[登录问题解决记录](docs/LOGIN_ISSUE_RESOLUTION_2025-11-03.md),常见问题包括:
- Cookie命名冲突
- URL参数编码错误
- 回调地址配置错误
- session过期

---

# Docker 部署详细说明

本项目采用 Docker 进行容器化部署，使用 Docker Compose 进行编排。

## 目录结构

```
task_feishu/
├── backend/          # 后端代码
├── frontend/         # 前端代码
├── data/             # (运行时创建) 用于持久化存储 SQLite 数据库文件
├── Dockerfile        # Docker 构建文件
├── docker-compose.yml # Docker Compose 编排文件
└── .dockerignore     # Docker 忽略文件
```

## 构建和运行

1.  **设置环境变量**：
    在运行 `docker-compose` 命令之前，需要设置飞书应用的环境变量。
    可以通过以下方式设置：
    *   **方式一：在终端中导出环境变量**
        ```bash
        export FEISHU_APP_ID=your_actual_app_id
        export FEISHU_APP_SECRET=your_actual_app_secret
        export FEISHU_APP_TOKEN=your_actual_app_token
        export FEISHU_TABLE_ID=your_actual_table_id
        ```
    *   **方式二：创建 `.env` 文件**
        在 `task_feishu` 目录下创建一个 `.env` 文件，并添加以下内容：
        ```
        FEISHU_APP_ID=your_actual_app_id
        FEISHU_APP_SECRET=your_actual_app_secret
        FEISHU_APP_TOKEN=your_actual_app_token
        FEISHU_TABLE_ID=your_actual_table_id
        ```

2.  **构建镜像**：
    ```bash
    cd task_feishu
    docker-compose build
    ```

3.  **启动服务**：
    ```bash
    docker-compose up
    ```
    或者在后台运行：
    ```bash
    docker-compose up -d
    ```

4.  **访问应用**：
    *   后端API: `http://localhost:8000/api/tasks`
    *   前端页面: `http://localhost:8000/static/index.html`

5.  **停止服务**：
    ```bash
    docker-compose down
    ```

## 数据持久化

SQLite 数据库文件 `tasks.db` 会保存在主机的 `task_feishu/data` 目录中，以确保容器重启或删除后数据不会丢失。

## 环境变量

### 飞书多维表格配置

| 变量名 | 描述 | 默认值 |
| :--- | :--- | :--- |
| `FEISHU_APP_ID` | 飞书应用的 App ID | `your_app_id_here` |
| `FEISHU_APP_SECRET` | 飞书应用的 App Secret | `your_app_secret_here` |
| `FEISHU_APP_TOKEN` | 飞书多维表格的 App Token | `your_app_token_here` |
| `FEISHU_TABLE_ID` | 飞书多维表格中具体表的 ID | `your_table_id_here` |

### Identity Hub身份认证配置

| 变量名 | 描述 | 示例值 |
| :--- | :--- | :--- |
| `IDENTITY_HUB_URL` | Identity Hub服务地址 | `http://10.242.94.9:9000` |
| `IDENTITY_HUB_CLIENT_ID` | OAuth客户端ID | `task_feishu_dispatch_system` |
| `IDENTITY_HUB_CLIENT_SECRET` | OAuth客户端密钥 | `task_secret_key_2024` |
| `IDENTITY_HUB_REDIRECT_URI` | OAuth回调地址 | `http://10.242.94.9:8081/auth/callback` |
| `FRONTEND_URL` | 前端应用地址(登录后跳转) | `http://10.242.94.9:3000` |

### 服务端口配置

| 变量名 | 描述 | 默认值 |
| :--- | :--- | :--- |
| `BACKEND_PORT` | 后端服务监听的端口 | `8081` |
| `FRONTEND_PORT` | 前端服务监听的端口 | `3000` |

**注意事项**:
- 身份认证功能需要先部署Identity Hub服务
- Cookie命名: 后端使用`task_session_id`,避免与Identity Hub的`session_id`冲突
- 详细配置说明见[身份认证集成指南](docs/PHASE3_OAUTH_INTEGRATION_GUIDE.md)