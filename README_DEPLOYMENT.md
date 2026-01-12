# 飞书派工系统 快速部署指南

**版本**: v1.0
**更新**: 2025-11-04

---

## 📦 部署包内容

```
task_feishu/
├── backend/              # 后端Python代码
├── frontend/build/       # 前端React构建产物
├── docker/               # Docker配置文件
│   ├── Dockerfile              # 后端镜像
│   ├── docker-compose.yml      # Docker编排
│   └── nginx/
│       ├── Dockerfile.frontend     # 前端镜像
│       └── nginx.frontend.conf     # Nginx配置
├── data/db/              # 数据库目录（SQLite）
├── scripts/              # 启动脚本
├── docs/                 # 完整文档
│   ├── DOCKER_MIGRATION_GUIDE.md           # 详细迁移手册
│   ├── FRONTEND_URL_FIX_2025-11-04.md      # 前端URL配置说明
│   └── PORT_ARCHITECTURE_EXPLANATION.md    # 端口架构说明
├── .env                  # 环境配置（需要修改）
└── README_DEPLOYMENT.md  # 本文件（快速部署指南）
```

---

## 🚀 快速开始（5分钟部署）

### 步骤1: 解压文件

```bash
# 上传压缩包到服务器
scp task_feishu-deployment.tar.gz user@NEW_SERVER_IP:/tmp/

# SSH登录到新服务器
ssh user@NEW_SERVER_IP

# 解压到用户目录
cd ~
tar -xzf /tmp/task_feishu-deployment.tar.gz
cd task_feishu
```

### 步骤2: 修改配置（⚠️ 必须操作）

```bash
# 编辑.env文件
nano .env

# 必须修改以下配置（将NEW_SERVER_IP替换为实际IP，将IDENTITY_HUB_IP替换为Identity Hub服务器IP）：
# 1. IDENTITY_HUB_URL=http://IDENTITY_HUB_IP:9000
# 2. IDENTITY_HUB_REDIRECT_URI=http://NEW_SERVER_IP:8080/auth/callback
# 3. ALLOWED_ORIGINS=http://NEW_SERVER_IP:8080,...

# 快速替换命令
# 将10.242.94.9替换为新服务器IP
sed -i 's/10.242.94.9/NEW_SERVER_IP/g' .env

# 如果Identity Hub也迁移了，需要单独替换Identity Hub地址
# sed -i 's|IDENTITY_HUB_URL=.*|IDENTITY_HUB_URL=http://IDENTITY_HUB_IP:9000|' .env
```

**⚠️ 特别注意**: 还需要修改 `docker/docker-compose.yml` 中的 `FRONTEND_URL`

```bash
nano docker/docker-compose.yml

# 找到第18行，修改为：
environment:
  - BACKEND_PORT=8000
  - FRONTEND_URL=http://NEW_SERVER_IP:8080
```

**快速替换**:
```bash
sed -i 's/10.242.94.9/NEW_SERVER_IP/g' docker/docker-compose.yml
```

### 步骤3: 启动服务

```bash
# 进入docker目录
cd docker

# 构建Docker镜像
docker-compose build

# 启动容器（后台运行）
docker-compose up -d

# 查看启动日志
docker-compose logs -f
```

**预期日志输出**:
```
app_1       | 🚀 Starting application setup...
app_1       | [SYNC] Starting one-time data synchronization...
app_1       | [SUCCESS] Finished fetching all records. Total: 210
app_1       | ✅ Data sync finished successfully.
app_1       | Starting backend service...
app_1       | INFO:     Uvicorn running on http://0.0.0.0:8000
frontend_1  | (Nginx日志)
```

### 步骤4: 验证部署

```bash
# 检查容器状态
docker-compose ps
# 预期: 两个容器都为Up (healthy)

# 测试健康检查
curl http://localhost:8080/health

# 从外部访问测试（替换为实际IP）
curl http://NEW_SERVER_IP:8080
```

### 步骤5: 同步Identity Hub配置（⚠️ 必须操作）

在Identity Hub服务器上更新OAuth白名单：

```bash
# SSH登录到Identity Hub服务器
ssh user@IDENTITY_HUB_IP

# 进入Identity Hub容器
docker exec -it identity-hub bash

# 连接数据库
sqlite3 /app/data/identity-hub.db

-- 更新派工系统的回调地址白名单
UPDATE oauth_clients
SET redirect_uris='["http://NEW_SERVER_IP:8080/auth/callback", "http://localhost:8080/auth/callback", "http://NEW_SERVER_IP:3000/auth/callback", "http://localhost:3000/auth/callback"]'
WHERE client_id='task_feishu_dispatch_system';

-- 验证修改
SELECT client_id, redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system';

-- 退出
.quit
exit
```

---

## 🔧 配置说明

### 必须修改的配置项

