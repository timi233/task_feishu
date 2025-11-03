# 权限管理系统设计方案

**日期**: 2025-11-03
**版本**: v1.0
**阶段**: Phase 4.6 - 权限管理功能
**状态**: 📝 设计阶段

---

## 一、现状分析

### 1.1 数据检查结果

#### ✅ 现有结构

1. **tasks表** (365条记录)
   - ✅ `assignee` 字段 - 指派工程师
   - ❌ **缺少 `creator_id` 字段** - 发起人/申请人
   - ❌ **缺少 `creator_name` 字段** - 发起人姓名

2. **engineers表** (1条记录)
   - ✅ `user_id` - 飞书user_id
   - ✅ `name` - 工程师姓名
   - ✅ `department_name` - 部门名称
   - ✅ `mobile`, `email` - 联系方式

3. **权限系统** (Phase 4.5已实现)
   - ✅ 基础权限验证 (`resource:action`格式)
   - ✅ `@require_permission` 装饰器
   - ✅ 前端权限控制组件 (PermissionWrapper)
   - ❌ **没有角色管理系统**

4. **Identity Hub**
   - ✅ OAuth认证集成
   - ✅ 基础权限表 `cross_app_permissions`
   - ✅ 用户信息同步

#### ❌ 缺失部分

1. **tasks表**: 缺少`creator_id`, `creator_name`字段
2. **角色系统**: 没有`roles`, `user_roles`表
3. **权限管理UI**: 没有权限管理页面
4. **数据范围控制**: 没有实现数据过滤逻辑

### 1.2 飞书原始数据验证

**✅ 好消息**: 飞书原始数据中**确实包含发起人信息**！

```json
{
  "发起人": [
    {
      "id": "ou_ad883f9af7460763443f4b8b234e25b2",
      "name": "张健",
      "avatar_url": "...",
      "email": "",
      "en_name": "张健"
    }
  ],
  "提交人": [...],  // 也可用作发起人
  "售后工程师": [...]  // 当前已使用(assignee)
}
```

**问题**: 数据同步时未提取发起人字段，`process_feishu_data.py`中没有配置`CREATOR_FIELD`。

---

## 二、设计目标

### 2.1 核心需求

实现**三级权限体系**:

| 角色 | 权限 | 数据范围 |
|------|------|----------|
| **系统管理员** | 分配用户角色、查看所有数据 | 全部数据 |
| **管理者** | 查看和操作所有数据 | 全部数据 |
| **普通人员** | 仅查看和操作自己相关的数据 | 自己相关（assignee=自己 OR creator_id=自己）|

### 2.2 功能需求

1. **用户管理页面** (仅系统管理员可访问)
   - 用户列表展示（姓名、部门、角色）
   - 角色分配（下拉选择+保存）
   - 用户搜索和过滤
   - 权限预览

2. **数据范围过滤**
   - 后端API自动过滤数据
   - 普通人员只能看到：
     - 自己作为**指派工程师**的任务
     - 自己作为**发起人**的任务

3. **角色管理**
   - 3个预定义角色
   - 角色权限配置
   - 数据范围配置

---

## 三、数据库设计

### 3.1 添加tasks表字段

```sql
-- 添加发起人字段
ALTER TABLE tasks ADD COLUMN creator_id TEXT;       -- 发起人user_id（飞书）
ALTER TABLE tasks ADD COLUMN creator_name TEXT;     -- 发起人姓名（冗余字段，方便查询）

-- 创建索引
CREATE INDEX idx_tasks_creator ON tasks(creator_id);
```

**字段说明**:
- `creator_id`: 从飞书`发起人[0].id`提取
- `creator_name`: 从飞书`发起人[0].name`提取

### 3.2 创建roles表（角色定义）

