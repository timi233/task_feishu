# Phase 3 快速启动指南

**目标**: 启动并测试Identity Hub与派工系统的OAuth集成

---

## 🚀 快速启动

### 第1步: 启动Identity Hub（终端1）

```bash
# 进入Identity Hub目录
cd /home/jian/code/identity-hub

# 启动服务器
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**验证**:
- 访问 http://10.242.94.9:8000/health
- 访问 http://10.242.94.9:8000/docs（API文档）

---

### 第2步: 启动派工系统后端（终端2）

```bash
# 进入派工系统后端目录
cd /home/jian/code/Task_feishu/backend

# 启动服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

**验证**:
- 访问 http://10.242.94.9:8080/health
- 访问 http://10.242.94.9:8080/auth/status

---

### 第3步: 启动派工系统前端（终端3）

```bash
# 进入派工系统前端目录
cd /home/jian/code/Task_feishu/frontend

# 启动开发服务器
npm start
```

**验证**:
- 自动打开浏览器 http://localhost:3000
- 或手动访问 http://10.242.94.9:3000

---

## 🧪 测试OAuth登录

### 1. 打开派工系统

访问: http://10.242.94.9:3000

### 2. 查看Header右上角

应该看到"登录"按钮（如果Identity Hub可用）

### 3. 点击"登录"

- 应该跳转到Identity Hub
- URL类似: `http://10.242.94.9:8000/oauth/authorize?client_id=task_feishu_dispatch_system&...`

### 4. 自动授权

- Identity Hub自动授权（信任应用）
- 自动重定向回派工系统: `http://10.242.94.9:8080/auth/callback?code=xxx&state=xxx`

### 5. 验证登录成功

- Header应显示: `👤 张健 | 登出`
- 浏览器应有`session_id` Cookie

### 6. 测试登出

- 点击"登出"按钮
- 应该恢复到未登录状态

---

## 🔍 调试技巧

### 查看后端日志

**Identity Hub**:
```bash
# 终端1应该显示OAuth请求日志
# 例如:
# INFO: Generated authorization URL (state=xxx...)
# INFO: ✅ User logged in: 张健 (b1fe8eb1...)
```

**派工系统**:
```bash
# 终端2应该显示认证日志
# 例如:
# INFO: Initialized IdentityHubClient: http://10.242.94.9:8000
# INFO: ✅ User logged in: 张健 (b1fe8eb1...)
```

### 检查浏览器Cookie

打开浏览器开发者工具 → Application → Cookies → http://10.242.94.9:3000

应该看到:
- `session_id`: 长字符串（如果已登录）

### 测试认证API

```bash
# 检查认证状态（需要先在浏览器登录并复制Cookie）
curl http://10.242.94.9:8080/auth/status

# 应该返回:
{
  "authenticated": true,
  "user_name": "张健",
  "identity_hub_available": true
}
```

---

## ⚠️ 常见问题

### 问题1: 看不到"登录"按钮

**原因**: Identity Hub未启动或不可用

**解决**:
```bash
# 检查Identity Hub
curl http://10.242.94.9:8000/health

# 如果失败,启动Identity Hub
cd /home/jian/code/identity-hub
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 问题2: 点击登录后跳转失败

**原因**: 环境变量未配置

**解决**:
```bash
# 检查派工系统环境变量
cd /home/jian/code/Task_feishu
cat backend/.env | grep IDENTITY_HUB

# 应该看到:
# IDENTITY_HUB_URL=http://10.242.94.9:8000
# IDENTITY_HUB_CLIENT_ID=task_feishu_dispatch_system
# IDENTITY_HUB_CLIENT_SECRET=xxx
```

### 问题3: OAuth回调失败

**原因**: redirect_uri不匹配

**解决**:
```bash
# 检查OAuth客户端配置
cd /home/jian/code/identity-hub
sqlite3 data/identity-hub.db "SELECT redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system'"

# 应该包含: http://10.242.94.9:8080/auth/callback
```

---

## 📊 完整测试清单

- [ ] Identity Hub启动成功
- [ ] 派工系统后端启动成功
- [ ] 派工系统前端启动成功
- [ ] 页面显示"登录"按钮
- [ ] 点击登录跳转到Identity Hub
- [ ] 自动授权并跳转回派工系统
- [ ] 显示用户名"👤 张健"
- [ ] 刷新页面后仍保持登录状态
- [ ] 点击登出成功
- [ ] 登出后恢复未登录状态

---

## 🎯 成功标准

所有上述测试清单都打✅，即表示Phase 3集成成功！

---

## 📝 下一步

Phase 3测试通过后，可以进入Phase 4：管理后台开发。

或者先完善Phase 3的高级功能：
- Token自动刷新
- 基于用户的数据过滤
- 审计日志记录
- Redis Session存储

---

**预计测试时间**: 15-30分钟
**测试难度**: ⭐⭐☆☆☆（简单）