| 配置项 | 文件 | 说明 | 示例 |
|--------|------|------|------|
| Identity Hub URL | `.env` | Identity Hub服务地址 | `http://192.168.1.200:9000` |
| OAuth回调地址 | `.env` | 派工系统回调地址 | `http://192.168.1.100:8080/auth/callback` |
| CORS来源 | `.env` | 允许访问的来源 | `http://192.168.1.100:8080,...` |
| 前端URL | `docker-compose.yml` | 登录成功后跳转地址 | `http://192.168.1.100:8080` |

### 飞书配置（无需修改）

`.env` 中的飞书配置通常不需要修改（除非更换了飞书应用）：
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_APP_TOKEN`
- `FEISHU_TABLE_ID`

---

## ✅ 部署验证清单

完成部署后，请逐项检查：

### 容器服务
- [ ] 后端容器状态为 `Up (healthy)`
- [ ] 前端容器状态为 `Up`
- [ ] 可以访问前端页面: `http://NEW_SERVER_IP:8080`
- [ ] 健康检查正常: `curl http://localhost:8080/health`

### 前端界面
- [ ] 页面正常加载，显示"派工管理系统"标题
- [ ] 显示"登录"按钮
- [ ] 显示周视图（周一到周五）
- [ ] 显示统计面板

### 身份认证
- [ ] 点击登录按钮跳转到Identity Hub
- [ ] OAuth参数中的redirect_uri是8080端口（不是3000）
- [ ] 飞书扫码登录成功
- [ ] 登录成功后跳转回派工系统（8080端口）
- [ ] 显示用户名和权限

### 数据同步
- [ ] 容器启动时自动同步飞书数据
- [ ] 任务数据正常显示
- [ ] 可以手动点击"同步数据"按钮

### Identity Hub对接
- [ ] Identity Hub的OAuth白名单已更新
- [ ] `.env`中的Identity Hub地址正确
- [ ] OAuth登录流程完整通过

---

## 🔍 故障排查

### 问题1: 容器无法启动

```bash
# 查看详细日志
docker-compose logs --tail=100 app

# 检查端口占用
sudo ss -tuln | grep 8080

# 检查.env文件
cat ../.env | grep -E "FEISHU|IDENTITY_HUB"
```

### 问题2: 前端显示404或无法加载

```bash
# 检查前端构建产物是否存在
ls -la ../frontend/build/

# 如果不存在，需要重新构建前端
cd ../frontend
npm install
npm run build

# 重新构建Docker镜像
cd ../docker
docker-compose build --no-cache frontend
docker-compose up -d
```

### 问题3: OAuth登录后跳转到3000端口

**原因**: `docker-compose.yml`中的`FRONTEND_URL`未修改

**解决**:
```bash
# 检查配置
grep FRONTEND_URL docker-compose.yml

# 修改为8080端口
sed -i 's|FRONTEND_URL=.*|FRONTEND_URL=http://NEW_SERVER_IP:8080|' docker-compose.yml

# 重启容器
docker-compose down
docker-compose up -d
```

### 问题4: OAuth登录失败

**常见原因**:
1. Identity Hub地址配置错误
2. Identity Hub的OAuth白名单未更新
3. 回调地址配置不一致

**排查步骤**:
```bash
# 1. 检查Identity Hub连通性
curl http://IDENTITY_HUB_IP:9000/health

# 2. 查看后端日志中的OAuth错误
docker logs docker_app_1 | grep -i oauth

# 3. 验证配置一致性
# 在派工系统服务器
grep IDENTITY_HUB_REDIRECT_URI ../.env

# 在Identity Hub服务器
docker exec identity-hub sqlite3 /app/data/identity-hub.db \
  "SELECT redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system';"

# 两者必须一致
```

### 问题5: 数据同步失败

```bash
# 查看同步日志
docker logs docker_app_1 | grep SYNC

# 检查飞书凭证
docker exec docker_app_1 printenv | grep FEISHU

# 手动触发同步
curl -X POST http://localhost:8080/api/sync
```

### 问题6: 数据库权限问题

```bash
# 检查数据库目录权限
ls -la ../data/db/

# 修复权限
sudo chown -R 1000:1000 ../data/db/
chmod 755 ../data/db/
chmod 644 ../data/db/tasks.db

# 重启容器
docker-compose restart
```

---

## 📊 运维命令

### 日常操作

```bash
# 进入docker目录
cd ~/task_feishu/docker

# 查看容器状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 查看后端日志
docker-compose logs -f app

# 查看前端日志
docker-compose logs -f frontend

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 启动服务
docker-compose up -d

# 查看资源使用
docker stats docker_app_1 docker_frontend_1 --no-stream
```

### 数据库操作

```bash
# 进入后端容器
docker exec -it docker_app_1 bash

# 查看数据库文件
ls -lh /app/db/

# 使用SQLite CLI
apt-get update && apt-get install -y sqlite3
sqlite3 /app/db/tasks.db

# 常用查询
SELECT COUNT(*) FROM tasks;                          -- 任务总数
SELECT COUNT(DISTINCT record_id) FROM tasks;         -- 记录数
SELECT date, COUNT(*) FROM tasks GROUP BY date;      -- 按日期统计
```

### 备份数据库

