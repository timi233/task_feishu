# 权限管理系统实施任务清单

**日期**: 2025-11-03
**版本**: v1.0
**状态**: 🚧 进行中
**关联设计文档**: `PERMISSION_MANAGEMENT_DESIGN_2025-11-03.md`

---

## 📊 任务统计

- **总任务数**: 31个
- **已完成**: 0个
- **进行中**: 0个
- **待开始**: 31个
- **预估总工时**: ~19小时

---

## Phase 1: 数据库迁移与字段添加 (1小时)

### 任务1.1: 添加tasks表creator字段
**状态**: ⏸️ 待开始
**文件**: `backend/migrations/add_creator_fields_to_tasks.py`
**描述**: 添加creator_id和creator_name字段到tasks表
**SQL**:
```sql
ALTER TABLE tasks ADD COLUMN creator_id TEXT;
ALTER TABLE tasks ADD COLUMN creator_name TEXT;
CREATE INDEX idx_tasks_creator ON tasks(creator_id);
```
**验收标准**:
- [ ] tasks表包含creator_id字段
- [ ] tasks表包含creator_name字段
- [ ] 索引idx_tasks_creator已创建
- [ ] 运行`python migrations/add_creator_fields_to_tasks.py`成功

**预估工时**: 15分钟

---

### 任务1.2: 创建roles表
**状态**: ⏸️ 待开始
**文件**: `backend/migrations/create_roles_table.py`
**描述**: 创建角色定义表
**SQL**:
```sql
CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_key TEXT UNIQUE NOT NULL,
    role_name TEXT NOT NULL,
    description TEXT,
    permissions TEXT,
    data_scope TEXT DEFAULT 'all',
    is_system BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_roles_key ON roles(role_key);
```
**验收标准**:
- [ ] roles表已创建
- [ ] 包含所有必需字段
- [ ] 索引已创建

**预估工时**: 15分钟

---

### 任务1.3: 创建user_roles表
**状态**: ⏸️ 待开始
**文件**: `backend/migrations/create_user_roles_table.py`
**描述**: 创建用户角色关联表
**SQL**:
```sql
CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    assigned_by TEXT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    UNIQUE(user_id, role_id)
);
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
```
**验收标准**:
- [ ] user_roles表已创建
- [ ] 外键约束正确
- [ ] UNIQUE约束正确
- [ ] 索引已创建

**预估工时**: 15分钟

---

### 任务1.4: 插入默认角色数据
**状态**: ⏸️ 待开始
**文件**: `backend/migrations/insert_default_roles.py`
**描述**: 插入3个预定义角色
**SQL**:
```sql
INSERT INTO roles (role_key, role_name, description, permissions, data_scope, is_system) VALUES
('system_admin', '系统管理员', '可以管理用户权限，查看所有数据',
 '["task:*", "user:*", "role:*", "approval:*"]', 'all', 1),
('manager', '管理者', '可以查看和操作所有派工数据',
 '["task:create", "task:read", "task:update", "task:delete", "approval:read", "approval:create"]', 'all', 1),
('regular_user', '普通人员', '只能查看和操作自己相关的派工',
 '["task:read", "task:update"]', 'self', 1);
```
**验收标准**:
- [ ] 3个角色插入成功
- [ ] 角色信息完整
- [ ] `SELECT * FROM roles`返回3条记录

**预估工时**: 10分钟

---

### 任务1.5: 验证数据库结构
**状态**: ⏸️ 待开始
**描述**: 验证所有表和字段创建成功
**操作**:
```bash
sqlite3 ./data/db/tasks.db << 'EOF'
.tables
PRAGMA table_info(tasks);
PRAGMA table_info(roles);
PRAGMA table_info(user_roles);
SELECT COUNT(*) FROM roles;
EOF
```
**验收标准**:
- [ ] tasks表包含creator_id和creator_name
- [ ] roles表存在且有3条记录
- [ ] user_roles表存在
- [ ] 所有索引已创建

**预估工时**: 5分钟

---

## Phase 2: 数据同步改造 (2小时)