```sql
CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_key TEXT UNIQUE NOT NULL,           -- 角色标识: 'system_admin', 'manager', 'regular_user'
    role_name TEXT NOT NULL,                  -- 角色名称: '系统管理员', '管理者', '普通人员'
    description TEXT,                         -- 角色描述
    permissions TEXT,                         -- JSON数组: ["task:create", "task:read", ...]
    data_scope TEXT DEFAULT 'all',            -- 数据范围: 'all'(全部), 'self'(仅自己相关)
    is_system BOOLEAN DEFAULT 0,              -- 是否系统内置角色（不可删除）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_roles_key ON roles(role_key);
```

**预设角色数据**:

```sql
INSERT INTO roles (role_key, role_name, description, permissions, data_scope, is_system) VALUES
-- 系统管理员
('system_admin', '系统管理员', '可以管理用户权限，查看所有数据',
 '["task:*", "user:*", "role:*", "approval:*"]', 'all', 1),

-- 管理者
('manager', '管理者', '可以查看和操作所有派工数据',
 '["task:create", "task:read", "task:update", "task:delete", "approval:read", "approval:create"]', 'all', 1),

-- 普通人员
('regular_user', '普通人员', '只能查看和操作自己相关的派工',
 '["task:read", "task:update"]', 'self', 1);
```

### 3.3 创建user_roles表（用户角色关联）

```sql
CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,                    -- 飞书user_id
    role_id INTEGER NOT NULL,                 -- 角色ID
    assigned_by TEXT,                         -- 分配人user_id
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    UNIQUE(user_id, role_id)                  -- 一个用户一个角色类型只能分配一次
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
```

**说明**:
- 一个用户可以有多个角色
- 权限取并集
- 数据范围取最宽的（all > self）

---

## 四、后端API设计

### 4.1 角色管理API (`backend/routers/roles.py`)

#### 1. GET /api/roles
**功能**: 获取所有角色列表
**权限**: 任何登录用户
**返回**:
```json
{
  "roles": [
    {
      "id": 1,
      "role_key": "system_admin",
      "role_name": "系统管理员",
      "description": "可以管理用户权限，查看所有数据",
      "permissions": ["task:*", "user:*", "role:*"],
      "data_scope": "all",
      "is_system": true
    },
    ...
  ]
}
```

#### 2. GET /api/roles/{id}
**功能**: 获取角色详情
**权限**: `role:read`

#### 3. POST /api/roles
**功能**: 创建自定义角色
**权限**: `role:create` (系统管理员)
**请求**:
```json
{
  "role_key": "custom_role",
  "role_name": "自定义角色",
  "description": "描述",
  "permissions": ["task:read"],
  "data_scope": "self"
}
```

#### 4. PUT /api/roles/{id}
**功能**: 修改角色
**权限**: `role:update` (系统管理员)
**限制**: 系统内置角色(`is_system=1`)不可修改

#### 5. DELETE /api/roles/{id}
**功能**: 删除角色
**权限**: `role:delete` (系统管理员)
**限制**: 系统内置角色不可删除

---

### 4.2 用户管理API (`backend/routers/users.py`)

#### 1. GET /api/users
**功能**: 获取用户列表（支持分页、搜索）
**权限**: `user:read` (系统管理员)
**参数**:
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20）
- `search`: 搜索关键词（姓名/邮箱）
- `department`: 部门筛选
- `role`: 角色筛选

