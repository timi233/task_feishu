# 工单系统 - 前端权限管理页面完整说明文档

**生成时间**: 2025-11-09
**开发阶段**: Phase 4.3 - 4.6
**功能模块**: 权限管理系统前端实现

---

## 一、功能概览

前端权限管理系统提供了完整的RBAC（基于角色的访问控制）界面，主要包含以下功能：

### 核心功能
1. **用户管理页面** - 显示和管理所有系统用户
2. **角色分配** - 为用户分配和撤销角色
3. **权限控制组件** - 基于权限的UI渲染控制
4. **用户同步** - 从飞书组织架构同步用户数据

### 访问权限
- **仅系统管理员**可以访问用户管理页面
- 普通用户访问会显示"权限不足"提示

---

## 二、页面结构

### 1. 用户管理主页面 (UserManagement.js)

**路由**: `/user-management` （需在App.js中配置）

**文件位置**: `frontend/src/components/UserManagement.js`

#### 页面布局

```
┌─────────────────────────────────────────────────────┐
│ 用户管理                                            │
│ 管理系统用户的角色和权限                            │
│                                     [同步飞书组织架构] [清理重复数据] [刷新] │
├─────────────────────────────────────────────────────┤
│ 🔍 搜索用户（姓名、邮箱、ID或角色）                 │
│ 找到 X 个用户                                       │
├─────────────────────────────────────────────────────┤
│ 用户ID    │ 姓名    │ 邮箱         │ 角色      │ 操作   │
├─────────────────────────────────────────────────────┤
│ ou_xxx    │ 张三    │ zhang@...    │ [管理者]  │ [管理角色] │
│ ou_yyy    │ 李四    │ li@...       │ [普通人员]│ [管理角色] │
│ ou_zzz    │ 王五    │ wang@...     │ 暂无角色  │ [管理角色] │
└─────────────────────────────────────────────────────┘
```

#### 功能详解

##### A. 头部操作区
```javascript
// 3个核心按钮
1. [同步飞书组织架构] - 从飞书遍历所有部门同步用户
2. [清理重复数据] - 删除临时用户和Identity Hub用户，只保留飞书用户
3. [刷新] - 重新加载用户列表
```

##### B. 搜索区域
- **支持模糊搜索**：
  - 用户姓名
  - 邮箱地址
  - 用户ID（飞书user_id）
  - 角色名称
- **实时过滤**：输入时立即更新结果
- **统计显示**：`找到 X 个用户（共 Y 个）`

##### C. 用户列表表格
```javascript
表头字段：
- 用户ID（user_id）
- 姓名（name）
- 邮箱（email）
- 角色（roles）- 以徽章形式显示
- 操作（actions）- [管理角色] 按钮
```

##### D. 角色徽章样式
```css
角色类型            背景色          文字色          边框色
系统管理员 (admin)   橙色 #fff2e8    #d46b08       #ffd591
管理者 (manager)     蓝色 #e6f7ff    #0958d9       #91d5ff
普通人员 (regular)   绿色 #f6ffed    #389e0d       #b7eb8f
```

##### E. 权限检查
```javascript
// 页面级权限控制
const hasPermission = canAssignRole();

// 无权限时显示
if (!hasPermission) {
  return (
    <div className="permission-denied">
      🔒
      <h2>权限不足</h2>
      <p>您没有访问用户管理页面的权限</p>
      <p>仅系统管理员可以访问此页面</p>
    </div>
  );
}
```

---

### 2. 角色分配对话框 (RoleAssignDialog.js)

**触发方式**: 点击用户列表中的"管理角色"按钮

**文件位置**: `frontend/src/components/RoleAssignDialog.js`

#### 对话框布局

```
┌──────────────────────────────────────────┐
│ 角色管理 - 张三                      [×] │
├──────────────────────────────────────────┤
│ 用户信息                                 │
│ 用户ID: ou_xxx                           │
│ 姓名: 张三                               │
│ 邮箱: zhang@example.com                  │
├──────────────────────────────────────────┤
│ 当前角色                                 │
│ ┌────────────────────────────────────┐  │
│ │ 管理者 (all)              [撤销]  │  │
│ │ 普通人员 (self)           [撤销]  │  │
│ └────────────────────────────────────┘  │
├──────────────────────────────────────────┤
│ 分配新角色                               │
│ [选择角色 ▼]             [分配角色]      │
│ └─ 系统管理员 (all)                      │
│ └─ 管理者 (all)                          │
│ └─ 普通人员 (self)                       │
├──────────────────────────────────────────┤
│ ✓ 角色分配成功                           │
├──────────────────────────────────────────┤
│                              [关闭]      │
└──────────────────────────────────────────┘
```

