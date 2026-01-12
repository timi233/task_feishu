# 快速部署指南

本文档提供最快速的部署流程,适合初次部署用户。

---

## 一分钟快速部署

### 前提条件
- 已安装 Docker 和 Docker Compose
- 有外网访问权限(访问飞书API)

### 步骤

#### 1. 获取项目文件

将整个 `Task_feishu` 文件夹复制到目标服务器:

```bash
# 方式A: 使用scp传输
scp -r Task_feishu user@your-server:/home/user/

# 方式B: 使用git
git clone <repository_url> Task_feishu

# 方式C: 手动上传(使用FTP/SFTP工具)
```

#### 2. 进入项目目录

```bash
cd Task_feishu
```

#### 3. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
nano .env
```

**最少需要修改以下内容:**

```bash
# 飞书凭证(从飞书开放平台获取)
FEISHU_APP_ID=你的APP_ID
FEISHU_APP_SECRET=你的APP_SECRET
FEISHU_APP_TOKEN=你的APP_TOKEN
FEISHU_TABLE_ID=你的TABLE_ID

# API密钥(请自行生成强密码)
API_KEYS=你的管理员密钥
READONLY_API_KEYS=你的只读密钥

# 访问来源(改为你的服务器IP)
ALLOWED_ORIGINS=http://你的服务器IP:8080
```

#### 4. 运行部署脚本

```bash
chmod +x deploy.sh
./deploy.sh
```

脚本会自动:
- ✅ 检查环境
- ✅ 创建数据目录
- ✅ 构建Docker镜像
- ✅ 启动服务
- ✅ 验证部署

#### 5. 访问系统

部署成功后,在浏览器访问:

```
http://你的服务器IP:8080
```

---

## 手动部署(一步步执行)

如果自动脚本失败,可以手动执行:

```bash
# 1. 创建数据目录
mkdir -p data/db

# 2. 启动服务
docker-compose up -d --build

# 3. 查看日志
docker-compose logs -f

# 4. 验证健康
curl http://localhost:8000/health
```

---

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 重新部署
docker-compose down
docker-compose up -d --build --force-recreate
```

---

## 获取飞书凭证

### 1. FEISHU_APP_ID 和 FEISHU_APP_SECRET

1. 访问 https://open.feishu.cn/app
2. 选择你的应用
3. 在"凭证与基础信息"页面找到:
   - App ID
   - App Secret

### 2. FEISHU_APP_TOKEN

1. 打开飞书多维表格
2. 从URL获取: `https://xxx.feishu.cn/base/<APP_TOKEN>`
3. `<APP_TOKEN>` 就是你需要的值

### 3. FEISHU_TABLE_ID

1. 在多维表格中选择具体的表
2. 从URL获取: `https://xxx.feishu.cn/base/xxx?table=<TABLE_ID>`
3. `<TABLE_ID>` 就是你需要的值

---

## 生成API密钥

推荐使用强密码生成器生成32位随机字符串:

```bash
# Linux/Mac
openssl rand -base64 32

# 或在线工具
# https://passwordsgenerator.net/
```

---

## 端口说明

| 端口 | 服务 | 用途 |
|------|------|------|
| 8000 | 后端API | FastAPI服务 |
| 8080 | 前端界面 | Nginx托管的React应用 |

**防火墙配置**:
```bash
# 开放必要端口
sudo ufw allow 8000/tcp
sudo ufw allow 8080/tcp
```

---

## 验证部署

### 1. 检查后端健康

```bash
curl http://localhost:8000/health
```

预期响应:
```json
{
  "status": "healthy",
  "database": "connected",
  "task_count": 0,
  "timestamp": "2025-10-20T10:30:00.123456"
}
```

### 2. 访问API文档

浏览器打开: `http://你的服务器IP:8000/docs`

### 3. 测试数据同步

```bash
curl -X POST \
  -H "X-API-Key: 你的API密钥" \
  http://localhost:8000/api/sync
```

### 4. 访问前端

浏览器打开: `http://你的服务器IP:8080`

**自动同步功能**:
- ✅ 页面打开时会自动同步一次数据
- ✅ 之后每隔1小时自动同步一次
- ✅ 可通过页头的复选框开启/关闭自动同步
- ✅ 显示下次同步的倒计时
- ✅ 也可随时点击"同步数据"按钮手动同步

---

## 常见问题速查

| 问题 | 解决方案 |
|------|----------|
| 端口被占用 | 修改 `docker-compose.yml` 中的端口映射 |
| 前端无法连接后端 | 检查 `.env` 中的 `ALLOWED_ORIGINS` |
| 数据同步失败 | 验证飞书凭证是否正确 |
| 容器启动失败 | 查看日志: `docker-compose logs` |

---

## 更新系统

```bash
# 拉取最新代码(如使用git)
git pull

# 重新部署
./deploy.sh
```

---

## 卸载

```bash
# 停止并删除容器
docker-compose down

# 删除数据(可选)
rm -rf data/

# 删除镜像(可选)
docker rmi task_feishu_app task_feishu_frontend
```

---

## 需要帮助?

- **详细文档**: `docs/DEPLOYMENT_GUIDE.md`
- **API文档**: `docs/API_USAGE_GUIDE.md`
- **问题排查**: 查看容器日志 `docker-compose logs -f`

---

**部署检查清单**:

- [ ] Docker和Docker Compose已安装
- [ ] 已创建 `.env` 文件
- [ ] 已配置飞书凭证(APP_ID, APP_SECRET, APP_TOKEN, TABLE_ID)
- [ ] 已生成并配置API密钥
- [ ] 已配置ALLOWED_ORIGINS为服务器IP
- [ ] 执行 `./deploy.sh` 成功
- [ ] 访问 http://服务器IP:8080 可以看到界面
- [ ] 点击"同步数据"按钮可以成功同步