**返回**:
```json
{
  "users": [
    {
      "user_id": "ou_xxx",
      "name": "张三",
      "email": "zhangsan@example.com",
      "mobile": "13800138000",
      "department_name": "技术部",
      "roles": [
        {"role_id": 3, "role_name": "普通人员"}
      ],
      "status": 1
    },
    ...
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

#### 2. GET /api/users/{user_id}
**功能**: 获取用户详情（含角色和权限）
**权限**: `user:read`
**返回**:
```json
{
  "user_id": "ou_xxx",
  "name": "张三",
  "email": "...",
  "mobile": "...",
  "department_name": "技术部",
  "roles": [
    {
      "role_id": 3,
      "role_key": "regular_user",
      "role_name": "普通人员",
      "assigned_at": "2025-11-03T10:00:00"
    }
  ],
  "permissions": ["task:read", "task:update"],
  "data_scope": "self"
}
```

#### 3. PUT /api/users/{user_id}/roles
**功能**: 分配用户角色
**权限**: `user:update` (系统管理员)
**请求**:
```json
{
  "role_ids": [2, 3]  // 分配"管理者"和"普通人员"角色
}
```

#### 4. GET /api/users/{user_id}/permissions
**功能**: 获取用户权限列表
**权限**: `user:read`
**返回**:
```json
{
  "user_id": "ou_xxx",
  "roles": ["管理者"],
  "permissions": ["task:create", "task:read", "task:update", "task:delete"],
  "data_scope": "all"
}
```

---

### 4.3 数据范围过滤中间件 (`backend/auth_data_scope.py`)

#### 核心函数

```python
def get_user_role_info(user_id: str) -> Dict[str, Any]:
    """
    获取用户角色信息（包括权限和数据范围）

    Returns:
        {
            "roles": ["系统管理员"],
            "role_keys": ["system_admin"],
            "permissions": ["task:*", ...],
            "data_scope": "all"  # all或self
        }
    """
    # 1. 查询user_roles表获取用户所有角色
    # 2. 合并所有角色的权限
    # 3. 取最宽的数据范围（all > self）
    pass


def apply_data_scope(user_id: str, base_query: str) -> str:
    """
    根据用户角色自动添加数据过滤条件

    Args:
        user_id: 用户ID
        base_query: 基础SQL查询

    Returns:
        添加了过滤条件的SQL
    """
    role_info = get_user_role_info(user_id)

    if role_info["data_scope"] == "all":
        # 系统管理员或管理者 - 无限制
        return base_query

    elif role_info["data_scope"] == "self":
        # 普通人员 - 只能查看自己相关的
        # WHERE (assignee = 'user_id' OR creator_id = 'user_id')
        return add_self_filter(base_query, user_id)
```

#### 应用到现有API

```python
# 修改 main.py 或 routers/tasks.py 的查询接口
@router.get("/api/tasks")
async def get_tasks(request: Request, date: str = None):
    user_id = get_current_user_id(request)

    # 构建基础查询
    base_query = "SELECT * FROM tasks WHERE date = ?"

    # 应用数据范围过滤
    filtered_query = apply_data_scope(user_id, base_query)

    # 执行查询
    tasks = execute_query(filtered_query, [date])
    return tasks