#### 功能详解

##### A. 用户信息显示
```javascript
{
  user_id: "ou_xxx",       // 飞书用户ID
  name: "张三",            // 用户姓名
  email: "zhang@xx.com"    // 用户邮箱
}
```

##### B. 当前角色列表
- **显示内容**：
  - 角色名称（如"系统管理员"）
  - 数据范围（all=全部数据，self=仅自己相关）
  - [撤销] 按钮
- **撤销功能**：
  ```javascript
  // 点击撤销会：
  1. 弹出确认对话框
  2. 发送DELETE请求到 /api/users/{user_id}/roles/{role_id}
  3. 成功后刷新用户列表
  ```

##### C. 分配新角色
- **下拉选择框**：
  - 只显示用户**尚未拥有**的角色
  - 格式：`角色名称 (数据范围)`
  - 示例：`系统管理员 (all)`
- **分配流程**：
  ```javascript
  1. 选择角色
  2. 点击"分配角色"按钮
  3. 发送POST请求到 /api/users/{user_id}/roles
  4. 请求体: { role_id: 1 }
  5. 成功后显示成功消息，刷新列表
  ```

##### D. 消息提示
```javascript
// 成功消息
<div className="success-message">
  ✓ 角色分配成功
</div>

// 错误消息
<div className="error-message">
  ⚠️ 分配角色失败: {错误原因}
</div>
```

---

## 三、权限控制体系

### 1. 权限工具函数 (permission.js)

**文件位置**: `frontend/src/utils/permission.js`

#### 核心函数

```javascript
// ===== 权限获取 =====
getUserPermissions()       // 从localStorage获取权限列表
getUserRoles()             // 从localStorage获取角色列表
isAuthenticated()          // 检查是否已登录
getCurrentUser()           // 获取当前用户完整信息

// ===== 权限检查 =====
hasPermission('task:create')                    // 检查单个权限
hasAnyPermission(['task:create', 'task:read'])  // 有任一权限即可
hasAllPermissions(['task:create', 'task:read']) // 必须拥有所有权限
hasRole('系统管理员')                           // 检查是否有指定角色
isSystemAdmin()                                 // 检查是否是系统管理员

// ===== 常用快捷函数 =====
canCreateTask()      // 是否可以创建派工
canReadTask()        // 是否可以读取派工
canUpdateTask()      // 是否可以更新派工
canDeleteTask()      // 是否可以删除派工
canManageApproval()  // 是否可以管理审批
canManageUser()      // 是否可以管理用户
canAssignRole()      // 是否可以分配角色（系统管理员专属）
```

#### 数据结构

```javascript
// localStorage中的userInfo结构
{
  user_id: "ou_abc123",
  name: "张三",
  email: "zhang@example.com",

  // 权限列表
  permissions: [
    "task:create",
    "task:read",
    "task:update",
    "task:delete",
    "approval:create",
    "role:assign",
    // ...
  ],

  // 角色列表
  roles: [
    {
      role_id: 1,
      role_key: "system_admin",
      role_name: "系统管理员",
      data_scope: "all"
    }
  ]
}
```

---

### 2. 权限包装组件 (PermissionWrapper.js)

**文件位置**: `frontend/src/components/PermissionWrapper.js`

#### 组件类型

##### A. PermissionWrapper - 通用权限包装器
```jsx
// 基础用法
<PermissionWrapper permission="task:create">
  <button>新建派工</button>
</PermissionWrapper>

// 多权限（任一即可）
<PermissionWrapper permissions={["task:update", "task:delete"]} mode="any">
  <button>编辑或删除</button>
</PermissionWrapper>

// 多权限（必须全部拥有）
<PermissionWrapper permissions={["task:create", "task:delete"]} mode="all">
  <button>高级操作</button>
</PermissionWrapper>

// 基于角色
<PermissionWrapper role="系统管理员">
  <AdminPanel />
</PermissionWrapper>

// 自定义fallback
<PermissionWrapper
  permission="task:delete"
  fallbackMessage="您没有删除权限"
>
  <button>删除</button>
</PermissionWrapper>

// 不显示fallback（直接隐藏）
<PermissionWrapper permission="task:create" fallback={false}>
  <button>新建</button>
</PermissionWrapper>
```

