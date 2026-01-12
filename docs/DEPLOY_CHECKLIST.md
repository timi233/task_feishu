# 外部设备部署检查清单

## 📦 打包传输清单

### 必须文件/目录
- [x] `backend/` - 后端代码目录
- [x] `frontend/` - 前端代码目录
- [x] `dd/` - Docker配置目录
- [x] `docs/` - 文档目录
- [x] `docker-compose.yml` - Docker编排文件
- [x] `Dockerfile` - 后端镜像构建文件
- [x] `.env.example` - 环境变量示例
- [x] `deploy.sh` - 自动部署脚本
- [x] `pre-deploy-check.sh` - 预检脚本
- [x] `README_DEPLOY.md` - 快速部署指南

### 不要传输的文件/目录
- [ ] `data/` - 本地数据库(会在目标服务器重新生成)
- [ ] `backend/__pycache__/` - Python缓存
- [ ] `frontend/node_modules/` - Node依赖(会重新安装)
- [ ] `frontend/build/` - 前端构建产物(会重新构建)
- [ ] `.env` - 本地环境变量(含敏感信息,不要传输)
- [ ] `.git/` - Git历史(可选)

---

## 🚀 部署步骤

### 方式一: 自动部署(推荐)

```bash
# 1. 检查环境
./pre-deploy-check.sh

# 2. 配置环境变量
cp .env.example .env
nano .env  # 填写真实的飞书凭证和API密钥

# 3. 一键部署
./deploy.sh
```

### 方式二: 手动部署

```bash
# 1. 配置环境变量
cp .env.example .env
nano .env

# 2. 创建数据目录
mkdir -p data/db

# 3. 构建并启动
docker-compose up -d --build

# 4. 验证
curl http://localhost:8000/health
```

---

## ✅ 部署后验证清单

### 基础检查
- [ ] 容器状态正常: `docker-compose ps` 显示所有服务 "Up"
- [ ] 后端健康检查通过: `curl http://localhost:8000/health` 返回 "healthy"
- [ ] 前端可访问: 浏览器打开 `http://服务器IP:8080` 显示界面
- [ ] API文档可访问: `http://服务器IP:8000/docs` 显示Swagger UI

### 功能检查
- [ ] **自动同步功能**: 打开页面时自动同步一次数据
- [ ] **自动同步控制**: 页头显示自动同步开关和倒计时
- [ ] **定时同步**: 每小时自动同步一次(如已开启)
- [ ] **手动同步**: 点击"同步数据"按钮,显示"同步成功"提示
- [ ] 同步后页面显示任务数据
- [ ] 切换周视图可以正常显示不同周的数据
- [ ] 切换"按日期视图"和"按工程师视图"正常工作

### API检查
```bash
# 测试健康检查
curl http://localhost:8000/health

# 测试工程师列表
curl -H "X-API-Key: your-readonly-key" http://localhost:8000/api/engineers

# 测试手动同步
curl -X POST -H "X-API-Key: your-readonly-key" http://localhost:8000/api/sync
```

### 数据持久化检查
```bash
# 重启容器
docker-compose restart

# 验证数据未丢失
curl http://localhost:8000/health  # task_count应该>0
```

---

## 🔐 安全配置清单

### 必须修改的配置
- [ ] `.env` 中的 `API_KEYS` 已替换为强密码
- [ ] `.env` 中的 `READONLY_API_KEYS` 已替换为强密码
- [ ] `.env` 中的 `ALLOWED_ORIGINS` 已改为实际访问地址

### 推荐配置
- [ ] 配置防火墙,仅开放8000和8080端口
- [ ] 如果对外提供服务,配置Nginx反向代理
- [ ] 启用HTTPS (使用Let's Encrypt免费证书)
- [ ] 设置数据库定期备份(cron任务)

---

## 📊 监控检查清单

### 日常监控
- [ ] 每日检查容器状态: `docker-compose ps`
- [ ] 每周检查磁盘空间: `df -h`
- [ ] 每周检查数据库大小: `du -sh data/db/tasks.db`

### 日志查看
```bash
# 查看实时日志
docker-compose logs -f

# 查看最近100行
docker-compose logs --tail=100

# 仅查看后端日志
docker-compose logs -f app

# 仅查看前端日志
docker-compose logs -f frontend
```

---

## 🆘 问题排查清单

### 服务无法启动
- [ ] 检查端口是否被占用: `lsof -i:8000` 和 `lsof -i:8080`
- [ ] 检查Docker服务是否运行: `docker info`
- [ ] 查看容器日志: `docker-compose logs`
- [ ] 检查.env文件是否存在且配置正确

### 前端无法连接后端
- [ ] 检查CORS配置: `.env` 中的 `ALLOWED_ORIGINS`
- [ ] 检查后端是否运行: `curl http://localhost:8000/health`
- [ ] 检查防火墙: `sudo ufw status`

### 数据同步失败
- [ ] 验证飞书凭证: 手动运行 `python backend/sync_once.py`
- [ ] 检查网络连接: `ping open.feishu.cn`
- [ ] 查看详细错误日志: `docker-compose logs app`

### 数据库问题
- [ ] 检查data目录权限: `ls -la data/db/`
- [ ] 检查数据库文件: `sqlite3 data/db/tasks.db ".tables"`
- [ ] 如有损坏,从备份恢复: `cp backup/tasks_backup.db data/db/tasks.db`

---

## 📁 备份恢复清单

### 备份内容
- [ ] 数据库文件: `data/db/tasks.db`
- [ ] 环境配置: `.env` (注意安全存储)
- [ ] 筛选器配置: `backend/filter_config.json`

### 自动备份配置
```bash
# 添加到crontab
crontab -e

# 每天凌晨2点备份
0 2 * * * /path/to/Task_feishu/backup_script.sh
```

### 恢复步骤
```bash
# 1. 停止服务
docker-compose down

# 2. 恢复数据库
cp backup/tasks_YYYYMMDD.db data/db/tasks.db

# 3. 启动服务
docker-compose up -d
```

---

## 📞 联系支持

如遇到无法解决的问题:

1. 收集日志: `docker-compose logs > debug.log`
2. 记录错误信息
3. 联系系统管理员

---

## 📚 文档索引

- **快速开始**: `README_DEPLOY.md`
- **详细部署**: `docs/DEPLOYMENT_GUIDE.md`
- **API文档**: `docs/API_USAGE_GUIDE.md`
- **项目说明**: `CLAUDE.md`
