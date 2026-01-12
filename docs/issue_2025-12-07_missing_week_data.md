# 问题记录：前端缺少12.08那周数据

**日期**: 2025-12-07
**状态**: ✅ 已解决

## 问题描述

前端页面没有显示12.08那周的数据

## 问题原因

### 1. 数据库路径不一致（已在之前修复）
- 宿主机同步进程写入 `backend/data/db/tasks.db`
- Docker容器使用 `data/db/tasks.db`

### 2. Nginx未传递Cookie（已修复）
- `/api/` location缺少 `proxy_set_header Cookie $http_cookie;`
- 导致后端无法识别用户登录状态

### 3. 前端fetchTasks未携带credentials（已修复）
- `frontend/src/utils/api.js` 的 `fetchTasks` 函数缺少 `credentials: 'include'`

### 4. 后端未登录返回空数据（已修复）
- `backend/routers/tasks.py` 第51-56行，未登录用户返回空TaskGroup
- 业务需求：未登录用户也应能查看任务数据

## 解决方案

### 修复1: Nginx配置 (docker/nginx/nginx.frontend.conf)
```nginx
location /api/ {
    proxy_pass http://app:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Cookie $http_cookie;  # 添加此行
}
```

### 修复2: 前端API (frontend/src/utils/api.js)
```javascript
// fetchTasks函数添加credentials
const response = await fetch(url, {
    credentials: 'include',
});
```

### 修复3: 后端权限逻辑 (backend/routers/tasks.py)
移除未登录返回空数据的限制，改为：
```python
# 1. 检查用户登录状态（可选，用于数据权限过滤）
current_user = await get_current_user_optional(request)
user_id = current_user.get("user_id") if current_user else None
user_name = current_user.get("user_name", "Unknown") if current_user else None

# 3. 应用数据权限过滤（未登录用户可查看所有数据）
if user_id:
    data_scope = get_user_data_scope(user_id)
else:
    data_scope = "all"  # 未登录用户显示所有数据
```

## 部署步骤

```bash
cd /opt/task_feishu/prod_192.168.101.13/docker

# 重新构建并部署前端（包含nginx配置和前端代码）
cd ../frontend && npm run build && cd ../docker
docker compose build frontend
docker compose up -d frontend

# 重新构建并部署后端
docker compose build app
docker compose up -d app
```

## 验证结果

```bash
# API返回12.08那周数据
curl -s "http://localhost:8080/api/tasks?start_date=2025-12-08&end_date=2025-12-14" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for day in ['monday','tuesday','wednesday','thursday','friday']:
    print(f'{day}: {len(d.get(day,[]))} tasks')
"
# 输出: monday: 3 tasks, tuesday: 3 tasks, ...
```

## Cron同步状态

- 配置: `0 * * * *` (每小时整点执行)
- 脚本: `/opt/task_feishu/prod_192.168.101.13/scripts/cron_sync.sh`
- 日志: `/opt/task_feishu/prod_192.168.101.13/logs/sync.log`
- 状态: ✅ 正常运行

## 相关文件

- `docker/nginx/nginx.frontend.conf` - Nginx配置
- `frontend/src/utils/api.js` - 前端API调用
- `backend/routers/tasks.py` - 后端任务路由
- `scripts/cron_sync.sh` - 定时同步脚本
