# 派工系统外部设备部署指南

**更新日期**: 2025-10-20

本文档详细说明如何在外部服务器或设备上部署派工管理系统。

---

## 系统功能概述

### 核心功能
- **飞书数据同步**: 从飞书多维表格自动同步派工数据
- **自动同步机制**:
  - 页面打开时立即同步一次
  - 每小时自动同步一次(可开启/关闭)
  - 支持手动触发同步
  - 实时显示下次同步倒计时
- **多视图展示**: 支持周视图、月视图、按日期视图、按工程师视图
- **任务筛选**: 支持优先级筛选、状态筛选等
- **统计面板**: 实时统计不同优先级任务数量
- **RESTful API**: 提供完整的API接口供其他系统集成

---

## 目录

1. [系统要求](#系统要求)
2. [快速部署(Docker方式)](#快速部署docker方式)
3. [手动部署(非Docker)](#手动部署非docker)
4. [配置说明](#配置说明)
5. [启动与停止](#启动与停止)
6. [常见问题](#常见问题)
7. [维护与备份](#维护与备份)

---

## 系统要求

### 硬件要求
- **CPU**: 1核及以上
- **内存**: 512MB及以上 (推荐1GB)
- **磁盘**: 2GB可用空间
- **网络**: 需要访问飞书API (open.feishu.cn)

### 软件要求

**方式一: Docker部署(推荐)**
- Docker 20.10+
- Docker Compose 1.29+

**方式二: 手动部署**
- Python 3.9+
- Node.js 16+ (仅构建前端时需要)
- Nginx (可选,用于生产环境)

---

## 快速部署(Docker方式)

### 1. 准备项目文件

在外部设备上创建项目目录并获取代码:

```bash
# 方式A: 使用git克隆(如果有仓库)
git clone <repository_url> Task_feishu
cd Task_feishu

# 方式B: 手动传输
# 将整个项目文件夹复制到目标设备
scp -r /path/to/Task_feishu user@remote-server:/home/user/
```

### 2. 配置环境变量

复制并编辑环境变量文件:

```bash
cd Task_feishu
cp .env.example .env  # 如果有示例文件
# 或直接创建 .env 文件
nano .env
```

`.env` 文件内容 (必须配置):

```bash
# === 飞书应用配置 ===
FEISHU_APP_ID=cli_xxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx
FEISHU_APP_TOKEN=xxxxxxxxxxxxxxxx
FEISHU_TABLE_ID=tblxxxxxxxxxx

# === API认证配置 ===
# 管理员API密钥(读写权限,逗号分隔支持多个)
API_KEYS=admin-key-feishu-2025,frontend-key-abc123

# 只读API密钥(供其他系统使用,逗号分隔支持多个)
READONLY_API_KEYS=readonly-key-for-hr-system,readonly-key-for-report-system

# API限流配置(每个密钥每分钟最大请求数)
API_RATE_LIMIT=100

# === CORS配置 ===
# 允许跨域访问的来源(逗号分隔)
# 部署时需要根据实际访问地址修改
ALLOWED_ORIGINS=http://your-server-ip:8080,http://your-domain.com

# === 其他配置 ===
LOG_LEVEL=INFO
SYNC_INTERVAL_MINUTES=60
```

### 3. 创建数据目录

```bash
# 创建数据库存储目录
mkdir -p data/db
chmod 755 data/db
```

### 4. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 5. 验证部署

```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 访问前端 (在浏览器中)
# http://<服务器IP>:8080
```

**预期响应**:
```json
{
  "status": "healthy",
  "database": "connected",
  "task_count": 0,
  "timestamp": "2025-10-20T10:30:00.123456"
}
```

---

## 手动部署(非Docker)

### 1. 安装依赖

```bash
# 安装Python依赖
cd backend
pip install -r requirements.txt

# 构建前端(如需)
cd ../frontend
npm install
npm run build
```

### 2. 配置环境变量

```bash
# 在项目根目录创建 .env 文件
cd /path/to/Task_feishu
nano .env
```

内容同上Docker部署的 `.env` 配置。

### 3. 初始化数据库

```bash
cd backend
python -c "from task_db import init_db; init_db()"
```

### 4. 启动后端服务

**方式A: 直接运行**
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**方式B: 使用systemd服务(推荐生产环境)**

创建服务文件 `/etc/systemd/system/task-feishu-backend.service`:

```ini
[Unit]
Description=Task Feishu Backend Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Task_feishu/backend
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile=/path/to/Task_feishu/.env
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable task-feishu-backend
sudo systemctl start task-feishu-backend
sudo systemctl status task-feishu-backend
```

### 5. 配置前端(Nginx)

安装Nginx:
```bash
sudo apt install nginx  # Ubuntu/Debian
# 或
sudo yum install nginx  # CentOS/RHEL
```

创建Nginx配置 `/etc/nginx/sites-available/task-feishu`:

```nginx
server {
    listen 8080;
    server_name your-server-ip;  # 或域名

    root /path/to/Task_feishu/frontend/build;
    index index.html;

    # 前端静态文件
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API代理到后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

启用配置:
```bash
sudo ln -s /etc/nginx/sites-available/task-feishu /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. 启动数据同步服务(可选)

创建定时同步服务 `/etc/systemd/system/task-feishu-sync.service`:

```ini
[Unit]
Description=Task Feishu Data Sync Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Task_feishu/backend
EnvironmentFile=/path/to/Task_feishu/.env
ExecStart=/usr/bin/python3 sync_feishu_to_db.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable task-feishu-sync
sudo systemctl start task-feishu-sync
```

---

## 配置说明

### 环境变量详解

| 变量名 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| `FEISHU_APP_ID` | ✅ | 飞书应用ID | `cli_a8e5c86826ab9013` |
| `FEISHU_APP_SECRET` | ✅ | 飞书应用密钥 | `ObaI5gvFKKKtKZD09olblhM13kXrNFXB` |
| `FEISHU_APP_TOKEN` | ✅ | 多维表格App Token | `ZbpqbNgpNa0IvTsXfLuc5seBnJg` |
| `FEISHU_TABLE_ID` | ✅ | 表格ID | `tblIrTdzXCFUwjti` |
| `API_KEYS` | ✅ | 管理员API密钥 | `admin-key-123,admin-key-456` |
| `READONLY_API_KEYS` | ✅ | 只读API密钥 | `readonly-key-hr,readonly-key-report` |
| `API_RATE_LIMIT` | ❌ | 限流阈值(次/分钟) | `100` (默认) |
| `ALLOWED_ORIGINS` | ✅ | CORS允许的来源 | `http://192.168.1.100:8080` |
| `LOG_LEVEL` | ❌ | 日志级别 | `INFO` (默认) |

### 安全建议

1. **修改默认API密钥**: 部署前务必替换 `.env` 中的所有默认密钥
2. **HTTPS部署**: 生产环境建议配置SSL证书
3. **防火墙配置**: 仅开放必要端口(8000, 8080)
4. **权限控制**: 数据库目录权限设为 `755` 或 `750`

---

## 启动与停止

### Docker方式

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f app        # 后端日志
docker-compose logs -f frontend   # 前端日志

# 重新构建并启动
docker-compose up -d --build --force-recreate
```

### 手动方式

```bash
# 后端
sudo systemctl start task-feishu-backend
sudo systemctl stop task-feishu-backend
sudo systemctl restart task-feishu-backend

# 前端
sudo systemctl restart nginx

# 同步服务
sudo systemctl start task-feishu-sync
sudo systemctl stop task-feishu-sync
```

---

## 常见问题

### 1. 端口被占用

**错误**: `Error: address already in use`

**解决**:
```bash
# 查看占用8000端口的进程
lsof -i:8000
# 杀死进程
kill -9 <PID>

# 或修改端口
# 编辑 docker-compose.yml 或 .env 中的端口配置
```

### 2. 数据库连接失败

**错误**: `Failed to connect to database`

**解决**:
```bash
# 检查数据目录权限
ls -la data/db/

# 修复权限
chmod 755 data/db
chown -R www-data:www-data data/db  # 根据运行用户调整
```

### 3. 前端无法连接后端

**错误**: `Failed to load resource: net::ERR_CONNECTION_REFUSED`

**解决**:
- 检查 `.env` 中的 `ALLOWED_ORIGINS` 是否包含前端访问地址
- 确认后端服务正在运行: `curl http://localhost:8000/health`
- 检查防火墙是否阻止端口

### 4. 飞书数据同步失败

**错误**: `Failed to sync data from Feishu`

**解决**:
```bash
# 手动测试同步
cd backend
python sync_once.py

# 检查飞书凭证
curl -X POST -H "X-API-Key: <your-key>" http://localhost:8000/api/sync

# 查看详细日志
docker-compose logs -f app
```

### 5. Docker镜像构建失败

**解决**:
```bash
# 清理Docker缓存
docker system prune -a

# 单独构建测试
docker build -t task-feishu-backend -f Dockerfile .
docker build -t task-feishu-frontend -f dd/Dockerfile.frontend .
```

---

## 维护与备份

### 数据备份

**方式一: 备份SQLite数据库**
```bash
# 停止服务
docker-compose down

# 备份数据库
cp data/db/tasks.db data/db/tasks_backup_$(date +%Y%m%d).db

# 启动服务
docker-compose up -d
```

**方式二: 自动备份脚本**

创建 `/home/user/backup_tasks.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/home/user/backups"
DB_PATH="/home/user/Task_feishu/data/db/tasks.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp $DB_PATH $BACKUP_DIR/tasks_$DATE.db

# 保留最近7天的备份
find $BACKUP_DIR -name "tasks_*.db" -mtime +7 -delete

echo "Backup completed: tasks_$DATE.db"
```

添加到crontab:
```bash
crontab -e
# 每天凌晨2点备份
0 2 * * * /home/user/backup_tasks.sh
```

### 日志管理

```bash
# 查看Docker日志
docker-compose logs --tail=100 -f

# 手动部署日志位置
journalctl -u task-feishu-backend -f

# 清理旧日志(Docker)
docker-compose logs --tail=0
```

### 更新系统

```bash
# Docker方式
cd /path/to/Task_feishu
git pull  # 或手动更新文件
docker-compose down
docker-compose up -d --build

# 手动方式
git pull
cd backend
pip install -r requirements.txt --upgrade
sudo systemctl restart task-feishu-backend
```

---

## 监控建议

### 1. 健康检查脚本

创建 `/home/user/check_health.sh`:
```bash
#!/bin/bash
HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s $HEALTH_URL)

if echo "$RESPONSE" | grep -q "healthy"; then
    echo "$(date): Service is healthy"
else
    echo "$(date): Service is unhealthy! Response: $RESPONSE"
    # 发送告警(邮件/钉钉/企业微信)
fi
```

### 2. 系统资源监控

```bash
# 查看Docker容器资源使用
docker stats

# 查看磁盘使用
df -h

# 查看数据库大小
du -sh data/db/tasks.db
```

---

## 联系支持

- **文档位置**: `/docs`目录
- **API文档**: `http://<server-ip>:8000/docs` (Swagger UI)
- **问题反馈**: 项目管理员

---

**部署检查清单**:

- [ ] 安装Docker和Docker Compose
- [ ] 创建并配置 `.env` 文件
- [ ] 修改默认API密钥
- [ ] 配置CORS允许的来源
- [ ] 创建数据目录并设置权限
- [ ] 启动服务: `docker-compose up -d`
- [ ] 验证后端健康: `curl http://localhost:8000/health`
- [ ] 访问前端: `http://<server-ip>:8080`
- [ ] 测试同步功能: 点击"同步数据"按钮
- [ ] 配置自动备份脚本
- [ ] 配置防火墙规则
- [ ] (可选) 配置HTTPS证书
