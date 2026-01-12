# 权限管理页面消失问题 - 诊断与修复方案

**问题描述**: 迁移服务器后，权限管理页面入口消失，无法访问用户管理功能

**诊断时间**: 2025-11-09

---

## 问题诊断结果

### ✅ 已确认正常的部分

1. **前端代码完整**
   - ✅ `UserManagement.js` - 用户管理主页面存在
   - ✅ `UserManagement.css` - 样式文件存在
   - ✅ `RoleAssignDialog.js` - 角色分配对话框存在
   - ✅ `PermissionWrapper.js` - 权限包装组件存在
   - ✅ `permission.js` - 权限工具函数存在

2. **前端集成完整**
   - ✅ Header.js 中有"用户管理"按钮（第99-109行）
   - ✅ App.js 中有UserManagement组件集成
   - ✅ 权限检查逻辑存在：`canAssignRole()`

3. **后端API路由已注册**
   - ✅ `/api/users` 路由已注册（users_router）
   - ✅ `/api/roles` 路由已注册（roles_router）
   - ✅ main.py 第77-78行已include

---

## ❌ 核心问题

### 问题1: 数据库文件权限错误（最严重）

```bash
错误信息: Error: in prepare, attempt to write a readonly database (8)

原因: 数据库文件所有者是root，普通用户无法读写
当前状态:
-rw-r--r-- 1 root root 364544 10月 22 11:25 /home/jian/code/Task_feishu/data/db/tasks.db
```

**影响**:
- 无法查询roles表
- 无法查询user_roles表
- 权限检查失败，导致按钮不显示

---

### 问题2: 可能缺少数据库表或数据

需要验证以下表是否存在且有数据：
- `roles` 表（角色定义）
- `user_roles` 表（用户角色关联）
- 默认3个角色数据

---

### 问题3: 用户未分配系统管理员角色

即使数据库正常，如果当前登录用户没有`system_admin`角色，也无法看到"用户管理"按钮。

---

## 修复方案

### 步骤1: 修复数据库文件权限（立即执行）

```bash
# 在新服务器上执行
cd /path/to/Task_feishu

# 检查当前运行应用的用户
whoami
# 假设输出是: deploy_user

# 修改数据库文件所有者
sudo chown deploy_user:deploy_user data/db/tasks.db
sudo chown deploy_user:deploy_user data/db/tasks.db-wal
sudo chown deploy_user:deploy_user data/db/tasks.db-shm

# 修改文件权限
sudo chmod 644 data/db/tasks.db
sudo chmod 644 data/db/tasks.db-wal 2>/dev/null
sudo chmod 644 data/db/tasks.db-shm 2>/dev/null

# 修改目录权限
sudo chmod 755 data/db
sudo chmod 755 data

# 验证权限
ls -la data/db/tasks.db
# 应该显示: -rw-r--r-- 1 deploy_user deploy_user ...
```

---

### 步骤2: 验证数据库表结构

```bash
# 检查数据库表
sqlite3 data/db/tasks.db ".tables"

# 应该看到：
# engineers  roles  tasks  user_roles

# 检查roles表
sqlite3 data/db/tasks.db "SELECT * FROM roles;"

# 应该有3条记录：
# 1|system_admin|系统管理员|...
# 2|manager|管理者|...
# 3|regular_user|普通人员|...
```

---

### 步骤3: 如果缺少表或数据，运行迁移脚本

```bash
cd backend

# 1. 创建角色表
python3 migrations/create_role_tables.py

# 2. 插入默认角色
python3 migrations/insert_default_roles.py

# 3. 验证结果
python3 migrations/verify_permission_schema.py
```

---

### 步骤4: 给当前用户分配系统管理员角色

#### 方法A: 通过数据库直接分配（推荐，用于第一个管理员）

```bash
# 1. 查看当前用户的user_id
sqlite3 data/db/tasks.db "SELECT user_id, name, email FROM engineers LIMIT 10;"

# 2. 找到你的user_id，假设是 'ou_abc123'

# 3. 检查system_admin角色的ID
sqlite3 data/db/tasks.db "SELECT id, role_key, role_name FROM roles WHERE role_key='system_admin';"
# 应该输出: 1|system_admin|系统管理员

# 4. 分配系统管理员角色
sqlite3 data/db/tasks.db "INSERT INTO user_roles (user_id, role_id) VALUES ('ou_abc123', 1);"

# 5. 验证分配成功
sqlite3 data/db/tasks.db "
SELECT u.user_id, u.name, r.role_name
FROM user_roles ur
JOIN engineers u ON ur.user_id = u.user_id
JOIN roles r ON ur.role_id = r.id
WHERE ur.user_id = 'ou_abc123';
"
```

#### 方法B: 通过API分配（需要已有管理员权限）

```bash
# 使用curl调用API（需要有有效的session cookie）
curl -X POST http://10.242.94.9:8000/api/users/ou_abc123/roles \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"role_id": 1}'
```

---

### 步骤5: 重启应用并验证

```bash
# 重启后端服务
cd /path/to/Task_feishu
# 如果是Docker
docker-compose restart app

# 如果是直接运行
pkill -f "python.*main.py"
cd backend
python3 main.py
```

---

### 步骤6: 前端验证

1. **清除浏览器缓存和localStorage**
   ```javascript
   // 浏览器控制台执行
   localStorage.clear();
   location.reload();
   ```

2. **重新登录**
   - 访问 http://10.242.94.9:8080
   - 使用飞书OAuth登录