```

---

## 五、前端UI设计

### 5.1 用户管理页面 (`frontend/src/components/UserManagement.js`)

#### 功能设计

1. **用户列表展示**
   - 表格展示：姓名、部门、当前角色、操作
   - 分页（20条/页）
   - 搜索框（按姓名、邮箱）
   - 部门筛选下拉框
   - 角色筛选下拉框

2. **角色分配**
   - 点击"分配角色"按钮 → 弹出对话框
   - 单选角色（或多选，支持多角色）
   - 显示角色权限预览
   - 保存后刷新列表

3. **同步功能**
   - "从Identity Hub同步"按钮
   - 同步所有用户信息到engineers表

#### UI布局

```
┌────────────────────────────────────────────────────────────┐
│ 用户管理                                 [+ 从Hub同步用户]  │
│────────────────────────────────────────────────────────────│
│ 🔍 搜索: [________________]  部门: [全部▼]  角色: [全部▼] │
│────────────────────────────────────────────────────────────│
│ 姓名      │ 部门      │ 当前角色      │ 最后登录     │ 操作 │
│────────────────────────────────────────────────────────────│
│ 张三      │ 技术部    │ 普通人员      │ 2小时前      │ [分配角色] │
│ 李四      │ 运维部    │ 管理者        │ 1天前        │ [分配角色] │
│ 王五      │ 技术部    │ 系统管理员    │ 刚刚         │ [分配角色] │
│────────────────────────────────────────────────────────────│
│ 共3个用户                              < 1 2 3 > 第1/5页   │
└────────────────────────────────────────────────────────────┘
```

#### 核心代码结构

```jsx
function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDepartment, setSelectedDepartment] = useState('');
  const [page, setPage] = useState(1);
  const [showRoleDialog, setShowRoleDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // 获取用户列表
  const fetchUsers = async () => {
    const params = {
      page,
      page_size: 20,
      search: searchTerm,
      department: selectedDepartment
    };
    const response = await api.get('/api/users', { params });
    setUsers(response.data.users);
  };

  // 打开角色分配对话框
  const handleAssignRole = (user) => {
    setSelectedUser(user);
    setShowRoleDialog(true);
  };

  return (
    <div className="user-management">
      {/* 搜索和筛选区域 */}
      <div className="filters">
        <input
          type="text"
          placeholder="搜索用户..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <select onChange={(e) => setSelectedDepartment(e.target.value)}>
          <option value="">全部部门</option>
          {/* 部门列表 */}
        </select>
      </div>

      {/* 用户表格 */}
      <table className="user-table">
        <thead>
          <tr>
            <th>姓名</th>
            <th>部门</th>
            <th>当前角色</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <tr key={user.user_id}>
              <td>{user.name}</td>
              <td>{user.department_name}</td>
              <td>{user.roles.map(r => r.role_name).join(', ')}</td>
              <td>
                <button onClick={() => handleAssignRole(user)}>
                  分配角色
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* 角色分配对话框 */}
      {showRoleDialog && (
        <RoleAssignDialog
          user={selectedUser}
          onClose={() => setShowRoleDialog(false)}
          onSave={() => {
            setShowRoleDialog(false);
            fetchUsers();
          }}
        />
      )}
    </div>
  );
}
```

---

### 5.2 角色分配对话框 (`frontend/src/components/RoleAssignDialog.js`)

#### 功能设计

1. **角色选择**
   - 单选框或复选框（支持多角色）
   - 显示角色描述
   - 当前角色高亮显示

2. **权限预览**
   - 显示所选角色的权限列表
   - 显示数据范围（全部/仅自己）

3. **保存逻辑**
   - 调用 `PUT /api/users/{id}/roles`
   - 成功后刷新父组件
   - 失败显示错误提示

#### UI布局

```
┌───────────────────────────────────────────┐
│ 为 "张三" 分配角色                  [×]   │
│───────────────────────────────────────────│
│ 当前角色: 普通人员                        │
│                                            │
│ 选择新角色:                                │
│ ○ 系统管理员                              │
│   - 可以管理用户权限，查看所有数据        │
│                                            │
│ ● 管理者                                  │
│   - 可以查看和操作所有派工数据            │
│                                            │
│ ○ 普通人员                                │
│   - 只能查看和操作自己相关的派工          │
│                                            │
│───────────────────────────────────────────│
│ 权限预览:                                  │
│ ✓ 创建派工 (task:create)                 │
│ ✓ 查看派工 (task:read)                   │
│ ✓ 修改派工 (task:update)                 │
│ ✓ 删除派工 (task:delete)                 │
│ ✓ 查看审批 (approval:read)               │
│ ✓ 创建审批 (approval:create)             │
│                                            │
│ 数据范围: 全部数据                         │
│                                            │
│               [取消]    [确定保存]        │
└───────────────────────────────────────────┘
```

#### 核心代码结构

```jsx
function RoleAssignDialog({ user, onClose, onSave }) {
  const [roles, setRoles] = useState([]);
  const [selectedRoleId, setSelectedRoleId] = useState(null);
  const [selectedRole, setSelectedRole] = useState(null);

  // 获取所有角色
  useEffect(() => {
    api.get('/api/roles').then(response => {
      setRoles(response.data.roles);
      // 设置用户当前角色为默认选中
      if (user.roles.length > 0) {
        setSelectedRoleId(user.roles[0].role_id);
      }
    });
  }, []);

  // 更新选中角色的详情
  useEffect(() => {
    const role = roles.find(r => r.id === selectedRoleId);
    setSelectedRole(role);
  }, [selectedRoleId, roles]);

  // 保存角色分配
  const handleSave = async () => {
    try {
      await api.put(`/api/users/${user.user_id}/roles`, {
        role_ids: [selectedRoleId]
      });
      message.success('角色分配成功');
      onSave();
    } catch (error) {
      message.error('角色分配失败: ' + error.message);
    }
  };

  return (
    <div className="role-assign-dialog">
      <div className="dialog-header">
        <h3>为 "{user.name}" 分配角色</h3>
        <button onClick={onClose}>×</button>
      </div>

      <div className="dialog-body">
        <div className="current-role">
          当前角色: {user.roles.map(r => r.role_name).join(', ')}
        </div>

        <div className="role-list">
          <h4>选择新角色:</h4>
          {roles.map(role => (
            <label key={role.id} className="role-option">
              <input
                type="radio"
                name="role"
                value={role.id}
                checked={selectedRoleId === role.id}
                onChange={() => setSelectedRoleId(role.id)}
              />
              <div>
                <strong>{role.role_name}</strong>
                <p>{role.description}</p>
              </div>
            </label>
          ))}
        </div>

        {selectedRole && (
          <div className="permission-preview">
            <h4>权限预览:</h4>
            <ul>
              {JSON.parse(selectedRole.permissions).map(perm => (
                <li key={perm}>✓ {perm}</li>
              ))}
            </ul>
            <div className="data-scope">
              数据范围: {selectedRole.data_scope === 'all' ? '全部数据' : '仅自己相关'}
            </div>
          </div>
        )}
      </div>

      <div className="dialog-footer">
        <button onClick={onClose}>取消</button>
        <button onClick={handleSave} className="btn-primary">
          确定保存
        </button>
      </div>
    </div>
  );
}
```

---

## 六、权限控制逻辑

### 6.1 页面访问权限

#### 路由保护

```jsx
// App.js
import { PermissionRoute } from './components/PermissionWrapper';
import UserManagement from './components/UserManagement';