##### B. PermissionButton - 权限控制按钮
```jsx
<PermissionButton
  permission="task:create"
  onClick={handleCreate}
  disabled={loading}
  disabledMessage="权限不足"
>
  新建派工
</PermissionButton>
```

##### C. PermissionRoute - 路由权限控制
```jsx
<PermissionRoute
  path="/user-management"
  component={UserManagement}
  permission="role:assign"
  fallbackComponent={NoPermissionPage}
/>
```

---

## 四、API 接口

### 1. 获取用户列表
```http
GET /api/users
Authorization: Cookie (session)

响应:
[
  {
    "user_id": "ou_abc123",
    "name": "张三",
    "email": "zhang@example.com",
    "roles": [
      {
        "role_id": 1,
        "role_key": "system_admin",
        "role_name": "系统管理员",
        "data_scope": "all"
      }
    ]
  }
]
```

### 2. 获取角色列表
```http
GET /api/roles
Authorization: Cookie (session)

响应:
[
  {
    "id": 1,
    "role_key": "system_admin",
    "role_name": "系统管理员",
    "description": "可以管理用户权限、查看和操作所有数据",
    "data_scope": "all",
    "permissions": ["user:read", "user:write", "role:assign", ...]
  },
  {
    "id": 2,
    "role_key": "manager",
    "role_name": "管理者",
    "description": "可以查看和操作所有派工数据，但不能管理用户权限",
    "data_scope": "all",
    "permissions": ["task:read", "task:create", ...]
  }
]
```

### 3. 分配角色
```http
POST /api/users/{user_id}/roles
Authorization: Cookie (session)
Content-Type: application/json

请求体:
{
  "role_id": 1
}

响应:
{
  "message": "角色分配成功",
  "user_id": "ou_abc123",
  "role_id": 1,
  "role_name": "系统管理员"
}
```

### 4. 撤销角色
```http
DELETE /api/users/{user_id}/roles/{role_id}
Authorization: Cookie (session)

响应:
{
  "message": "角色撤销成功",
  "user_id": "ou_abc123",
  "role_id": 1
}
```

### 5. 同步飞书用户
```http
POST /api/users/sync/feishu
Authorization: Cookie (session)

响应:
{
  "message": "同步成功",
  "synced_count": 25,
  "updated_count": 10,
  "new_count": 15
}
```

### 6. 同步Identity Hub用户
```http
POST /api/users/sync/identity-hub
Authorization: Cookie (session)

响应:
{
  "message": "同步成功",
  "synced_count": 5
}
```

### 7. 清理重复用户
```http
POST /api/users/sync/cleanup
Authorization: Cookie (session)

响应:
{
  "message": "清理成功",
  "deleted_count": 3,
  "deleted_users": ["temp_user_1", "temp_user_2"]
}
```

---

## 五、样式设计

### 1. 配色方案

```css
/* 主色调 */
--primary-blue: #1890ff;      /* 主要操作按钮 */
--success-green: #52c41a;     /* 成功状态、同步按钮 */
--warning-orange: #ff9800;    /* 警告操作 */
--danger-red: #ff4d4f;        /* 删除、错误 */

/* 角色徽章颜色 */
--admin-orange: #d46b08;      /* 系统管理员 */
--manager-blue: #0958d9;      /* 管理者 */
--regular-green: #389e0d;     /* 普通人员 */

/* 背景色 */
--bg-gray: #fafafa;           /* 表头背景 */
--border-gray: #e8e8e8;       /* 边框 */
--hover-gray: #f5f5f5;        /* hover背景 */
```

### 2. 组件样式

#### 用户表格
```css
.users-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
}

/* 行hover效果 */
.users-table tbody tr:hover {
  background-color: #fafafa;
  transition: background-color 0.2s;
}
```

#### 角色徽章
```css
.role-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

/* 系统管理员徽章 */
.role-badge.admin {
  background-color: #fff2e8;
  color: #d46b08;
  border: 1px solid #ffd591;
}
```

#### 对话框
```css
.role-assign-dialog {
  width: 600px;
  max-width: 90vw;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
```

---

## 六、使用流程示例

### 场景1: 系统管理员分配角色给新员工