3. **检查localStorage中的权限数据**
   ```javascript
   // 浏览器控制台执行
   const userInfo = JSON.parse(localStorage.getItem('userInfo'));
   console.log('用户信息:', userInfo);
   console.log('权限列表:', userInfo.permissions);
   console.log('角色列表:', userInfo.roles);

   // 应该看到：
   // roles: [{ role_name: "系统管理员", role_key: "system_admin", ... }]
   // permissions: ["user:read", "user:write", "role:assign", ...]
   ```

4. **验证"用户管理"按钮显示**
   - 登录后，页面顶部应该显示橙色的"用户管理"按钮
   - 位置：在"工单管理"按钮右侧

5. **点击进入用户管理页面**
   - 应该看到用户列表
   - 可以搜索用户
   - 可以点击"管理角色"按钮

---

## 完整检查清单

### 数据库层面
- [ ] 数据库文件权限正确（644, 所有者为运行用户）
- [ ] roles表存在且有3条默认数据
- [ ] user_roles表存在
- [ ] 当前用户在user_roles表中有system_admin角色

### 后端层面
- [ ] main.py已注册roles_router和users_router
- [ ] 后端服务正常启动，无错误日志
- [ ] API接口可访问：GET /api/roles
- [ ] API接口可访问：GET /api/users

### 前端层面
- [ ] Header.js中有用户管理按钮代码
- [ ] App.js中有UserManagement组件集成
- [ ] canAssignRole()函数正常工作
- [ ] localStorage中有正确的userInfo和permissions

### 用户体验层面
- [ ] 登录后可以看到"用户管理"按钮
- [ ] 点击按钮可以进入用户管理页面
- [ ] 可以查看用户列表
- [ ] 可以分配和撤销角色

---

## 快速诊断脚本

创建一个诊断脚本来自动检查所有问题：

```bash
#!/bin/bash
# 文件: diagnose_permission_system.sh

echo "=== 权限管理系统诊断 ==="
echo ""

# 1. 检查数据库文件权限
echo "1. 数据库文件权限:"
ls -l data/db/tasks.db
echo ""

# 2. 检查数据库表
echo "2. 数据库表列表:"
sqlite3 data/db/tasks.db ".tables"
echo ""

# 3. 检查角色数据
echo "3. 角色列表:"
sqlite3 data/db/tasks.db "SELECT id, role_key, role_name FROM roles;"
echo ""

# 4. 检查用户角色分配
echo "4. 系统管理员列表:"
sqlite3 data/db/tasks.db "
SELECT u.user_id, u.name, u.email, r.role_name
FROM user_roles ur
JOIN engineers u ON ur.user_id = u.user_id
JOIN roles r ON ur.role_id = r.id
WHERE r.role_key = 'system_admin';
"
echo ""

# 5. 检查后端进程
echo "5. 后端进程状态:"
ps aux | grep "python.*main.py" | grep -v grep
echo ""

# 6. 测试API访问
echo "6. 测试API访问:"
curl -s http://localhost:8000/health | head -1
echo ""

echo "=== 诊断完成 ==="
```

使用方法：
```bash
chmod +x diagnose_permission_system.sh
./diagnose_permission_system.sh
```

---

## 常见问题Q&A

### Q1: 修复权限后还是看不到按钮？
**A**: 清除浏览器localStorage并重新登录
```javascript
localStorage.clear();
location.reload();
```

### Q2: 用户列表是空的？
**A**: 需要先同步飞书用户
1. 点击"同步飞书组织架构"按钮
2. 或运行：`python3 backend/sync_users_from_feishu_full.py`

### Q3: API返回403 Forbidden？
**A**: 检查用户是否有正确的权限
```sql
SELECT u.user_id, u.name, r.role_name
FROM user_roles ur
JOIN engineers u ON ur.user_id = u.user_id
JOIN roles r ON ur.role_id = r.id
WHERE u.user_id = 'YOUR_USER_ID';
```

### Q4: 数据库迁移失败？
**A**: 确保数据库文件权限正确，然后重新运行迁移脚本

---

## 预防措施

### 1. 备份关键数据
```bash
# 迁移前备份
cp data/db/tasks.db data/db/tasks.db.backup.$(date +%Y%m%d_%H%M%S)

# 导出SQL
sqlite3 data/db/tasks.db .dump > backup.sql
```

### 2. 文档化权限配置
- 记录哪些用户是系统管理员
- 记录数据库文件路径和权限要求
- 记录迁移步骤

### 3. 自动化检查
- 在启动脚本中添加权限检查
- 定期验证数据库完整性

---

## 相关文件路径

### 前端文件
```
frontend/src/
├── components/
│   ├── UserManagement.js          # 用户管理主页面
│   ├── UserManagement.css         # 样式
│   ├── RoleAssignDialog.js        # 角色分配对话框
│   ├── RoleAssignDialog.css       # 对话框样式
│   ├── PermissionWrapper.js       # 权限包装组件
│   └── Header.js                  # 顶部导航（第99-109行有按钮）
└── utils/
    └── permission.js              # 权限工具函数
```

### 后端文件
```
backend/
├── routers/
│   ├── users.py                   # 用户管理API
│   └── roles.py                   # 角色管理API
├── migrations/
│   ├── create_role_tables.py     # 创建角色表
│   ├── insert_default_roles.py   # 插入默认角色
│   └── verify_permission_schema.py # 验证schema
├── auth_permission.py             # 权限验证中间件
└── main.py                        # 主应用（第77-78行注册路由）
```

### 数据库
```
data/db/
└── tasks.db                       # 主数据库文件
    ├── roles                      # 角色表
    ├── user_roles                 # 用户角色关联表
    ├── engineers                  # 工程师表
    └── tasks                      # 任务表
```

---

**总结**: 99%的可能是**数据库文件权限问题**导致的。修复权限后，给自己分配系统管理员角色，重新登录即可看到"用户管理"按钮。
