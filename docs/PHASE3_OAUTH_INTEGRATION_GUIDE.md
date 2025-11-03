# Phase 3: OAuth集成测试指南

**日期**: 2025-10-30
**目标**: 测试派工系统与Identity Hub的OAuth集成

---

## ✅ 完成的工作

### 后端集成
- ✅ 创建派工系统OAuth客户端（client_id: task_feishu_dispatch_system）
- ✅ 实现认证客户端（auth_identity_hub.py）
- ✅ 创建Session管理模块（session_manager.py）
- ✅ 添加认证路由（/auth/login, /auth/callback, /auth/logout, /auth/user, /auth/status）
- ✅ 实现认证中间件（可选认证，保持API Key兼容）
- ✅ 修改main.py集成OAuth

### 前端集成
- ✅ 创建LoginButton组件（显示登录/登出按钮）
- ✅ 创建AuthCallback组件（处理OAuth回调）
- ✅ 修改Header组件（添加登录按钮）

---

## 🧪 测试流程

### 前置条件

1. **Identity Hub运行中**
   ```bash
   cd /home/jian/code/identity-hub
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

2. **用户已同步**
   ```bash
   python backend/sync/sync_manager.py
   ```

### 测试步骤

#### 1. 启动派工系统

```bash
# 后端
cd /home/jian/code/Task_feishu/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8080

# 前端（另一个终端）
cd /home/jian/code/Task_feishu/frontend
npm start
```

#### 2. 访问派工系统

打开浏览器访问: http://10.242.94.9:3000

#### 3. 测试登录流程

1. **点击"登录"按钮**
   - 应该跳转到Identity Hub授权页面
   - URL: `http://10.242.94.9:8000/oauth/authorize?client_id=task_feishu_dispatch_system&...`

2. **自动授权（信任应用）**
   - Identity Hub应自动重定向回派工系统
   - URL: `http://10.242.94.9:8080/auth/callback?code=xxx&state=xxx`

3. **回调处理**
   - 派工系统后端用授权码换取token
   - 创建session并存储用户信息
   - 重定向回原页面

4. **验证登录状态**
   - 登录按钮应变为"👤 [用户名] | 登出"
   - 浏览器应有session_id cookie

#### 4. 测试认证状态API

```bash
# 检查认证状态
curl -b cookies.txt http://10.242.94.9:8080/auth/status

# 获取当前用户
curl -b cookies.txt http://10.242.94.9:8080/auth/user
```

#### 5. 测试登出

1. 点击"登出"按钮
2. Session应被清除
3. 登录按钮应重新显示

---

## 🔍 调试指南

### 查看日志

**Identity Hub日志**:
```bash
cd /home/jian/code/identity-hub
tail -f identity-hub.log
```

**派工系统后端日志**:
```bash
# 查看uvicorn输出
```

### 常见问题

#### 问题1: 点击登录无反应

**可能原因**:
- Identity Hub未启动
- 环境变量未配置

**解决方法**:
```bash
# 检查Identity Hub
curl http://10.242.94.9:8000/health

# 检查环境变量
cd /home/jian/code/Task_feishu
cat backend/.env | grep IDENTITY_HUB
```

#### 问题2: OAuth回调失败

**可能原因**:
- redirect_uri不匹配
- state验证失败

**解决方法**:
```bash
# 检查OAuth客户端配置
cd /home/jian/code/identity-hub
sqlite3 data/identity-hub.db "SELECT client_id, redirect_uris FROM oauth_clients WHERE client_id='task_feishu_dispatch_system'"
```

#### 问题3: Session丢失

**可能原因**:
- Cookie未设置
- Session过期

**解决方法**:
```bash
# 检查浏览器Cookie
# 应该有session_id cookie

# 检查Session管理器状态
# 在派工系统后端代码中添加日志
```

---

## 📊 验证清单

- [ ] 点击登录按钮能跳转到Identity Hub
- [ ] Identity Hub自动授权并重定向回派工系统
- [ ] 回调处理成功，显示用户名
- [ ] 刷新页面后仍保持登录状态
- [ ] 点击登出能成功登出
- [ ] 登出后刷新页面不再显示用户信息

---

## 🔧 配置文件

### 派工系统 .env
```bash
# Identity Hub OAuth配置
IDENTITY_HUB_URL=http://10.242.94.9:8000
IDENTITY_HUB_CLIENT_ID=task_feishu_dispatch_system
IDENTITY_HUB_CLIENT_SECRET=1e4ngu17g3Fk6_IkjH7Fbx8IGBT0U9aufGq2kQkOOX8
IDENTITY_HUB_REDIRECT_URI=http://10.242.94.9:8080/auth/callback
```

### Identity Hub数据库
```sql
-- OAuth客户端
SELECT * FROM oauth_clients WHERE client_id='task_feishu_dispatch_system';

-- 用户
SELECT user_id, name, email FROM users WHERE is_admin=1;
```

---

## 🎯 成功标准

OAuth集成成功的标准：

1. ✅ 用户可以通过Identity Hub登录
2. ✅ 登录状态在session中持久化
3. ✅ 用户信息正确显示
4. ✅ 登出功能正常工作
5. ✅ 原有API Key认证仍然兼容
6. ✅ 不影响现有功能

---

## 📝 后续工作

- [ ] 添加基于用户身份的权限过滤（只能看自己的任务）
- [ ] 记录审计日志
- [ ] 实现Token自动刷新
- [ ] 生产环境使用Redis存储Session

---

**测试负责人**: Claude
**预计测试时间**: 30分钟
**报告更新**: 测试完成后