```
1. 管理员登录系统
   ↓
2. 点击顶部导航"用户管理"
   ↓
3. 点击"同步飞书组织架构"同步最新人员
   ↓
4. 在搜索框输入新员工姓名
   ↓
5. 找到新员工，点击"管理角色"按钮
   ↓
6. 在对话框中选择"普通人员"角色
   ↓
7. 点击"分配角色"
   ↓
8. 看到"角色分配成功"提示
   ↓
9. 关闭对话框，用户列表自动刷新显示新角色
```

### 场景2: 提升普通用户为管理者

```
1. 管理员搜索目标用户
   ↓
2. 点击"管理角色"
   ↓
3. 看到当前角色：[普通人员]
   ↓
4. 在"分配新角色"区域选择"管理者"
   ↓
5. 点击"分配角色"
   ↓
6. 用户现在同时拥有两个角色
   ↓
7. 如需撤销旧角色，点击旧角色旁的"撤销"按钮
```

### 场景3: 批量清理重复数据

```
1. 管理员发现用户列表有重复数据
   ↓
2. 点击"清理重复数据"按钮
   ↓
3. 确认弹窗："确定要清理重复用户吗？将删除所有临时用户..."
   ↓
4. 点击"确定"
   ↓
5. 看到"清理成功，删除了3个重复用户"
   ↓
6. 用户列表自动刷新
```

---

## 七、权限矩阵

### 默认角色权限

| 功能 | 系统管理员 | 管理者 | 普通人员 |
|------|-----------|--------|---------|
| 查看所有派工 | ✅ | ✅ | ❌ (仅自己相关) |
| 创建派工 | ✅ | ✅ | ❌ |
| 更新派工 | ✅ | ✅ | ✅ (仅自己相关) |
| 删除派工 | ✅ | ✅ | ❌ |
| 创建审批 | ✅ | ✅ | ❌ |
| 查看审批 | ✅ | ✅ | ✅ (仅自己相关) |
| 管理用户角色 | ✅ | ❌ | ❌ |
| 同步组织架构 | ✅ | ❌ | ❌ |
| 访问用户管理页面 | ✅ | ❌ | ❌ |

### 权限代码映射

```javascript
// 系统管理员权限
const ADMIN_PERMISSIONS = [
  "user:read", "user:write", "user:delete",
  "role:assign", "role:revoke",
  "task:read", "task:create", "task:update", "task:delete",
  "approval:read", "approval:create", "approval:update", "approval:delete"
];

// 管理者权限
const MANAGER_PERMISSIONS = [
  "task:read", "task:create", "task:update", "task:delete",
  "approval:read", "approval:create", "approval:update", "approval:delete"
];

// 普通人员权限
const REGULAR_USER_PERMISSIONS = [
  "task:read", "task:update",          // 仅自己相关
  "approval:read", "approval:update"   // 仅自己相关
];
```

---

## 八、响应式设计

### 移动端适配

```css
@media (max-width: 768px) {
  /* 头部操作区垂直排列 */
  .user-management-header {
    flex-direction: column;
    gap: 16px;
  }

  /* 按钮全宽 */
  .header-actions button {
    width: 100%;
  }

  /* 表格横向滚动 */
  .users-table-container {
    overflow-x: auto;
  }

  /* 对话框宽度适配 */
  .role-assign-dialog {
    width: 95vw;
    margin: 10px;
  }
}
```

---

## 九、错误处理

### 常见错误场景

#### 1. 未登录访问
```javascript
// 检测到未登录
if (!isAuthenticated()) {
  // 重定向到登录页
  window.location.href = '/login';
}
```

#### 2. 权限不足
```javascript
// 用户管理页面
if (!canAssignRole()) {
  return <PermissionDenied />;
}

// 显示内容
<div className="permission-denied">
  🔒 权限不足
  您没有访问用户管理页面的权限
  仅系统管理员可以访问此页面
</div>
```

#### 3. API请求失败
```javascript
// 网络错误
catch (err) {
  setError(err.message);
  // 显示错误横幅
  <div className="error-banner">
    ⚠️ {error}
    <button onClick={retry}>重试</button>
  </div>
}
```

#### 4. 同步失败
```javascript
// 飞书同步失败
{
  "detail": "飞书API访问失败: 401 Unauthorized"
}

// 前端显示
<div className="error-banner">
  ⚠️ 同步失败: 飞书API访问失败
</div>
```

