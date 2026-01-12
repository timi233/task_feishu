# Invalid State 登录问题修复记录

**日期**: 2025-11-26
**环境**: 生产环境 192.168.101.13
**问题**: OAuth 登录回调时提示 "Invalid state"

---

## 问题现象

用户在生产环境 (192.168.101.13) 点击登录后，完成飞书扫码认证，回调时出现 "Invalid state" 错误。

## 问题分析

### OAuth 登录流程

```
1. 用户访问 192.168.101.13:8080/auth/login
   ↓
2. 派工后端创建 session，保存 oauth_state
   ↓
3. 设置 task_session_id cookie
   ↓
4. 重定向到 Identity Hub (192.168.101.13:9000/oauth/authorize)
   ↓
5. Identity Hub 检查用户登录状态，未登录则显示飞书扫码页
   ↓
6. 用户扫码登录
   ↓
7. Identity Hub 重定向回 192.168.101.13:8080/auth/callback?code=xxx&state=xxx
   ↓
8. 派工后端从 cookie 获取 session，验证 state
   ↓
9. 如果 state 不匹配，返回 "Invalid state" 错误
```

### 根因分析

**可能原因 1: 配置错误**
- `docker/docker-compose.yml` 中 `FRONTEND_URL` 仍为开发环境 IP (`10.242.94.9`)
- 代码中默认回退值使用开发环境 IP

**可能原因 2: Session 丢失**
- 两个系统都使用内存存储 session
- Docker 容器重启会导致所有 session 丢失
- 用户扫码期间如果后端容器重启，`oauth_state` 就会丢失

**可能原因 3: Cookie 未携带**
- 浏览器阻止第三方 cookie
- SameSite 策略限制跨端口 cookie 传递

---

## 修复内容

### 1. 修复 docker-compose.yml

**文件**: `docker/docker-compose.yml`

```diff
- - FRONTEND_URL=http://10.242.94.9:8080
+ - FRONTEND_URL=http://192.168.101.13:8080
```

### 2. 修复 auth_routes.py 默认值

**文件**: `backend/auth_routes.py`

所有 `FRONTEND_URL` 的默认回退值从 `http://10.242.94.9:3000` 改为 `http://192.168.101.13:8080`

### 3. 修复 auth_identity_hub.py 默认值

**文件**: `backend/auth_identity_hub.py`

```diff
- self.hub_url = hub_url or os.getenv("IDENTITY_HUB_URL", "http://10.242.94.9:8000")
+ self.hub_url = hub_url or os.getenv("IDENTITY_HUB_URL", "http://192.168.101.13:9000")
```

### 4. 增强调试日志

**文件**: `backend/auth_routes.py`

在 `/auth/login` 和 `/auth/callback` 端点添加详细日志：

```python
# Login 端点
logger.info(f"✅ Login initiated:")
logger.info(f"   Session ID: {session_id[:16]}...")
logger.info(f"   State: {state[:16]}...")
logger.info(f"   Active sessions: {session_manager.get_session_count()}")

# Callback 端点
logger.info(f"All cookies received: {list(all_cookies.keys())}")
logger.info(f"Active sessions count: {session_manager.get_session_count()}")
```

### 5. 改进错误处理

将 HTTP 400 错误改为友好的重定向，让用户可以重新登录：

```python
# Session 丢失时
return RedirectResponse(
    url=f"{frontend_url}/?error=session_lost&message=请重新登录",
    status_code=status.HTTP_302_FOUND
)

# State 不匹配时
return RedirectResponse(
    url=f"{frontend_url}/?error=invalid_state&message=登录验证失败，请重新登录",
    status_code=status.HTTP_302_FOUND
)
```

---

## 部署步骤

```bash
# 1. SSH 到生产服务器
ssh pytc@192.168.101.13

# 2. 进入项目目录
cd /path/to/task_feishu

# 3. 重建并重启 Docker 容器
cd docker
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 4. 检查日志
docker-compose logs -f app

# 5. 重启 Identity Hub（如果单独运行）
cd ../identity-hub
docker-compose restart
```

---

## 验证方法

```bash
# 1. 检查后端健康状态
curl http://192.168.101.13:8080/health

# 2. 检查 Identity Hub 健康状态
curl http://192.168.101.13:9000/health

# 3. 测试登录端点
curl -I http://192.168.101.13:8080/auth/login?return_url=/

# 4. 查看后端日志
docker-compose logs -f app | grep -E "(Login initiated|Callback received|State mismatch)"
```

---

## 日志排查指南

如果问题仍然存在，查看后端日志中的以下信息：

| 日志关键字 | 含义 | 处理方式 |
|-----------|------|---------|
| `✅ Login initiated` | 登录请求成功 | 正常 |
| `Callback received` | 回调已收到 | 检查后续日志 |
| `❌ Missing task_session_id cookie` | Cookie 未携带 | 检查浏览器 cookie 设置 |
| `❌ Invalid or expired session` | Session 丢失 | 可能容器重启，检查容器运行状态 |
| `❌ State mismatch` | State 不匹配 | 检查是否多次点击登录 |

---

## 后续优化建议

1. **持久化 Session 存储**: 考虑使用 Redis 或数据库存储 session，避免容器重启导致 session 丢失

2. **Session 恢复机制**: 在 callback 时如果 session 丢失，可以尝试从数据库恢复或直接重新发起登录

3. **监控告警**: 添加登录失败的监控指标，及时发现问题

---

## 相关文件

- `backend/auth_routes.py` - OAuth 认证路由
- `backend/auth_identity_hub.py` - Identity Hub 客户端
- `backend/session_manager.py` - Session 管理器
- `docker/docker-compose.yml` - Docker 配置
- `.env` - 环境变量配置
