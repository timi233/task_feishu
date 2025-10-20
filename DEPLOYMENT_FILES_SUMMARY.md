# 外部设备部署文件总览

本文档列出为外部设备部署准备的所有文件和使用方法。

---

## 📄 核心部署文件

### 1. 配置文件
| 文件 | 用途 | 是否必须 |
|------|------|----------|
| `.env.example` | 环境变量模板 | ✅ 必须复制为.env |
| `docker-compose.yml` | Docker编排配置 | ✅ 必须 |
| `Dockerfile` | 后端镜像构建 | ✅ 必须 |
| `dd/Dockerfile.frontend` | 前端镜像构建 | ✅ 必须 |

### 2. 部署脚本
| 文件 | 用途 | 使用方法 |
|------|------|----------|
| `deploy.sh` | 一键自动部署 | `./deploy.sh` |
| `pre-deploy-check.sh` | 部署前环境检查 | `./pre-deploy-check.sh` |
| `backup.sh` | 数据库备份 | `./backup.sh` |

### 3. 文档
| 文件 | 内容 | 适用人群 |
|------|------|----------|
| `README_DEPLOY.md` | 快速部署指南 | 初次部署用户 |
| `docs/DEPLOYMENT_GUIDE.md` | 详细部署文档 | 需要深入了解的用户 |
| `docs/API_USAGE_GUIDE.md` | API使用文档 | 其他系统开发者 |
| `DEPLOY_CHECKLIST.md` | 部署检查清单 | 所有用户 |

---

## 🚀 快速部署流程

### 新用户(推荐)

```bash
# 1. 检查环境
./pre-deploy-check.sh

# 2. 配置环境变量
cp .env.example .env
nano .env  # 填写飞书凭证

# 3. 一键部署
./deploy.sh
```

### 有经验用户

```bash
# 1. 配置.env
cp .env.example .env && nano .env

# 2. 手动部署
mkdir -p data/db
docker-compose up -d --build
```

---

## 📦 打包传输指南

### 方式一: 使用tar打包

```bash
# 在源服务器打包(排除不需要的文件)
tar -czf Task_feishu_deploy.tar.gz \
  --exclude='.git' \
  --exclude='data' \
  --exclude='backend/__pycache__' \
  --exclude='frontend/node_modules' \
  --exclude='frontend/build' \
  --exclude='.env' \
  Task_feishu/

# 传输到目标服务器
scp Task_feishu_deploy.tar.gz user@target-server:/home/user/

# 在目标服务器解压
tar -xzf Task_feishu_deploy.tar.gz
cd Task_feishu
```

### 方式二: 使用rsync

```bash
rsync -avz --progress \
  --exclude='.git' \
  --exclude='data' \
  --exclude='backend/__pycache__' \
  --exclude='frontend/node_modules' \
  --exclude='.env' \
  Task_feishu/ user@target-server:/home/user/Task_feishu/
```

### 方式三: 手动上传(FTP/SFTP)

使用FileZilla等工具,上传以下目录:
- ✅ `backend/`
- ✅ `frontend/`
- ✅ `dd/`
- ✅ `docs/`
- ✅ 所有 `.sh` 脚本
- ✅ 所有 `.md` 文档
- ✅ `docker-compose.yml`
- ✅ `Dockerfile`
- ✅ `.env.example`

---

## 🔐 安全注意事项

### 必须修改的敏感信息

在 `.env` 文件中:

```bash
# ⚠️ 必须替换为真实值
FEISHU_APP_ID=你的APP_ID
FEISHU_APP_SECRET=你的APP_SECRET
FEISHU_APP_TOKEN=你的APP_TOKEN
FEISHU_TABLE_ID=你的TABLE_ID

# ⚠️ 必须生成强密码(至少32位)
API_KEYS=生成强密码替换
READONLY_API_KEYS=生成强密码替换

# ⚠️ 必须改为实际访问地址
ALLOWED_ORIGINS=http://你的服务器IP:8080
```

### 生成强密码

```bash
# Linux/Mac
openssl rand -base64 32

# 或使用在线工具
# https://passwordsgenerator.net/
```

---

## 📋 部署后验证

### 1. 服务状态检查

```bash
# 查看容器状态
docker-compose ps

# 预期输出: 所有服务显示 "Up"
```

### 2. 健康检查

```bash
# 后端健康检查
curl http://localhost:8000/health

# 预期输出: {"status":"healthy","database":"connected",...}
```

### 3. 前端访问

浏览器打开: `http://服务器IP:8080`

### 4. 功能测试

**自动同步功能**:
1. 打开页面时会自动同步一次数据
2. 页头显示自动同步开关和倒计时
3. 每小时自动同步一次(可通过复选框关闭)

**手动同步测试**:
1. 点击"同步数据"按钮
2. 应显示"同步成功"提示
3. 页面显示任务数据

---

## 🛠️ 常用维护命令

```bash
# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新并重启
docker-compose up -d --build --force-recreate

# 备份数据库
./backup.sh

# 查看磁盘使用
du -sh data/db/tasks.db
```

---

## 📞 获取帮助

### 文档索引

1. **快速开始**: `README_DEPLOY.md`
2. **详细步骤**: `docs/DEPLOYMENT_GUIDE.md`
3. **检查清单**: `DEPLOY_CHECKLIST.md`
4. **API文档**: `docs/API_USAGE_GUIDE.md`

### 问题排查

遇到问题时:
1. 查看日志: `docker-compose logs`
2. 检查清单: `DEPLOY_CHECKLIST.md`
3. 运行检查: `./pre-deploy-check.sh`

---

## 📊 部署文件清单

### 必须文件 (共享给部署人员)

```
Task_feishu/
├── backend/                    # 后端代码
├── frontend/                   # 前端代码
├── dd/                        # Docker配置
├── docs/                      # 文档
├── .env.example               # 环境变量模板 ⭐
├── docker-compose.yml         # Docker编排 ⭐
├── Dockerfile                 # 后端镜像 ⭐
├── deploy.sh                  # 部署脚本 ⭐
├── pre-deploy-check.sh        # 检查脚本 ⭐
├── backup.sh                  # 备份脚本
├── README_DEPLOY.md           # 快速指南 ⭐
├── DEPLOY_CHECKLIST.md        # 检查清单
└── DEPLOYMENT_FILES_SUMMARY.md # 本文档
```

### 不要传输的文件

```
Task_feishu/
├── .git/                      # Git历史(可选)
├── .env                       # 本地配置(含敏感信息) ⚠️
├── data/                      # 本地数据库 ⚠️
├── backend/__pycache__/       # Python缓存
├── frontend/node_modules/     # Node依赖
└── frontend/build/            # 构建产物
```

---

## ⚡ 一键打包命令

复制以下命令直接使用:

```bash
# 创建部署包(不含敏感数据)
tar -czf Task_feishu_deploy_$(date +%Y%m%d).tar.gz \
  --exclude='.git' \
  --exclude='data' \
  --exclude='backend/__pycache__' \
  --exclude='frontend/node_modules' \
  --exclude='frontend/build' \
  --exclude='.env' \
  Task_feishu/

echo "✓ 部署包已创建: Task_feishu_deploy_$(date +%Y%m%d).tar.gz"
```

---

**最后更新**: 2025-10-20
**版本**: 1.0
