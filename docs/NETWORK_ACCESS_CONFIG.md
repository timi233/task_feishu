# 网络访问配置指南

**更新日期**: 2025-10-22
**目标IP**: `10.242.94.9`

---

## 📡 访问地址

### ✅ 通过IP地址访问 (推荐)

```
前端界面: http://10.242.94.9:8080
后端API:  http://10.242.94.9:8000
```

### 🔄 通过localhost访问 (仅本机)

```
前端界面: http://localhost:8080
后端API:  http://localhost:8000
```

---

## 🏗️ 系统架构

```
浏览器 (http://10.242.94.9:8080)
   ↓
Nginx (端口8080)
   ├─→ 静态文件: /usr/share/nginx/html
   └─→ API代理: /api/* → http://app:8000
         ↓
   FastAPI后端 (端口8000)
         ↓
   SQLite数据库 + 飞书API
```

**关键特性**:
- ✅ Nginx自动反向代理API请求
- ✅ 前端无需配置后端地址
- ✅ 统一通过8080端口访问

---

## 🔧 端口配置

| 服务 | 容器端口 | 主机端口 | 绑定地址 | 状态 |
|------|---------|---------|---------|------|
| **前端 (Nginx)** | 80 | **8080** | 0.0.0.0 | ✅ 运行中 |
| **后端 (FastAPI)** | 8000 | **8000** | 0.0.0.0 | ✅ 运行中 |
| **MySQL** | - | 3306 | 0.0.0.0 | ✅ 运行中 |

**说明**:
- `0.0.0.0` 绑定表示可从任何IP访问
- 8080端口避免与系统80端口冲突
- 8000端口直接暴露用于API调试

---

## 🌐 CORS配置

**允许的来源** (`.env`):
```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,http://10.242.94.9:8080,http://10.242.94.9:3000
```

**说明**:
- ✅ 已添加 `http://10.242.94.9:8080` 到白名单
- ✅ 支持前端开发服务器 (3000端口)
- ✅ 支持生产环境 (8080端口)

---

## 🚀 启动服务

### 使用Docker Compose (推荐)

```bash
# 1. 进入项目目录
cd /home/jian/code/Task_feishu

# 2. 启动所有服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f
```

### 重启服务

```bash
# 重启后端(应用CORS配置)
docker-compose restart app

# 重启前端
docker-compose restart frontend

# 重启所有服务
docker-compose restart
```

### 停止服务

```bash
docker-compose down
```

---

## 🧪 测试访问

### 1. 测试前端访问

在浏览器打开:
```
http://10.242.94.9:8080
```

**预期结果**: 看到派工管理系统首页

### 2. 测试后端API

```bash
# 测试健康检查
curl http://10.242.94.9:8000/health

# 测试API文档
curl http://10.242.94.9:8000/docs
```

**预期结果**: 返回健康状态或重定向到文档页面

### 3. 测试API代理

在浏览器控制台:
```javascript
fetch('http://10.242.94.9:8080/api/tasks')
  .then(r => r.json())
  .then(d => console.log('任务数据:', d))
```

**预期结果**: 返回任务列表数据

---

## 🔍 故障排查

### 问题1: 无法通过10.242.94.9访问

**检查步骤**:

1. **确认IP地址正确**
   ```bash
   ip addr show | grep "inet 10.242.94.9"
   ```

2. **确认服务运行**
   ```bash
   docker-compose ps
   # 应显示 Up (healthy)
   ```

3. **确认端口监听**
   ```bash
   ss -tuln | grep -E ":(8000|8080)"
   # 应显示 0.0.0.0:8000 和 0.0.0.0:8080
   ```

4. **检查防火墙**
   ```bash
   sudo ufw status
   # 如果启用,需要允许8000和8080端口
   sudo ufw allow 8080/tcp
   sudo ufw allow 8000/tcp
   ```

### 问题2: CORS错误

**错误信息**:
```
Access to fetch at 'http://10.242.94.9:8000/api/xxx' from origin 'http://10.242.94.9:8080'
has been blocked by CORS policy
```

**解决方案**:

