# 派工管理系统

飞书派工系统 - 从飞书多维表格同步任务数据，提供多视图展示和自动同步功能。

## 核心功能

- **统一身份认证**: 集成 Identity Hub，支持 OAuth 2.0 + OpenID Connect
  - 飞书扫码登录，无需记忆密码
  - 基于角色的权限控制 (RBAC)
  - 安全的会话管理和 Token 刷新
- **智能同步**: 容器启动时自动同步，之后每30分钟自动同步一次
- **多视图展示**: 周视图、月视图、按日期/工程师视图
- **手动控制**: 随时手动同步，可开启/关闭自动同步
- **任务筛选**: 支持优先级、状态等多维度筛选
- **实时统计**: 动态统计不同优先级任务数量
- **API 接口**: 完整的 RESTful API 供其他系统集成

---

## 项目结构

```
task_feishu/
├── backend/                    # 后端服务 (FastAPI)
│   ├── main.py                 # 主入口
│   ├── routers/                # API 路由
│   │   ├── tasks.py            # 任务查询 API
│   │   ├── dispatch.py         # 派工单 API (前端主要使用)
│   │   ├── sync.py             # 数据同步 API
│   │   ├── users.py            # 用户管理 API
│   │   ├── roles.py            # 角色权限 API
│   │   ├── engineers.py        # 工程师 API
│   │   ├── approvals.py        # 审批 API
│   │   └── ...
│   ├── models/                 # 数据模型
│   │   └── schemas.py          # Pydantic 模型
│   ├── utils/                  # 工具函数
│   │   ├── logging_config.py   # 日志配置
│   │   └── errors.py           # 错误处理
│   ├── task_db.py              # tasks 表数据库操作
│   ├── dispatch_db.py          # dispatch_orders 表数据库操作
│   ├── dispatch_sync.py        # 派工单同步脚本 ★
│   ├── sync_once.py            # 任务同步脚本
│   ├── feishu_reader.py        # 飞书多维表格读取器
│   ├── process_feishu_data.py  # 数据处理
│   ├── auth_*.py               # 认证相关模块
│   └── ...
├── frontend/                   # 前端应用 (React)
│   └── src/
│       ├── App.js              # 主应用
│       ├── components/         # React 组件
│       │   ├── WeekView.js     # 周视图
│       │   ├── MonthView.js    # 月视图
│       │   ├── DispatchOrdersView.js  # 派工单视图
│       │   ├── UserManagement.js      # 用户管理
│       │   └── ...
│       ├── hooks/              # React Hooks
│       └── utils/              # 工具函数
├── identity-hub/               # 统一身份认证服务
│   └── backend/
│       ├── main.py             # Identity Hub 主入口
│       ├── oauth/              # OAuth 2.0 实现
│       ├── feishu_auth.py      # 飞书认证
│       └── ...
├── docker/                     # Docker 配置
│   ├── docker-compose.yml      # 主编排文件
│   ├── Dockerfile              # 后端 Dockerfile
│   └── nginx/                  # Nginx 配置
├── scripts/                    # 脚本
│   ├── start.sh                # 容器启动脚本 ★
│   ├── cron_sync.sh            # 定时同步脚本 (Cron)
│   └── start_all_services.sh   # 本地开发启动脚本
├── docs/                       # 文档
├── data/                       # 数据目录 (SQLite 数据库)
└── .env                        # 环境变量配置
```

---

## 数据同步机制

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     飞书多维表格                              │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ 公司派单         │    │ 厂家派工         │                │
│  │ tbl6CuEM97ybgRri│    │ tbl8DESrT22JYvfS│                │
│  └────────┬────────┘    └────────┬────────┘                │
└───────────┼─────────────────────┼──────────────────────────┘
            │                     │
            ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│              定时同步任务 (scripts/start.sh)                 │
│                    每 30 分钟执行一次                         │
│                                                             │
│  sync_once.py              dispatch_sync.py                 │
│       │                          │                          │
│       ▼                          ▼                          │
│  ┌─────────┐              ┌──────────────┐                 │
│  │ tasks   │              │dispatch_orders│ ← 前端使用      │
│  │   表    │              │      表       │                 │
│  └─────────┘              └──────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### 同步方式