function App() {
  return (
    <Router>
      <Routes>
        {/* 用户管理页面 - 仅系统管理员可访问 */}
        <Route
          path="/admin/users"
          element={
            <PermissionRoute
              permission="user:read"
              component={UserManagement}
              fallback={<AccessDenied />}
            />
          }
        />

        {/* 其他路由 */}
      </Routes>
    </Router>
  );
}
```

#### 菜单显示控制

```jsx
// Header.js
import { hasPermission } from '../utils/permission';

function Header() {
  return (
    <nav>
      <Link to="/">首页</Link>
      <Link to="/tasks">任务列表</Link>

      {/* 仅系统管理员可见 */}
      {hasPermission('user:read') && (
        <Link to="/admin/users">用户管理</Link>
      )}
    </nav>
  );
}
```

### 6.2 API数据过滤

#### 自动过滤逻辑

```python
# backend/routers/tasks.py
from auth_data_scope import apply_data_scope, get_user_role_info

@router.get("/api/tasks")
async def get_tasks(
    request: Request,
    date: str = None,
    assignee: str = None
):
    # 1. 获取当前用户
    user_id = get_current_user_id(request)

    # 2. 获取用户角色信息
    role_info = get_user_role_info(user_id)

    # 3. 构建基础查询
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if date:
        query += " AND date = ?"
        params.append(date)

    if assignee:
        query += " AND assignee = ?"
        params.append(assignee)

    # 4. 应用数据范围过滤
    if role_info["data_scope"] == "self":
        # 普通人员 - 只能看自己相关的
        query += " AND (assignee = ? OR creator_id = ?)"
        params.extend([user_id, user_id])

    # 5. 执行查询
    tasks = execute_query(query, params)

    return {"tasks": tasks}