1. **检查.env配置**
   ```bash
   cat .env | grep ALLOWED_ORIGINS
   ```
   确保包含: `http://10.242.94.9:8080`

2. **重启后端服务**
   ```bash
   docker-compose restart app
   ```

3. **清除浏览器缓存**
   - 按 Ctrl+Shift+R 强制刷新
   - 或清除浏览器缓存

### 问题3: 前端白屏

**检查步骤**:

1. **查看浏览器控制台错误**
   - 按 F12 打开开发者工具
   - 查看Console和Network标签

2. **检查Nginx日志**
   ```bash
   docker-compose logs frontend
   ```

3. **检查前端构建**
   ```bash
   ls -la frontend/build/
   # 应该有index.html和static目录
   ```

### 问题4: API请求失败

**检查步骤**:

1. **查看后端日志**
   ```bash
   docker-compose logs app | tail -50
   ```

2. **测试直接访问后端**
   ```bash
   curl http://10.242.94.9:8000/health
   ```

3. **检查API Key**
   ```bash
   # 前端默认使用的API Key
   grep "API_KEY" frontend/src/utils/api.js
   ```

---

## 📝 配置文件位置

| 配置项 | 文件路径 | 说明 |
|--------|---------|------|
| **环境变量** | `.env` | 飞书凭证、CORS配置 |
| **Docker配置** | `docker-compose.yml` | 端口映射、挂载卷 |
| **Nginx配置** | `dd/nginx.frontend.conf` | 反向代理规则 |
| **后端启动** | `start.sh` | uvicorn启动参数 |
| **前端API配置** | `frontend/src/utils/api.js` | API_BASE_URL |

---

## 🔐 安全建议

### 生产环境配置

1. **修改默认API Key**
   ```bash
   # 编辑 .env
   API_KEYS=your-strong-admin-key-here
   READONLY_API_KEYS=your-strong-readonly-key-here
   ```

2. **限制CORS来源**
   ```bash
   # 只允许特定IP
   ALLOWED_ORIGINS=http://10.242.94.9:8080
   ```

3. **启用HTTPS** (可选)
   - 配置Nginx SSL证书
   - 修改ALLOWED_ORIGINS为https://

4. **限制数据库访问**
   - SQLite文件权限: `chmod 600 data/db/tasks.db`
   - MySQL绑定到127.0.0.1而非0.0.0.0

---

## 📞 常用命令速查

```bash
# === 服务管理 ===
docker-compose up -d          # 启动服务
docker-compose down           # 停止服务
docker-compose restart        # 重启所有服务
docker-compose restart app    # 仅重启后端

# === 状态查看 ===
docker-compose ps             # 查看容器状态
docker-compose logs -f        # 实时查看日志
docker-compose logs app       # 查看后端日志
docker-compose logs frontend  # 查看前端日志

# === 数据库管理 ===
python backend/migrations/add_engineers_table.py  # 运行迁移
python backend/check_db.py                         # 查看数据库
sqlite3 data/db/tasks.db                           # 直接操作数据库

# === 数据同步 ===
python backend/sync_once.py                        # 手动同步一次
curl -X POST http://10.242.94.9:8000/api/sync \
  -H "X-API-Key: readonly-key-for-hr-system"      # API触发同步

# === 端口检查 ===
ss -tuln | grep -E ":(8000|8080|3306)"            # 查看端口监听
lsof -i :8080                                      # 查看端口占用
```

---

## ✅ 验证清单

部署完成后,请逐项验证:

- [ ] 访问 `http://10.242.94.9:8080` 看到派工系统首页
- [ ] Header显示"新建派工"和"工单管理"按钮
- [ ] 点击"同步数据"成功同步飞书数据
- [ ] 工程师选择器显示下拉联想列表
- [ ] 新建派工表单提交成功
- [ ] 工单管理面板可以打开
- [ ] API文档可访问: `http://10.242.94.9:8000/docs`
- [ ] 数据库迁移已执行
- [ ] 工程师数据已同步

---

**配置状态**: ✅ **已完成,可通过 `10.242.94.9` 访问**
**最后更新**: 2025-10-22
**维护人员**: Claude Code
