# 登录功能问题解决记录

**日期**: 2025-11-03
**问题**: 飞书派工系统OAuth登录功能无法正常工作
**状态**: ✅ 已解决

## 问题描述

用户点击登录按钮后，能够成功跳转到Identity Hub并完成飞书扫码授权，但在OAuth回调阶段失败，错误信息为"Invalid or expired session"。

## 问题症状

1. ✅ 前端登录按钮正常显示
2. ✅ 点击后成功跳转到Identity Hub (http://10.242.94.9:9000)
3. ✅ Identity Hub飞书扫码登录成功
4. ✅ Identity Hub OAuth授权成功
5. ❌ 后端callback处理失败："Invalid or expired session"
6. ❌ 无法跳转回前端首页并显示用户信息

## 根本原因

### 主要问题：Cookie命名冲突

后端和Identity Hub都使用了相同的cookie名称`session_id`，导致cookie覆盖：

**完整流程分析**：

```
1. 用户点击"登录" → 后端 /auth/login
   后端创建session: MQ6Tvjop_MHOLUuu...
   设置cookie: session_id=MQ6Tvjop_MHOLUuu...
   重定向到: Identity Hub /oauth/authorize

2. Identity Hub检查用户未登录 → 重定向到 /login
   Identity Hub创建session: aINZWJ6HFjF5w2yX...
   设置cookie: session_id=aINZWJ6HFjF5w2yX...  ← 覆盖了后端的cookie！

3. 用户飞书扫码 → Identity Hub /callback
   Identity Hub使用自己的session验证成功
   重定向到: /oauth/authorize (已登录)

4. OAuth授权 → 重定向回后端 /auth/callback
   后端读取cookie: session_id=aINZWJ6HFjF5w2yX (Identity Hub的)
   后端查找session: MQ6Tvjop_MHOLUuu... (自己创建的)
   结果: ❌ session不匹配 → "Invalid or expired session"
```

**日志证据**：
```
后端日志:
2025-11-03 13:32:08 - session_manager - INFO - Created session: MQ6Tvjop_MHOLUuu...
2025-11-03 13:32:13 - auth_routes - INFO - Callback received: session_id=aINZWJ6HFjF5w2yX...
2025-11-03 13:32:13 - auth_routes - ERROR - Invalid or expired session: session_id=aINZWJ6HFjF5w2yX
```

### 次要问题：OAuth `next`参数URL编码

在Identity Hub OAuth端点中，`next`参数未正确URL编码，导致包含查询字符串的URL被截断。

**问题代码** (`backend/oauth/endpoints.py:213`):
```python
# 未编码，导致FastAPI把&后的内容当作独立参数
return RedirectResponse(url=f"/login?next={current_url}")

# 当current_url = "/oauth/authorize?client_id=...&redirect_uri=..."
# FastAPI解析为: next="/oauth/authorize?client_id=..." (被截断)
```

## 解决方案

### 方案1: 修改后端Cookie名称（已采用）

**修改文件**: `backend/auth_routes.py`
**修改内容**: 将所有`session_id` cookie重命名为`task_session_id` (共7处)

```python
# /auth/login - 设置cookie
response.set_cookie(
    key="task_session_id",  # 原: session_id
    value=session_id,
    httponly=True,
    max_age=7200,
    samesite="lax",
    path="/"
)

# /auth/callback - 读取cookie
session_id = request.cookies.get("task_session_id")  # 原: session_id

# /auth/logout - 删除cookie
response.delete_cookie(key="task_session_id")  # 原: session_id

# /auth/user - 读取cookie
session_id = request.cookies.get("task_session_id")  # 原: session_id

# /auth/status - 读取cookie
session_id = request.cookies.get("task_session_id")  # 原: session_id
```

### 方案2: 修复OAuth `next`参数URL编码

**修改文件**: `backend/oauth/endpoints.py`

```python
# 添加导入
from urllib.parse import urlencode, quote

# 修改重定向逻辑 (line 214)
# 修改前
return RedirectResponse(url=f"/login?next={current_url}")

# 修改后
return RedirectResponse(url=f"/login?next={quote(current_url, safe='')}")
```

### 方案3: 修复前端登录按钮URL（已在之前修复）

**修改文件**: `frontend/src/components/LoginButton.js`

```javascript
// 修改前（使用相对路径，window.location.href不会被proxy拦截）
window.location.href = `/auth/login?return_url=${returnUrl}`;

// 修改后（使用完整后端URL）
const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://10.242.94.9:8081';
window.location.href = `${backendUrl}/auth/login?return_url=${returnUrl}`;
```

### 方案4: 修复Identity Hub用户创建（已在之前修复）

**修改文件**: `identity-hub/backend/auth_routes.py`

```python
# 添加缺失的source_id和source_user_id字段
INSERT INTO users (user_id, source_id, source_user_id, name, email, mobile, status)
VALUES (?, ?, ?, ?, ?, ?, 1)
```

## 验证结果

### 成功日志

```
Identity Hub日志:
2025-11-03 13:47:31,565 - auth_routes - INFO - ✅ User logged in: 张健 (ou_ad883f9af7460763443f4b8b234e25b2)
2025-11-03 13:47:31,608 - oauth.server - INFO - ✅ Created authorization code for user=ou_ad883f9af7460763443f4b8b234e25b2
2025-11-03 13:47:31,608 - oauth.endpoints - INFO - ✅ Authorization granted, redirecting to backend
2025-11-03 13:47:31,649 - oauth.server - INFO - ✅ Issued tokens for user=ou_ad883f9af7460763443f4b8b234e25b2
2025-11-03 13:47:31,667 - backend.main - INFO - GET /oauth/userinfo - 200
2025-11-03 13:47:31,675 - backend.main - INFO - GET /api/org/users/.../permissions - 200
```

### 前端效果

- ✅ 成功跳转回 http://10.242.94.9:3000
- ✅ 右上角显示 `👤 张健` + "登出"按钮
- ✅ 用户可以正常使用系统功能

## 经验教训

### 1. 避免全局Cookie命名冲突

**问题**: 多个服务使用相同的cookie名称会导致覆盖。

**最佳实践**:
- 为每个服务的cookie添加唯一前缀（如`task_session_id`, `hub_session_id`）
- 或使用domain/path隔离cookie作用域

### 2. URL参数必须正确编码

**问题**: 包含查询字符串的参数未编码会被框架错误解析。

**最佳实践**:
- 使用`urllib.parse.quote()`编码URL参数
- 对于完整URL使用`quote(url, safe='')`确保所有特殊字符被编码

### 3. window.location.href不会被proxy拦截

**问题**: Create React App的proxy只拦截fetch/axios请求，不拦截浏览器级跳转。

**最佳实践**:
- 浏览器级跳转（window.location.href）必须使用完整URL
- API调用可以使用相对路径依赖proxy

### 4. OAuth调试技巧

**有效方法**:
1. 在每个关键节点添加详细日志（session_id, state, code）
2. 比对创建的session_id和回调收到的session_id
3. 使用浏览器开发者工具查看cookie变化
4. 逐步验证每个OAuth步骤（authorize → login → callback → token → userinfo）

## 相关文件

### 后端修改
- `backend/auth_routes.py` - Cookie命名修改（主要）
- `backend/oauth/endpoints.py` - URL编码修复（Identity Hub）

### 前端修改
- `frontend/src/components/LoginButton.js` - 登录URL修复

### Identity Hub修改
- `identity-hub/backend/auth_routes.py` - 用户创建字段修复

## 配置说明

### 后端环境变量 (.env)

```bash
# Identity Hub配置
IDENTITY_HUB_URL=http://10.242.94.9:9000
IDENTITY_HUB_CLIENT_ID=task_feishu_dispatch_system
IDENTITY_HUB_CLIENT_SECRET=task_secret_key_2024
IDENTITY_HUB_REDIRECT_URI=http://10.242.94.9:8081/auth/callback

# 前端URL（用于OAuth回调后重定向）
FRONTEND_URL=http://10.242.94.9:3000
```

### 服务端口

- 前端: http://10.242.94.9:3000
- 后端: http://10.242.94.9:8081 (重要：不是8000！)
- Identity Hub: http://10.242.94.9:9000

### Cookie配置

- 后端session: `task_session_id` (httponly, samesite=lax, max_age=7200)
- Identity Hub session: `session_id` (httponly, samesite=lax, max_age=7200)

## 测试步骤

1. **清除浏览器cookie** - F12 → Application → Clear site data
2. **访问前端** - http://10.242.94.9:3000
3. **点击登录** - 右上角"登录"按钮
4. **飞书授权** - 点击"📱 使用飞书扫码登录" → 扫码
5. **验证结果** - 应跳转回前端并显示用户名

## 参考资料

- OAuth 2.0 RFC: https://datatracker.ietf.org/doc/html/rfc6749
- OpenID Connect Core: https://openid.net/specs/openid-connect-core-1_0.html
- FastAPI Cookie文档: https://fastapi.tiangolo.com/advanced/response-cookies/
- MDN - HTTP Cookies: https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies

## 后续优化建议

1. **生产环境部署**:
   - 使用HTTPS（启用secure=True）
   - 使用Redis存储session（当前是内存存储）
   - 设置合理的cookie domain和path

2. **安全增强**:
   - 实现CSRF token验证
   - 添加rate limiting
   - 记录安全审计日志

3. **用户体验**:
   - 添加登录加载动画
   - 优化错误提示信息
   - 实现remember me功能

---

**修复人员**: Claude (AI Assistant)
**审核人员**: 张健
**文档版本**: v1.0