1. **自动同步**: 容器启动时执行初始同步，之后每30分钟自动执行
2. **手动同步**: 通过前端"同步数据"按钮或 API 触发
3. **API 触发**: `POST /api/sync/dispatch`

### 相关配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `SYNC_INTERVAL_MINUTES` | 同步间隔（分钟） | 30 |
| `FEISHU_DISPATCH_BASE_ID` | 多维表格 Base ID | U7eAb65luaX1zKscoOzcgcednlh |
| `FEISHU_WORK_ORDER_TABLE_ID` | 公司派单表 ID | tbl6CuEM97ybgRri |
| `FEISHU_EISOO_DISPATCH_TABLE_ID` | 厂家派工表 ID | tbl8DESrT22JYvfS |

---

## 快速开始

### 使用 Docker 部署（推荐）

```bash
# 1. 进入项目目录
cd /opt/task_feishu/prod_192.168.101.13

# 2. 配置环境变量
cp .env.example .env
nano .env  # 填写飞书凭证和 Identity Hub 配置

# 3. 启动服务
cd docker
docker-compose up -d

# 4. 查看日志
docker logs -f docker-app-1

# 5. 访问系统
# 前端: http://192.168.101.13:8080
# API 文档: http://192.168.101.13:8080/docs
```

### 常用运维命令

```bash
# 查看服务状态
docker ps

# 查看同步日志
docker logs docker-app-1 2>&1 | grep -E "SYNC|sync"
tail -50 /opt/task_feishu/prod_192.168.101.13/logs/sync.log

# 手动触发同步
docker exec docker-app-1 python3 -c "from dispatch_sync import sync_all; sync_all()"

# 重启服务
cd docker && docker compose restart app

# 重新构建并部署
cd docker && docker compose build app frontend && docker compose up -d

# 查看数据库数据量
docker exec docker-app-1 python3 -c "
from dispatch_db import get_db_connection
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM dispatch_orders')
    print(f'派工单数量: {cursor.fetchone()[0]}')"
```

### 定时同步 (Cron)

系统通过 Cron 每小时自动同步飞书数据：

```bash
# 查看当前 cron 配置
crontab -l

# 配置定时同步（每小时整点执行）
crontab -e
# 添加: 0 * * * * /opt/task_feishu/prod_192.168.101.13/scripts/cron_sync.sh

# 查看同步日志
tail -f /opt/task_feishu/prod_192.168.101.13/logs/sync.log
```

---

## 技术栈

### 后端
- **FastAPI** (Python 3.11) - RESTful API 服务
- **SQLite** - 数据持久化
- **OAuth 2.0 + OpenID Connect** - 身份认证协议
- **Identity Hub** - 统一身份认证中心

### 前端
- **React 18** - UI 框架
- **Tailwind CSS** - 样式框架
- **OAuth Client** - 认证客户端

### 部署
- **Docker** + **Docker Compose**
- **Nginx** - 反向代理

---

## 环境变量配置

### 飞书多维表格配置

| 变量名 | 描述 |
|--------|------|
| `FEISHU_APP_ID` | 飞书应用的 App ID |
| `FEISHU_APP_SECRET` | 飞书应用的 App Secret |
| `FEISHU_DISPATCH_BASE_ID` | 多维表格的 Base ID |
| `FEISHU_WORK_ORDER_TABLE_ID` | 公司派单表 ID |
| `FEISHU_EISOO_DISPATCH_TABLE_ID` | 厂家派工表 ID |

### Identity Hub 身份认证配置

| 变量名 | 描述 | 示例值 |
|--------|------|--------|
| `IDENTITY_HUB_URL` | Identity Hub 服务地址 | `http://192.168.101.13:9000` |
| `IDENTITY_HUB_CLIENT_ID` | OAuth 客户端 ID | `task_feishu_dispatch_system` |
| `IDENTITY_HUB_CLIENT_SECRET` | OAuth 客户端密钥 | `task_secret_key_2024` |
| `IDENTITY_HUB_REDIRECT_URI` | OAuth 回调地址 | `http://192.168.101.13:8080/auth/callback` |
| `FRONTEND_URL` | 前端应用地址 | `http://192.168.101.13:8080` |

