# 文档索引

快速查找所有项目文档。

---

## 📚 用户文档

### 快速开始
- **[README.md](README.md)** - 项目概述和快速开始指南
- **[README_DEPLOY.md](README_DEPLOY.md)** - 最快速的部署流程(⭐ 推荐新用户)

### 部署相关
- **[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - 详细部署步骤和说明
- **[DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)** - 部署验证清单
- **[DEPLOYMENT_FILES_SUMMARY.md](DEPLOYMENT_FILES_SUMMARY.md)** - 部署文件总览
- **[deploy.sh](deploy.sh)** - 一键部署脚本
- **[pre-deploy-check.sh](pre-deploy-check.sh)** - 部署前环境检查脚本
- **[backup.sh](backup.sh)** - 数据库备份脚本

### 功能说明
- **[docs/FEATURES.md](docs/FEATURES.md)** - 系统功能详细介绍
- **[CHANGELOG.md](CHANGELOG.md)** - 版本更新日志

### API接口
- **[docs/API_USAGE_GUIDE.md](docs/API_USAGE_GUIDE.md)** - API接口详细说明
- **Swagger UI** - 访问 `http://localhost:8000/docs` 查看交互式API文档

---

## 💻 开发者文档

### 开发指南
- **[CLAUDE.md](CLAUDE.md)** - 开发者指南和项目架构说明
- **[.env.example](.env.example)** - 环境变量配置模板

### 技术文档
- **[FRONTEND_REFACTORING_2025-10-17.md](FRONTEND_REFACTORING_2025-10-17.md)** - 前端重构文档
- **[TIME_FILTER_FEATURE_2025-10-17.md](TIME_FILTER_FEATURE_2025-10-17.md)** - 时间筛选功能文档
- **[REFACTORING_REPORT_2025-10-17.md](REFACTORING_REPORT_2025-10-17.md)** - 重构报告
- **[WORK_LOG_2025-10-17.md](WORK_LOG_2025-10-17.md)** - 工作日志

### 配置文件
- **[backend/filter_config.json](backend/filter_config.json)** - 筛选器配置
- **[docker-compose.yml](docker-compose.yml)** - Docker编排配置
- **[Dockerfile](Dockerfile)** - 后端Docker镜像构建文件
- **[dd/Dockerfile.frontend](dd/Dockerfile.frontend)** - 前端Docker镜像构建文件

---

## 🎯 按场景查找

### 我想部署系统
1. 阅读 [README_DEPLOY.md](README_DEPLOY.md) - 快速了解部署流程
2. 运行 `./pre-deploy-check.sh` - 检查环境
3. 配置 `.env` 文件 - 参考 `.env.example`
4. 运行 `./deploy.sh` - 一键部署
5. 参考 [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md) - 验证部署

### 我想了解功能
1. 阅读 [README.md](README.md) - 核心功能概述
2. 阅读 [docs/FEATURES.md](docs/FEATURES.md) - 详细功能说明
3. 查看 [CHANGELOG.md](CHANGELOG.md) - 了解最新更新

### 我想使用API
1. 阅读 [docs/API_USAGE_GUIDE.md](docs/API_USAGE_GUIDE.md) - API使用文档
2. 访问 `http://localhost:8000/docs` - 查看Swagger UI
3. 配置API密钥 - 在 `.env` 中设置

### 我想进行开发
1. 阅读 [CLAUDE.md](CLAUDE.md) - 项目架构和开发指南
2. 查看 [backend/](backend/) - 后端代码
3. 查看 [frontend/src/](frontend/src/) - 前端代码
4. 运行本地开发环境 - 参考 CLAUDE.md 中的"常用命令"

### 遇到问题
1. 查看 [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) 的"常见问题"章节
2. 运行 `docker-compose logs` 查看日志
3. 参考 [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md) 的"问题排查清单"

---

## 📂 目录结构

```
Task_feishu/
├── 📖 用户文档
│   ├── README.md                          # 项目主文档
│   ├── README_DEPLOY.md                   # 快速部署指南 ⭐
│   ├── DEPLOY_CHECKLIST.md                # 部署检查清单
│   ├── DEPLOYMENT_FILES_SUMMARY.md        # 部署文件总览
│   ├── CHANGELOG.md                       # 更新日志
│   └── DOCUMENTATION_INDEX.md             # 本文档
│
├── 📚 详细文档 (docs/)
│   ├── DEPLOYMENT_GUIDE.md                # 详细部署文档
│   ├── FEATURES.md                        # 功能说明
│   └── API_USAGE_GUIDE.md                 # API文档
│
├── 🛠️ 部署脚本
│   ├── deploy.sh                          # 一键部署
│   ├── pre-deploy-check.sh                # 环境检查
│   └── backup.sh                          # 数据备份
│
├── 💻 开发文档
│   ├── CLAUDE.md                          # 开发指南 ⭐
│   ├── FRONTEND_REFACTORING_*.md          # 前端重构文档
│   ├── TIME_FILTER_FEATURE_*.md           # 功能文档
│   ├── REFACTORING_REPORT_*.md            # 重构报告
│   └── WORK_LOG_*.md                      # 工作日志
│
├── 🐳 Docker配置
│   ├── docker-compose.yml                 # Docker编排
│   ├── Dockerfile                         # 后端镜像
│   └── dd/Dockerfile.frontend             # 前端镜像
│
├── 🔧 代码目录
│   ├── backend/                           # 后端代码
│   └── frontend/                          # 前端代码
│
└── ⚙️ 配置文件
    ├── .env.example                       # 环境变量模板
    └── backend/filter_config.json         # 筛选器配置
```

---

## 🔗 快速链接

### 在线访问
- 前端界面: http://localhost:8080
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### 常用命令
```bash
# 部署
./deploy.sh

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 备份数据
./backup.sh
```

---

**最后更新**: 2025-10-20
**版本**: 1.1.0