```bash
# 备份数据库
docker cp docker_app_1:/app/db/tasks.db \
  ~/task_feishu-backup-$(date +%Y%m%d).db

# 压缩备份
gzip ~/task_feishu-backup-*.db

# 定期备份脚本（每天凌晨2点）
cat > ~/backup-task-feishu.sh <<'EOF'
#!/bin/bash
BACKUP_DIR=~/task_feishu-backups
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p $BACKUP_DIR
docker cp docker_app_1:/app/db/tasks.db $BACKUP_DIR/tasks-$TIMESTAMP.db
gzip $BACKUP_DIR/tasks-$TIMESTAMP.db
find $BACKUP_DIR -name "tasks-*.db.gz" -mtime +30 -delete
echo "Backup completed: tasks-$TIMESTAMP.db.gz"
EOF
chmod +x ~/backup-task-feishu.sh

# 添加到crontab
crontab -e
# 添加: 0 2 * * * /home/user/backup-task-feishu.sh >> /home/user/backup.log 2>&1
```

### 手动数据同步

```bash
# 通过API触发同步
curl -X POST http://localhost:8080/api/sync

# 进入容器手动执行同步脚本
docker exec -it docker_app_1 bash
cd /app
python sync_once.py
```

---

## 🌐 端口和网络说明

### 端口映射

| 服务 | 容器内部端口 | 主机端口 | 说明 |
|------|-------------|---------|------|
| 后端FastAPI | 8000 | - | 不直接暴露，通过Nginx代理 |
| 前端Nginx | 80 | 8080 | 主要访问入口 |
| Identity Hub | - | 9000 | 外部依赖服务 |

### 访问地址

- **前端界面**: http://NEW_SERVER_IP:8080
- **API文档**: http://NEW_SERVER_IP:8080/docs
- **健康检查**: http://NEW_SERVER_IP:8080/health
- **OAuth登录**: 自动跳转到Identity Hub

### 网络架构

```
用户浏览器
    ↓
前端Nginx (8080)
    ├─ 静态文件 (/) → /usr/share/nginx/html/
    ├─ API (/api/*) → 后端 (8000)
    └─ OAuth (/auth/*) → 后端 (8000)
              ↓
        后端FastAPI (8000)
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
飞书API          Identity Hub (9000)
```

---

## 📚 完整文档

本快速指南仅包含基本部署步骤。完整功能和详细说明请参考：

- **docs/DOCKER_MIGRATION_GUIDE.md** - Docker环境完整迁移手册
- **docs/FRONTEND_URL_FIX_2025-11-04.md** - 前端URL配置问题修复记录
- **docs/PORT_ARCHITECTURE_EXPLANATION.md** - 开发/Docker环境端口架构对比

---

## 🔐 安全建议

### 生产环境配置

1. **更新API密钥**（强烈推荐）

```bash
# 生成新的API密钥
openssl rand -hex 32

# 更新.env文件
nano .env
# 修改 API_KEYS 和 READONLY_API_KEYS
```

2. **配置防火墙**

```bash
# 仅开放必要端口
sudo ufw allow 8080/tcp
sudo ufw enable
```

3. **添加HTTPS支持**（推荐）

可以在Nginx前加一层反向代理，使用Let's Encrypt证书。

4. **定期备份数据库**

使用上面提供的备份脚本，定期备份到安全位置。

---

## 🆘 获取帮助

如遇到问题，请按以下顺序排查：

1. **查看日志**: `docker-compose logs -f app`
2. **检查配置**: 确认`.env`和`docker-compose.yml`中所有IP地址已正确替换
3. **参考完整手册**: `docs/DOCKER_MIGRATION_GUIDE.md`
4. **验证环境**:
   - Docker版本 >= 20.10
   - Docker Compose版本 >= 1.29
   - 端口8080未被占用
   - Identity Hub可访问

---

## 🎯 下一步

部署完成后：

1. **测试OAuth登录**: 完整测试从登录到退出的流程
2. **测试数据同步**: 点击"同步数据"按钮，验证飞书数据同步
3. **测试用户管理**: 登录后访问用户管理页面（如果有权限）
4. **测试派工管理**: 创建、修改、转交派工（如果有权限）
5. **配置定期备份**: 使用上面提供的备份脚本
6. **配置监控**: 设置健康检查告警（可选）

---

## 📝 版本信息

- **系统版本**: v1.0
- **前端构建时间**: 2025-11-04
- **Docker配置版本**: 2025-11-04
- **支持的功能**:
  - ✅ OAuth 2.0登录（Identity Hub）
  - ✅ 用户和角色管理
  - ✅ 派工管理（创建、修改、转交、完成、关闭）
  - ✅ 飞书数据自动同步
  - ✅ 周视图/月视图
  - ✅ 任务筛选和统计

---

**部署完成！** 🎉

飞书派工系统现在已经在Docker环境中运行，可以通过 `http://NEW_SERVER_IP:8080` 访问。

记得在Identity Hub中更新OAuth白名单，并测试完整的登录流程！