---

## 十、开发调试

### 本地开发模拟用户

```javascript
// 在浏览器控制台执行
import { setMockUser, debugPermissions } from './utils/permission';

// 模拟系统管理员
setMockUser({
  name: "测试管理员",
  email: "admin@test.com",
  permissions: [
    "user:read", "user:write", "user:delete",
    "role:assign", "role:revoke",
    "task:read", "task:create", "task:update", "task:delete"
  ],
  roles: [{ role_name: "系统管理员" }]
});

// 打印权限信息
debugPermissions();
```

### 查看localStorage数据

```javascript
// 浏览器控制台
const userInfo = JSON.parse(localStorage.getItem('userInfo'));
console.log('用户信息:', userInfo);
console.log('权限列表:', userInfo.permissions);
console.log('角色列表:', userInfo.roles);
```

---

## 十一、集成指南

### 在App.js中集成用户管理页面

```jsx
import React, { useState, useEffect } from 'react';
import UserManagement from './components/UserManagement';
import { isSystemAdmin } from './utils/permission';

function App() {
  const [currentView, setCurrentView] = useState('main');

  // 检查是否显示用户管理菜单
  const showUserManagement = isSystemAdmin();

  return (
    <div className="app">
      <Header>
        <nav>
          {showUserManagement && (
            <button onClick={() => setCurrentView('user-management')}>
              用户管理
            </button>
          )}
        </nav>
      </Header>

      <main>
        {currentView === 'user-management' ? (
          <UserManagement />
        ) : (
          <MainView />
        )}
      </main>
    </div>
  );
}
```

---

## 十二、性能优化

### 1. 搜索防抖
```javascript
// 避免每次输入都过滤
const [searchTerm, setSearchTerm] = useState('');

// 使用useEffect实现过滤
useEffect(() => {
  const timer = setTimeout(() => {
    // 执行过滤逻辑
    filterUsers(searchTerm);
  }, 300); // 300ms防抖

  return () => clearTimeout(timer);
}, [searchTerm]);
```

### 2. 虚拟滚动（用户列表过长时）
```javascript
// 仅渲染可见区域的用户
// 可使用 react-window 或 react-virtualized
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={filteredUsers.length}
  itemSize={60}
>
  {({ index, style }) => (
    <UserRow user={filteredUsers[index]} style={style} />
  )}
</FixedSizeList>
```

---

## 十三、安全考虑

### 1. XSS防护
```javascript
// 所有用户输入都使用React自动转义
// 避免使用dangerouslySetInnerHTML

// ✅ 安全
<div>{user.name}</div>

// ❌ 危险
<div dangerouslySetInnerHTML={{ __html: user.name }} />
```

### 2. 敏感信息处理
```javascript
// 不在前端存储敏感数据
// ✅ 只存储必要信息
localStorage.setItem('userInfo', JSON.stringify({
  user_id: "ou_xxx",
  name: "张三",
  permissions: [...]
}));

// ❌ 不要存储密码、token等
```

### 3. 权限双重验证
```javascript
// 前端控制UI显示
<PermissionWrapper permission="role:assign">
  <button onClick={assignRole}>分配角色</button>
</PermissionWrapper>

// 后端必须再次验证权限
// 前端权限检查只是UX优化，不能作为安全保障
```

---

## 十四、相关文件清单

```
frontend/src/
├── components/
│   ├── UserManagement.js           # 用户管理主页面
│   ├── UserManagement.css          # 用户管理样式
│   ├── RoleAssignDialog.js         # 角色分配对话框
│   ├── RoleAssignDialog.css        # 对话框样式
│   └── PermissionWrapper.js        # 权限包装组件
│
├── utils/
│   └── permission.js               # 权限工具函数
│
└── App.js                          # 主应用（需集成用户管理）
```

---

## 十五、未来优化方向

### 1. 批量操作
- 批量分配角色
- 批量撤销角色
- 批量导入用户

### 2. 高级搜索
- 按部门筛选
- 按角色筛选
- 按状态筛选（在职/离职）

### 3. 操作日志
- 记录角色分配历史
- 显示操作人和操作时间
- 支持审计追踪

### 4. 自定义角色
- 允许管理员创建自定义角色
- 自定义权限组合
- 角色模板功能

---

**文档维护**: 功能更新时请及时更新此文档