### 其他配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `SYNC_INTERVAL_MINUTES` | 数据同步间隔 | 30 |
| `API_KEYS` | API 密钥（逗号分隔） | - |
| `READONLY_API_KEYS` | 只读 API 密钥 | - |
| `LOG_LEVEL` | 日志级别 | INFO |

---

## API 接口

### 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/dispatch/orders` | GET | 获取派工单列表（前端主要使用） |
| `/api/tasks` | GET | 获取任务列表（需登录） |
| `/api/tasks/by-engineer` | GET | 按工程师查询任务 |
| `/api/tasks/by-date` | GET | 按日期查询任务 |
| `/api/sync/dispatch` | POST | 手动触发派工单同步 |
| `/api/sync` | POST | 手动触发任务同步 |
| `/api/engineers` | GET | 获取工程师列表 |
| `/health` | GET | 健康检查 |

### API 文档

启动服务后访问: `http://192.168.101.13:8080/docs`

---

## 文档索引

### 部署文档
- [快速部署指南](docs/README_DEPLOY.md)
- [详细部署文档](docs/DEPLOYMENT_GUIDE.md)
- [Docker 迁移指南](docs/DOCKER_MIGRATION_GUIDE.md)
- [生产环境部署](docs/PROD_DEPLOYMENT_GUIDE.md)

### 功能文档
- [功能说明](docs/FEATURES.md)
- [API 使用指南](docs/API_USAGE_GUIDE.md)
- [派工流程设计](docs/DISPATCH_WORKFLOW_DESIGN.md)
- [权限管理设计](docs/PERMISSION_MANAGEMENT_DESIGN_2025-11-03.md)

### 身份认证
- [身份认证集成指南](docs/PHASE3_OAUTH_INTEGRATION_GUIDE.md)
- [Identity Hub 设计](docs/IDENTITY_HUB_DESIGN.md)
- [登录问题排查](docs/LOGIN_ISSUE_RESOLUTION_2025-11-03.md)

### 问题修复记录
- [派工同步修复 2025-12-02](docs/DISPATCH_SYNC_FIX_2025-12-02.md) - **最新**
- [登录修复 2025-11-25](docs/LOGIN_FIX_2025-11-25.md)
- [Invalid State 修复 2025-11-26](docs/INVALID_STATE_FIX_2025-11-26.md)

### 开发文档
- [开发者指南](docs/CLAUDE.md)
- [数据库 Schema](docs/DATABASE_SCHEMA_NEW_2025-11-24.md)
- [代码审查修复计划](docs/CODE_REVIEW_FIX_PLAN.md)

---

## 故障排查

### 数据不显示/不更新

1. **检查同步状态**:
   ```bash
   docker logs docker-app-1 2>&1 | grep -E "SYNC|dispatch" | tail -20
   ```

2. **手动触发同步**:
   ```bash
   docker exec docker-app-1 python3 -c "from dispatch_sync import sync_all; sync_all()"
   ```

3. **检查数据库**:
   ```bash
   docker exec docker-app-1 python3 -c "
   from dispatch_db import get_db_connection
   with get_db_connection() as conn:
       cursor = conn.cursor()
       cursor.execute('SELECT COUNT(*), MAX(service_start_time) FROM dispatch_orders')
       print(cursor.fetchone())"
   ```

### 登录问题

参考 [登录问题解决记录](docs/LOGIN_ISSUE_RESOLUTION_2025-11-03.md)，常见问题：
- Cookie 命名冲突
- URL 参数编码错误
- 回调地址配置错误
- Session 过期

### 服务无法启动

1. 检查环境变量配置是否完整
2. 检查 Identity Hub 服务是否运行
3. 检查端口是否被占用

---

## 更新日志

### 2025-12-02
- 修复派工单数据同步不完整的问题
- 更新 `start.sh`，增加 `dispatch_sync.py` 调用

### 2025-11-24
- 新增多工程师派工单支持
- 优化派工单字段映射

### 2025-11-09
- 完善权限管理前端界面
- 修复用户角色分配问题

---

## 联系方式

如遇问题，请联系系统管理员或查看 [问题修复记录](docs/) 目录下的相关文档。