### 任务2.1: 修改process_feishu_data.py添加CREATOR_FIELD
**状态**: ⏸️ 待开始
**文件**: `backend/process_feishu_data.py`
**描述**: 在字段映射配置中添加发起人字段
**修改位置**: 第10-23行（配置部分）
**代码**:
```python
# 添加到配置部分
CREATOR_FIELD = "发起人"  # 发起人字段
```
**验收标准**:
- [ ] CREATOR_FIELD配置已添加
- [ ] 配置注释清晰

**预估工时**: 5分钟

---

### 任务2.2: 添加extract_creator函数
**状态**: ⏸️ 待开始
**文件**: `backend/process_feishu_data.py`
**描述**: 实现发起人信息提取函数
**插入位置**: 第104行后（extract_assignee函数之后）
**代码**:
```python
def extract_creator(creator_field: Any) -> tuple[str, str]:
    """
    提取发起人信息

    Args:
        creator_field: 发起人字段（可能是列表/字典/None）

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
**验收标准**:
- [ ] 函数实现正确
- [ ] 处理列表、字典、None三种情况
- [ ] 返回元组格式

**预估工时**: 15分钟

---

### 任务2.3: 修改create_task_item函数
**状态**: ⏸️ 待开始
**文件**: `backend/process_feishu_data.py`
**描述**: 在create_task_item函数中提取和返回发起人信息
**修改位置**: 第169行（提取负责人之后）
**代码**:
```python
# 提取发起人（新增）
creator_id, creator_name = extract_creator(fields.get(CREATOR_FIELD))
```
**修改位置**: 第183-196行（return语句）
**代码**:
```python
return {
    "record_id": record_id,
    "task_name": task_name,
    "assignee": assignee,
    "creator_id": creator_id,           # 新增
    "creator_name": creator_name,       # 新增
    "status": status,
    "priority": priority,
    "application_status": application_status,
    "date": date,
    "start_date": start_date,
    "end_date": end_date,
    "weekday": weekday,
    "approval_instance_code": approval_instance_code,
    "approval_status": approval_status
}
```
**验收标准**:
- [ ] 调用extract_creator函数
- [ ] 返回字典包含creator_id和creator_name
- [ ] 代码无语法错误

**预估工时**: 10分钟

---

### 任务2.4: 修改task_db.py保存逻辑
**状态**: ⏸️ 待开始
**文件**: `backend/task_db.py`
**描述**: 修改INSERT语句包含creator字段
**修改位置**: `save_processed_tasks_to_db`函数
**代码**:
```python
cursor.execute("""
    INSERT OR REPLACE INTO tasks (
        record_id, task_name, assignee, creator_id, creator_name,
        status, priority, application_status,
        date, start_date, end_date, weekday,
        approval_instance_code, approval_status, approval_type
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    task["record_id"],
    task["task_name"],
    task["assignee"],
    task.get("creator_id", ""),        # 新增
    task.get("creator_name", ""),      # 新增
    task["status"],
    task["priority"],
    task.get("application_status"),
    task["date"],
    task.get("start_date"),
    task.get("end_date"),
    task["weekday"],
    task.get("approval_instance_code"),
    task.get("approval_status"),
    task.get("approval_type", "daily_work")
))
```
**验收标准**:
- [ ] INSERT语句包含creator_id和creator_name
- [ ] 参数绑定正确
- [ ] 使用.get()方法避免KeyError

**预估工时**: 15分钟

---

### 任务2.5: 重新同步数据补充发起人信息
**状态**: ⏸️ 待开始
**描述**: 运行同步脚本，更新现有365条任务的发起人信息
**操作**:
```bash
cd backend
python sync_feishu_to_db.py --once
```
**验收标准**:
- [ ] 同步成功无报错
- [ ] `SELECT COUNT(*) FROM tasks WHERE creator_id IS NOT NULL`返回>0
- [ ] 随机抽查几条记录，creator_name正确

**预估工时**: 30分钟（含调试）

---

## Phase 3: 后端角色管理API (4小时)

### 任务3.1: 创建routers/roles.py基础结构
**状态**: ⏸️ 待开始
**文件**: `backend/routers/roles.py` (新建)
**描述**: 创建角色管理路由模块骨架
**代码结构**:
```python
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/roles", tags=["Roles"])

# Pydantic模型
class RoleResponse(BaseModel):
    id: int
    role_key: str
    role_name: str
    description: Optional[str]
    permissions: List[str]
    data_scope: str
    is_system: bool

# API端点
@router.get("", response_model=List[RoleResponse])
async def list_roles():
    """获取所有角色列表"""
    pass

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(role_id: int):
    """获取角色详情"""
    pass

# ... 其他端点
```
**验收标准**:
- [ ] 文件创建成功
- [ ] 导入正确
- [ ] Pydantic模型定义完整

**预估工时**: 30分钟

---

### 任务3.2: 实现角色CRUD API
**状态**: ⏸️ 待开始
**文件**: `backend/routers/roles.py`
**描述**: 实现5个角色管理端点
**端点**:
1. GET /api/roles - 列表
2. GET /api/roles/{id} - 详情
3. POST /api/roles - 创建（需要权限）
4. PUT /api/roles/{id} - 修改（需要权限）
5. DELETE /api/roles/{id} - 删除（需要权限）

**验收标准**:
- [ ] 所有端点实现完成
- [ ] 数据库CRUD操作正确
- [ ] 错误处理完整
- [ ] 返回格式符合Pydantic模型

**预估工时**: 1.5小时

---

### 任务3.3: 创建routers/users.py基础结构
**状态**: ⏸️ 待开始
**文件**: `backend/routers/users.py` (新建)
**描述**: 创建用户管理路由模块
**代码结构**:
```python
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["Users"])

# Pydantic模型
class UserRole(BaseModel):
    role_id: int
    role_name: str

class UserResponse(BaseModel):
    user_id: str
    name: str
    email: Optional[str]
    mobile: Optional[str]
    department_name: Optional[str]
    roles: List[UserRole]
    status: int

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    page_size: int

# API端点
@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None
):
    """获取用户列表（支持分页、搜索）"""
    pass

# ... 其他端点
```
**验收标准**:
- [ ] 文件创建成功
- [ ] Pydantic模型定义完整
- [ ] 路由前缀正确

**预估工时**: 30分钟

---

### 任务3.4: 实现用户列表和角色分配API
**状态**: ⏸️ 待开始
**文件**: `backend/routers/users.py`
**描述**: 实现4个用户管理端点
**端点**:
1. GET /api/users - 用户列表（分页、搜索）
2. GET /api/users/{id} - 用户详情
3. PUT /api/users/{id}/roles - 分配角色
4. GET /api/users/{id}/permissions - 权限列表

**验收标准**:
- [ ] 用户列表支持分页
- [ ] 搜索功能正常（按姓名/邮箱）
- [ ] 角色分配成功写入user_roles表
- [ ] 权限列表合并所有角色权限

**预估工时**: 1.5小时

---

### 任务3.5: 添加权限装饰器保护
**状态**: ⏸️ 待开始
**文件**: `backend/routers/roles.py`, `backend/routers/users.py`
**描述**: 给敏感端点添加@require_permission装饰器
**修改**:
```python
from auth_permission import require_permission

@router.post("")
@require_permission("role:create")
async def create_role(...):
    pass

@router.put("/{role_id}")
@require_permission("role:update")
async def update_role(...):
    pass

@router.delete("/{role_id}")
@require_permission("role:delete")
async def delete_role(...):
    pass

@router.put("/{user_id}/roles")
@require_permission("user:update")
async def assign_user_roles(...):
    pass
```
**验收标准**:
- [ ] 所有写操作端点已保护
- [ ] 读操作端点按需保护
- [ ] 测试无权限访问返回403

**预估工时**: 30分钟

---

### 任务3.6: 在main.py注册路由
**状态**: ⏸️ 待开始
**文件**: `backend/main.py`
**描述**: 将roles和users路由注册到FastAPI app
**代码**:
```python
from routers import roles, users

app.include_router(roles.router)
app.include_router(users.router)
```
**验收标准**:
- [ ] 路由注册成功
- [ ] 访问/docs可见新增端点
- [ ] 端点可正常访问

**预估工时**: 5分钟

---

## Phase 4: 数据范围过滤 (2小时)

### 任务4.1: 创建auth_data_scope.py模块
**状态**: ⏸️ 待开始
**文件**: `backend/auth_data_scope.py` (新建)
**描述**: 创建数据范围过滤中间件
**代码结构**:
```python
import logging
from typing import Dict, Any, List
from task_db import get_db_connection

logger = logging.getLogger(__name__)

def get_user_role_info(user_id: str) -> Dict[str, Any]:
    """获取用户角色信息"""
    pass

def get_effective_data_scope(roles: List[Dict]) -> str:
    """计算有效数据范围（取最宽）"""
    pass

def apply_data_scope(user_id: str, base_conditions: List[str], base_params: List) -> tuple:
    """应用数据范围过滤"""
    pass
```
**验收标准**:
- [ ] 文件创建成功
- [ ] 函数签名正确
- [ ] 导入语句完整

**预估工时**: 20分钟

---

### 任务4.2: 实现get_user_role_info函数
**状态**: ⏸️ 待开始
**文件**: `backend/auth_data_scope.py`
**描述**: 查询用户所有角色并合并权限
**代码**:
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
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. 查询用户所有角色
        cursor.execute("""
            SELECT r.role_key, r.role_name, r.permissions, r.data_scope
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = ?
        """, (user_id,))

        roles = cursor.fetchall()

        if not roles:
            # 没有角色，默认为普通人员
            return {
                "roles": ["普通人员"],
                "role_keys": ["regular_user"],
                "permissions": ["task:read", "task:update"],
                "data_scope": "self"
            }

        # 2. 合并权限
        all_permissions = set()
        role_names = []
        role_keys = []

        for role in roles:
            role_names.append(role["role_name"])
            role_keys.append(role["role_key"])
            permissions = json.loads(role["permissions"])
            all_permissions.update(permissions)

        # 3. 计算有效数据范围（取最宽）
        data_scope = get_effective_data_scope(roles)

        return {
            "roles": role_names,
            "role_keys": role_keys,
            "permissions": list(all_permissions),
            "data_scope": data_scope
        }
```
**验收标准**:
- [ ] 查询所有用户角色
- [ ] 合并权限取并集
- [ ] 数据范围取最宽
- [ ] 处理无角色情况

**预估工时**: 40分钟

---

### 任务4.3: 实现apply_data_scope函数
**状态**: ⏸️ 待开始
**文件**: `backend/auth_data_scope.py`
**描述**: 根据用户角色添加数据过滤条件
**代码**:
```python
def apply_data_scope(
    user_id: str,
    base_conditions: List[str],
    base_params: List
) -> tuple[List[str], List]:
    """
    应用数据范围过滤

    Args:
        user_id: 用户ID
        base_conditions: 基础WHERE条件列表 ['date = ?', 'status = ?']
        base_params: 基础参数列表 ['2025-11-03', 'completed']

    Returns:
        (conditions, params): 添加过滤后的条件和参数
    """
    role_info = get_user_role_info(user_id)

    if role_info["data_scope"] == "all":
        # 系统管理员或管理者 - 无限制
        return (base_conditions, base_params)

    elif role_info["data_scope"] == "self":
        # 普通人员 - 只能查看自己相关的
        self_condition = "(assignee = ? OR creator_id = ?)"
        conditions = base_conditions + [self_condition]
        params = base_params + [user_id, user_id]

        return (conditions, params)

    else:
        # 默认拒绝
        return (base_conditions + ["1=0"], base_params)
```
**验收标准**:
- [ ] all范围不添加过滤
- [ ] self范围添加assignee或creator_id过滤
- [ ] 返回格式正确

**预估工时**: 30分钟

---

### 任务4.4: 修改现有task查询API集成过滤
**状态**: ⏸️ 待开始
**文件**: `backend/main.py` 或 `backend/routers/tasks.py`
**描述**: 在get_tasks等查询端点应用数据范围过滤
**修改**:
```python
from auth_data_scope import apply_data_scope

@router.get("/api/tasks")
async def get_tasks(
    request: Request,
    date: str = None,
    assignee: str = None
):
    # 获取当前用户
    user_id = get_current_user_id(request)

    # 构建基础查询条件
    conditions = []
    params = []

    if date:
        conditions.append("date = ?")
        params.append(date)

    if assignee:
        conditions.append("assignee = ?")
        params.append(assignee)

    # 应用数据范围过滤
    conditions, params = apply_data_scope(user_id, conditions, params)

    # 构建完整SQL
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    query = f"SELECT * FROM tasks WHERE {where_clause}"

    # 执行查询
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        tasks = cursor.fetchall()

    return {"tasks": [dict(t) for t in tasks]}
```
**验收标准**:
- [ ] 系统管理员查询返回全部数据
- [ ] 普通人员只返回自己相关的数据
- [ ] SQL语法正确
- [ ] 无性能问题

**预估工时**: 40分钟

---

## Phase 5: 前端用户管理页面 (6小时)

### 任务5.1: 创建UserManagement.js组件骨架
**状态**: ⏸️ 待开始
**文件**: `frontend/src/components/UserManagement.js` (新建)
**描述**: 创建用户管理页面基础结构
**代码结构**:
```jsx
import React, { useState, useEffect } from 'react';
import api from '../utils/api';
import './UserManagement.css';

function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDepartment, setSelectedDepartment] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchUsers();
  }, [page, searchTerm, selectedDepartment]);

  const fetchUsers = async () => {
    // TODO: 实现
  };

  return (
    <div className="user-management">
      <h2>用户管理</h2>
      {/* TODO: 添加UI */}
    </div>
  );
}

export default UserManagement;
```
**验收标准**:
- [ ] 文件创建成功
- [ ] 基础state定义完整
- [ ] 组件可正常导入

**预估工时**: 20分钟

---

### 任务5.2: 实现用户列表展示和搜索
**状态**: ⏸️ 待开始
**文件**: `frontend/src/components/UserManagement.js`
**描述**: 实现用户列表、搜索、分页功能
**功能**:
1. 用户表格展示
2. 搜索框（实时搜索）
3. 部门筛选下拉框
4. 分页组件

**验收标准**:
- [ ] 表格展示用户信息
- [ ] 搜索功能正常
- [ ] 部门筛选正常
- [ ] 分页切换正常
- [ ] Loading状态显示

**预估工时**: 2小时

---

### 任务5.3: 创建RoleAssignDialog.js组件
**状态**: ⏸️ 待开始
**文件**: `frontend/src/components/RoleAssignDialog.js` (新建)
**描述**: 创建角色分配对话框组件
**代码结构**:
```jsx
import React, { useState, useEffect } from 'react';
import api from '../utils/api';
import './RoleAssignDialog.css';

function RoleAssignDialog({ user, onClose, onSave }) {
  const [roles, setRoles] = useState([]);
  const [selectedRoleId, setSelectedRoleId] = useState(null);
  const [selectedRole, setSelectedRole] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchRoles();
  }, []);

  const fetchRoles = async () => {
    // TODO: 实现
  };

  const handleSave = async () => {
    // TODO: 实现
  };

  return (
    <div className="role-assign-dialog-overlay">
      <div className="role-assign-dialog">
        {/* TODO: 添加UI */}
      </div>
    </div>
  );
}

export default RoleAssignDialog;
```
**验收标准**:
- [ ] 对话框组件创建成功
- [ ] 基础state定义完整
- [ ] 可正常导入和使用

**预估工时**: 30分钟

---

### 任务5.4: 实现角色选择和权限预览
**状态**: ⏸️ 待开始
**文件**: `frontend/src/components/RoleAssignDialog.js`
**描述**: 实现角色选择、权限预览功能
**功能**:
1. 显示所有可用角色（单选）
2. 显示用户当前角色
3. 显示所选角色的权限列表
4. 显示数据范围

**验收标准**:
- [ ] 角色列表显示完整
- [ ] 单选功能正常
- [ ] 权限预览实时更新
- [ ] 数据范围显示正确

**预估工时**: 1.5小时

---

### 任务5.5: 实现角色保存功能
**状态**: ⏸️ 待开始
**文件**: `frontend/src/components/RoleAssignDialog.js`
**描述**: 实现角色分配保存逻辑
**功能**:
1. 调用PUT /api/users/{id}/roles API
2. 成功后刷新父组件
3. 错误处理和提示

**代码**:
```jsx
const handleSave = async () => {
  if (!selectedRoleId) {
    message.error('请选择角色');
    return;
  }

  setSaving(true);
  try {
    await api.put(`/api/users/${user.user_id}/roles`, {
      role_ids: [selectedRoleId]
    });

    message.success('角色分配成功');
    onSave();  // 刷新父组件
  } catch (error) {
    message.error('角色分配失败: ' + error.message);
  } finally {
    setSaving(false);
  }
};
```
**验收标准**:
- [ ] 保存成功刷新列表
- [ ] 错误处理完整
- [ ] Loading状态显示

**预估工时**: 1小时

---

### 任务5.6: 创建CSS样式
**状态**: ⏸️ 待开始
**文件**: `frontend/src/components/UserManagement.css`, `frontend/src/components/RoleAssignDialog.css`
**描述**: 编写用户管理页面样式
**要求**:
- 响应式设计
- 符合系统整体风格
- 对话框居中显示
- 表格样式美观

**验收标准**:
- [ ] 页面布局美观
- [ ] 对话框样式正确
- [ ] 表格样式统一
- [ ] 响应式适配

**预估工时**: 1小时

---

## Phase 6: 前端路由和权限控制 (2小时)

### 任务6.1: 添加/admin/users路由
**状态**: ⏸️ 待开始
**文件**: `frontend/src/App.js`
**描述**: 在路由配置中添加用户管理页面路由
**代码**:
```jsx
import { PermissionRoute } from './components/PermissionWrapper';
import UserManagement from './components/UserManagement';

function App() {
  return (
    <Router>
      <Routes>
        {/* 现有路由 */}

        {/* 用户管理页面 - 仅系统管理员可访问 */}
        <Route
          path="/admin/users"
          element={
            <PermissionRoute
              permission="user:read"
              component={UserManagement}
              fallbackComponent={<AccessDenied />}
            />
          }
        />
      </Routes>
    </Router>
  );
}
```
**验收标准**:
- [ ] 路由配置正确
- [ ] 权限保护生效
- [ ] 访问/admin/users可正常显示

**预估工时**: 15分钟

---

### 任务6.2: 在Header中添加"用户管理"菜单
**状态**: ⏸️ 待开始
**文件**: `frontend/src/components/Header.js`
**描述**: 添加用户管理菜单入口（仅系统管理员可见）
**代码**:
```jsx
import { hasPermission } from '../utils/permission';

function Header() {
  return (
    <nav className="header-nav">
      <Link to="/">首页</Link>
      <Link to="/tasks">任务列表</Link>

      {/* 用户管理菜单 - 仅系统管理员可见 */}
      {hasPermission('user:read') && (
        <Link to="/admin/users" className="admin-link">
          <span>👤</span> 用户管理
        </Link>
      )}

      {/* 其他菜单 */}
    </nav>
  );
}
```
**验收标准**:
- [ ] 系统管理员可见菜单
- [ ] 普通用户不可见
- [ ] 菜单样式正确

**预估工时**: 20分钟

---

### 任务6.3: 创建AccessDenied组件
**状态**: ⏸️ 待开始
**文件**: `frontend/src/components/AccessDenied.js` (新建)
**描述**: 创建权限不足提示页面
**代码**:
```jsx
import React from 'react';
import { Link } from 'react-router-dom';
import './AccessDenied.css';

function AccessDenied() {
  return (
    <div className="access-denied">
      <div className="access-denied-content">
        <h1>🚫 访问受限</h1>
        <p>您没有权限访问此页面。</p>
        <p>如需访问，请联系系统管理员。</p>
        <Link to="/" className="btn-back">返回首页</Link>
      </div>
    </div>
  );
}

export default AccessDenied;
```
**验收标准**:
- [ ] 组件创建成功
- [ ] 样式美观
- [ ] 返回首页按钮正常

**预估工时**: 15分钟

---

### 任务6.4: 测试路由权限控制
**状态**: ⏸️ 待开始
**描述**: 测试不同角色用户访问权限
**测试场景**:
1. 系统管理员访问/admin/users → 正常显示
2. 管理者访问/admin/users → 显示AccessDenied
3. 普通人员访问/admin/users → 显示AccessDenied
4. 未登录访问/admin/users → 跳转到登录

**验收标准**:
- [ ] 所有测试场景通过
- [ ] 权限控制正确
- [ ] 无控制台错误

**预估工时**: 30分钟

---

## Phase 7: 测试和验证 (2小时)

### 任务7.1: 测试系统管理员分配角色功能
**状态**: ⏸️ 待开始
**描述**: 端到端测试角色分配流程
**测试步骤**:
1. 以系统管理员身份登录
2. 访问用户管理页面
3. 选择一个用户点击"分配角色"
4. 选择"管理者"角色
5. 点击保存
6. 验证用户角色已更新

**验收标准**:
- [ ] 角色分配成功
- [ ] 数据库user_roles表有记录
- [ ] 用户列表显示新角色
- [ ] 无错误日志

**预估工时**: 30分钟

---

### 任务7.2: 测试管理者查看所有数据
**状态**: ⏸️ 待开始
**描述**: 验证管理者数据范围
**测试步骤**:
1. 分配某用户为"管理者"
2. 以该用户登录
3. 访问任务列表页面
4. 验证可以看到所有任务（不限于自己相关）

**验收标准**:
- [ ] 管理者可查看所有365条任务
- [ ] 可以查看其他工程师的任务
- [ ] 数据过滤未生效（data_scope=all）

**预估工时**: 20分钟

---

### 任务7.3: 测试普通人员数据过滤
**状态**: ⏸️ 待开始
**描述**: 验证普通人员数据范围
**测试步骤**:
1. 分配某用户为"普通人员"
2. 以该用户登录
3. 访问任务列表页面
4. 验证只能看到自己作为assignee或creator_id的任务

**SQL验证**:
```sql
-- 假设用户ID为ou_test
SELECT COUNT(*) FROM tasks
WHERE assignee = 'ou_test' OR creator_id = 'ou_test';

-- 应该与前端显示的任务数量一致
```

**验收标准**:
- [ ] 普通人员只看到自己相关任务
- [ ] 数据过滤正确生效
- [ ] SQL过滤条件正确
- [ ] 无法看到其他人的任务

**预估工时**: 30分钟

---

### 任务7.4: 端到端测试和性能检查
**状态**: ⏸️ 待开始
**描述**: 完整流程测试和性能验证
**测试场景**:
1. 创建3个测试用户（系统管理员、管理者、普通人员）
2. 测试所有API端点
3. 测试前端所有功能
4. 检查SQL查询性能
5. 检查日志是否有错误

**性能指标**:
- [ ] 用户列表加载 < 500ms
- [ ] 角色分配保存 < 200ms
- [ ] 任务列表查询（过滤后）< 300ms

**验收标准**:
- [ ] 所有功能正常
- [ ] 性能符合指标
- [ ] 无控制台错误
- [ ] 无后端错误日志

**预估工时**: 40分钟

---

## 📌 依赖关系

```
Phase 1 (数据库迁移)
    ↓
Phase 2 (数据同步改造)
    ↓
Phase 3 (后端角色API) + Phase 4 (数据过滤)
    ↓
Phase 5 (前端用户管理)
    ↓
Phase 6 (路由和权限控制)
    ↓
Phase 7 (测试验证)
```

**关键路径**: Phase 1 → Phase 2 → Phase 3 → Phase 5 → Phase 7

---

## 🎯 里程碑

| 里程碑 | 完成标准 | 预计完成 |
|--------|---------|---------|
| M1: 数据库就绪 | 所有表创建成功，默认角色插入 | Phase 1完成 |
| M2: 数据完整 | 所有任务包含发起人信息 | Phase 2完成 |
| M3: API可用 | 所有角色和用户管理API正常工作 | Phase 3+4完成 |
| M4: UI可用 | 用户管理页面可正常使用 | Phase 5+6完成 |
| M5: 功能验证 | 所有测试通过，权限控制正确 | Phase 7完成 |

---

## ⚠️ 风险和注意事项

### 1. 数据迁移风险
**风险**: 添加字段时可能导致现有代码报错
**应对**: 在开发环境充分测试，生产环境备份数据库

### 2. 权限过滤性能
**风险**: 复杂的SQL过滤可能影响查询性能
**应对**: 为creator_id创建索引，监控查询性能

### 3. 角色分配错误
**风险**: 错误分配角色可能导致权限混乱
**应对**: 实现审计日志，记录所有角色变更操作

### 4. 最后系统管理员保护
**风险**: 删除最后一个系统管理员导致无人可管理
**应对**: 代码中强制检查，禁止删除最后一个系统管理员

---

## 📝 变更记录

| 日期 | 版本 | 变更内容 | 变更人 |
|------|------|---------|--------|
| 2025-11-03 | v1.0 | 初始版本，创建任务清单 | 张健 |

---

**下一步行动**: 开始Phase 1任务1.1 - 添加tasks表creator字段