```

---

## 七、数据同步改造

### 7.1 修改process_feishu_data.py

#### 添加发起人字段配置

```python
# 在配置部分添加
CREATOR_FIELD = "发起人"  # 发起人字段
# 或
SUBMITTER_FIELD = "提交人"  # 提交人字段（备选）
```

#### 添加提取函数

```python
def extract_creator(creator_field: Any) -> tuple[str, str]:
    """
    提取发起人信息

    Args:
        creator_field: 发起人字段（列表或字典）

    Returns:
        (creator_id, creator_name) 元组
    """
    if isinstance(creator_field, list) and len(creator_field) > 0:
        creator = creator_field[0]
        if isinstance(creator, dict):
            return (
                creator.get("id", ""),
                creator.get("name", "未知发起人")
            )

    elif isinstance(creator_field, dict):
        return (
            creator_field.get("id", ""),
            creator_field.get("name", "未知发起人")
        )

    return ("", "未知发起人")
```

#### 修改create_task_item函数

```python
def create_task_item(
    record_id: str,
    fields: Dict[str, Any],
    date: str,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    # ... 现有代码 ...

    # 提取发起人
    creator_id, creator_name = extract_creator(fields.get(CREATOR_FIELD))

    return {
        "record_id": record_id,
        "task_name": task_name,
        "assignee": assignee,
        "creator_id": creator_id,           # 新增
        "creator_name": creator_name,       # 新增
        "status": status,
        "priority": priority,
        # ... 其他字段 ...
    }
```

### 7.2 修改task_db.py

```python
# 修改save_processed_tasks_to_db函数
def save_processed_tasks_to_db(tasks: List[Dict[str, Any]]) -> int:
    """保存处理后的任务到tasks表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO tasks (
                record_id, task_name, assignee, creator_id, creator_name,
                status, priority, application_status,
                date, start_date, end_date, weekday,
                approval_instance_code, approval_status, approval_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)

        # ... 执行插入 ...
```

---

## 八、实施步骤

### Phase 1: 数据库迁移 (1小时)
1. ✅ 创建roles表
2. ✅ 创建user_roles表
3. ✅ 插入3个默认角色
4. ✅ 添加tasks.creator_id和creator_name字段
5. ✅ 创建索引

### Phase 2: 数据同步改造 (2小时)
1. ✅ 修改process_feishu_data.py添加CREATOR_FIELD配置
2. ✅ 添加extract_creator函数
3. ✅ 修改create_task_item函数
4. ✅ 修改task_db.py保存逻辑
5. ✅ 重新同步数据补充发起人信息

### Phase 3: 后端角色管理API (4小时)
1. ✅ 创建routers/roles.py
2. ✅ 实现角色CRUD API
3. ✅ 创建routers/users.py
4. ✅ 实现用户列表和角色分配API
5. ✅ 添加权限装饰器保护

### Phase 4: 数据范围过滤 (2小时)
1. ✅ 创建auth_data_scope.py
2. ✅ 实现get_user_role_info函数
3. ✅ 实现apply_data_scope函数
4. ✅ 修改现有task查询API集成过滤

### Phase 5: 前端用户管理页面 (6小时)
1. ✅ 创建UserManagement.js组件
2. ✅ 实现用户列表展示和搜索
3. ✅ 创建RoleAssignDialog.js组件
4. ✅ 实现角色分配功能
5. ✅ 添加权限预览

### Phase 6: 前端路由和权限控制 (2小时)
1. ✅ 添加/admin/users路由
2. ✅ 在Header中添加"用户管理"菜单
3. ✅ 应用PermissionRoute保护
4. ✅ 测试权限控制

### Phase 7: 测试和验证 (2小时)
1. ✅ 测试系统管理员分配角色
2. ✅ 测试管理者查看所有数据
3. ✅ 测试普通人员数据过滤
4. ✅ 端到端测试

---

## 九、技术要点

### 9.1 角色判断优先级

当用户有多个角色时：
1. **权限**: 取所有角色权限的**并集**
2. **数据范围**: 取最宽的范围（`all` > `self`）

```python
def get_effective_data_scope(user_roles: List[str]) -> str:
    """获取有效数据范围"""
    for role in user_roles:
        if role.data_scope == "all":
            return "all"  # 只要有一个all，就返回all
    return "self"
```

### 9.2 数据过滤SQL模板

```python
# 普通人员数据过滤
WHERE (assignee = '{user_id}' OR creator_id = '{user_id}')

# 示例：查询2025-11-03的任务
SELECT * FROM tasks
WHERE date = '2025-11-03'
  AND (assignee = 'ou_xxx' OR creator_id = 'ou_xxx')
```

### 9.3 系统管理员保护

```python
def can_modify_user_role(operator_user_id: str, target_user_id: str) -> bool:
    """检查是否可以修改用户角色"""
    # 1. 检查操作者是否是系统管理员
    if not is_system_admin(operator_user_id):
        return False

    # 2. 检查目标用户是否是最后一个系统管理员
    if is_last_system_admin(target_user_id):
        raise ValueError("不能删除最后一个系统管理员")

    return True
```

### 9.4 前端权限缓存

```javascript
// 登录后缓存用户信息和权限
localStorage.setItem('userInfo', JSON.stringify({
  user_id: 'ou_xxx',
  name: '张三',
  roles: ['系统管理员'],
  permissions: ['task:*', 'user:*', ...],
  data_scope: 'all'
}));

// 使用权限
import { getUserPermissions, hasPermission } from './utils/permission';

if (hasPermission('user:read')) {
  // 显示用户管理菜单
}
```

---

## 十、安全考虑

### 10.1 安全原则

1. **后端强制验证**: 所有权限检查在后端完成，前端UI仅用于用户体验
2. **默认拒绝**: 未授权时默认拒绝访问
3. **最小权限**: 只给用户必需的最小权限
4. **审计日志**: 记录所有角色分配操作

### 10.2 防护措施

1. **SQL注入防护**: 使用参数化查询
2. **权限绕过防护**: API强制验证权限
3. **会话劫持防护**: HttpOnly cookie
4. **CSRF防护**: state参数验证

### 10.3 审计日志

```sql
-- 创建审计日志表
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,           -- 'assign_role', 'remove_role'
    target_user_id TEXT,
    details TEXT,                    -- JSON格式详情
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 十一、测试用例

### 11.1 角色分配测试

| 测试场景 | 操作 | 预期结果 |
|---------|------|----------|
| 系统管理员分配角色 | 给用户A分配"管理者"角色 | ✅ 成功 |
| 普通用户分配角色 | 尝试分配角色 | ❌ 403 权限不足 |
| 删除最后系统管理员 | 删除唯一系统管理员角色 | ❌ 禁止操作 |

### 11.2 数据过滤测试

| 用户角色 | 查询条件 | 预期结果 |
|---------|---------|----------|
| 系统管理员 | 查询所有任务 | 返回全部365条 |
| 管理者 | 查询所有任务 | 返回全部365条 |
| 普通人员(张三) | 查询所有任务 | 仅返回assignee=张三 OR creator_id=张三的任务 |

### 11.3 权限控制测试

| 用户角色 | 访问页面 | 预期结果 |
|---------|---------|----------|
| 系统管理员 | /admin/users | ✅ 可访问 |
| 管理者 | /admin/users | ❌ 403 权限不足 |
| 普通人员 | /admin/users | ❌ 403 权限不足 |

---

## 十二、工作量估算

| 阶段 | 任务数 | 文件数 | 代码量 | 工作量 |
|------|--------|--------|--------|--------|
| Phase 1: 数据库迁移 | 5个 | 1个SQL | ~100行 | 1小时 |
| Phase 2: 数据同步改造 | 4个 | 3个.py | ~150行 | 2小时 |
| Phase 3: 后端角色API | 5个 | 2个.py | ~600行 | 4小时 |
| Phase 4: 数据范围过滤 | 4个 | 1个.py | ~200行 | 2小时 |
| Phase 5: 前端用户管理 | 5个 | 2个.js | ~800行 | 6小时 |
| Phase 6: 路由和权限 | 4个 | 2个.js | ~100行 | 2小时 |
| Phase 7: 测试验证 | 4个 | - | - | 2小时 |
| **总计** | **31个任务** | **11个文件** | **~1950行** | **~19小时** |

---

## 十三、后续优化建议

### 13.1 功能增强
- [ ] 支持部门级数据范围（data_scope='department'）
- [ ] 支持自定义角色创建
- [ ] 支持权限委托和临时权限
- [ ] 添加权限申请流程

### 13.2 性能优化
- [ ] 使用Redis缓存角色权限
- [ ] 实现权限变更时自动清理缓存
- [ ] 优化SQL查询性能
- [ ] 实现权限预加载

### 13.3 用户体验
- [ ] 权限不足时友好提示
- [ ] 权限管理帮助文档
- [ ] 权限状态可视化
- [ ] 批量角色分配

---

## 十四、附录

### 14.1 数据库ER图

```
┌─────────────┐        ┌──────────────┐        ┌─────────────┐
│   users     │        │  user_roles  │        │    roles    │
├─────────────┤        ├──────────────┤        ├─────────────┤
│ user_id(PK) │────┐   │ id (PK)      │   ┌────│ id (PK)     │
│ name        │    └───│ user_id (FK) │───┘    │ role_key    │
│ email       │        │ role_id (FK) │        │ role_name   │
│ mobile      │        │ assigned_by  │        │ permissions │
│ ...         │        │ assigned_at  │        │ data_scope  │
└─────────────┘        └──────────────┘        └─────────────┘
                                                      │
                                                      │
┌─────────────┐                                      │
│    tasks    │                                      │
├─────────────┤                                      │
│ id (PK)     │                                      │
│ assignee    │──────── 指派工程师                   │
│ creator_id  │──────── 发起人(NEW)                 │
│ creator_name│──────── 发起人姓名(NEW)              │
│ ...         │                                      │
└─────────────┘                                      │
       │                                             │
       └──── 数据过滤: WHERE (assignee=X OR creator_id=X)
```

### 14.2 权限矩阵

| 资源/操作 | system_admin | manager | regular_user |
|-----------|-------------|---------|--------------|
| task:create | ✅ | ✅ | ❌ |
| task:read | ✅ | ✅ | ✅ (仅自己) |
| task:update | ✅ | ✅ | ✅ (仅自己) |
| task:delete | ✅ | ✅ | ❌ |
| user:read | ✅ | ❌ | ❌ |
| user:update | ✅ | ❌ | ❌ |
| role:* | ✅ | ❌ | ❌ |

### 14.3 API端点汇总

**角色管理**:
- GET /api/roles
- GET /api/roles/{id}
- POST /api/roles
- PUT /api/roles/{id}
- DELETE /api/roles/{id}

**用户管理**:
- GET /api/users
- GET /api/users/{id}
- PUT /api/users/{id}/roles
- GET /api/users/{id}/permissions

**任务查询**（自动数据过滤）:
- GET /api/tasks
- GET /api/tasks/{id}
- POST /api/tasks
- PUT /api/tasks/{id}
- DELETE /api/tasks/{id}

---

**文档版本**: v1.0
**创建日期**: 2025-11-03
**维护人**: 张健
**审核人**: -

**下一步**: 创建详细任务清单，开始Phase 1实施
