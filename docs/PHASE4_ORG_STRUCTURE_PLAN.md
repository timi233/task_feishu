# Phase 4 - 组织架构与权限管理实施计划

**版本**: v1.0
**日期**: 2025-10-31
**方案**: 混合方案C（Identity Hub主数据源 + 派工系统缓存）
**目标**: 实现基于组织架构的统一权限管理

---

## 目录

1. [总体架构](#总体架构)
2. [实施阶段](#实施阶段)
3. [详细设计](#详细设计)
4. [风险控制](#风险控制)
5. [验收标准](#验收标准)

---

## 总体架构

### 数据流向

```
┌─────────────────────────────────────────────────────────────┐
│                   飞书（数据源）                              │
│  • 通讯录API: 用户、部门、上下级关系                          │
│  • 权限: contact:contact:readonly, contact:department:readonly│
└────────────────────┬────────────────────────────────────────┘
                     │ 定时同步（每天凌晨2点）
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              Identity Hub (主数据源)                          │
│  📊 数据库表:                                                 │
│    • departments (部门层级)                                   │
│    • users (用户完整信息)                                     │
│    • user_departments (用户-部门关系)                         │
│    • roles (角色定义)                                         │
│    • permissions (权限定义)                                   │
│    • user_roles (用户-角色关系)                               │
│                                                               │
│  🔌 API端点:                                                  │
│    POST /api/org/sync         → 从飞书同步组织架构            │
│    GET  /api/org/departments  → 获取部门列表/树               │
│    GET  /api/org/users        → 获取用户列表                  │
│    GET  /api/org/users/{id}   → 获取用户详情+部门+权限        │
│    GET  /api/permissions/check → 检查用户权限                 │
└────────────────────┬────────────────────────────────────────┘
                     │ OAuth + REST API
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              派工系统 (业务系统 + 缓存层)                      │
│  📊 数据库表:                                                 │
│    • engineers (缓存工程师基础信息)                           │
│      - user_id (主键，关联Identity Hub)                      │
│      - name, email, mobile (缓存，快速显示)                  │
│      - department_name (冗余，显示用)                         │
│      - sync_at (最后同步时间)                                 │
│    • tasks (派工业务数据)                                     │
│                                                               │
│  🔄 同步策略:                                                 │
│    • 用户登录时: 同步当前用户信息                             │
│    • 每天凌晨3点: 全量同步工程师列表                          │
│    • 权限判断: 实时调用Identity Hub API                       │
│                                                               │
│  🔐 权限检查:                                                 │
│    await check_permission(user_id, "task:edit")               │
│    → 调用Identity Hub API                                     │
│    → 缓存30分钟（Redis/内存）                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 实施阶段

### Phase 4.1: Identity Hub端 - 组织架构数据库设计

**时间**: 第1天（4小时）
**负责**: 后端开发
**输出**: 数据库Schema + 迁移脚本

#### 任务清单

1. **设计数据库表结构**（1小时）
   ```sql
   -- 部门表
   CREATE TABLE departments (
       department_id TEXT PRIMARY KEY,      -- 飞书部门ID
       name TEXT NOT NULL,                  -- 部门名称
       parent_id TEXT,                      -- 上级部门ID
       leader_user_id TEXT,                 -- 部门负责人
       full_path TEXT,                      -- 完整路径（如：/公司/技术部/后端组）
       level INTEGER DEFAULT 0,             -- 层级深度
       status INTEGER DEFAULT 1,            -- 1-启用，0-停用
       order_num INTEGER DEFAULT 0,         -- 排序
       member_count INTEGER DEFAULT 0,      -- 成员数
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (parent_id) REFERENCES departments(department_id)
   );

   -- 扩展users表（在现有users表基础上新增字段）
   ALTER TABLE users ADD COLUMN department_id TEXT;        -- 主部门
   ALTER TABLE users ADD COLUMN employee_no TEXT;          -- 工号
   ALTER TABLE users ADD COLUMN job_title TEXT;            -- 职位
   ALTER TABLE users ADD COLUMN leader_user_id TEXT;       -- 直属上级
   ALTER TABLE users ADD COLUMN join_time INTEGER;         -- 入职时间
   ALTER TABLE users ADD COLUMN avatar_url TEXT;           -- 头像
   ALTER TABLE users ADD COLUMN mobile TEXT;               -- 手机号
   ALTER TABLE users ADD COLUMN work_status INTEGER DEFAULT 1; -- 1-在职，0-离职

   -- 用户-部门关系表（支持多部门）
   CREATE TABLE user_departments (
       user_id TEXT NOT NULL,
       department_id TEXT NOT NULL,
       is_primary BOOLEAN DEFAULT 0,        -- 是否主部门
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY (user_id, department_id),
       FOREIGN KEY (user_id) REFERENCES users(user_id),
       FOREIGN KEY (department_id) REFERENCES departments(department_id)
   );

   -- 角色表
   CREATE TABLE roles (
       role_id TEXT PRIMARY KEY,            -- 角色ID（如：admin, dept_manager）
       role_name TEXT NOT NULL,             -- 角色名称
       description TEXT,                    -- 描述
       is_system BOOLEAN DEFAULT 0,         -- 是否系统角色（不可删除）
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   -- 权限表
   CREATE TABLE permissions (
       permission_id TEXT PRIMARY KEY,      -- 权限ID（如：task:create）
       resource TEXT NOT NULL,              -- 资源（task, approval, user）
       action TEXT NOT NULL,                -- 动作（create, read, update, delete）
       description TEXT,                    -- 描述
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(resource, action)
   );

   -- 角色-权限关系表
   CREATE TABLE role_permissions (
       role_id TEXT NOT NULL,
       permission_id TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY (role_id, permission_id),
       FOREIGN KEY (role_id) REFERENCES roles(role_id),
       FOREIGN KEY (permission_id) REFERENCES permissions(permission_id)
   );

   -- 用户-角色关系表
   CREATE TABLE user_roles (
       user_id TEXT NOT NULL,
       role_id TEXT NOT NULL,
       scope TEXT,                          -- 作用域（如：department:dept001）
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY (user_id, role_id, scope),
       FOREIGN KEY (user_id) REFERENCES users(user_id),
       FOREIGN KEY (role_id) REFERENCES roles(role_id)
   );

   -- 创建索引
   CREATE INDEX idx_departments_parent ON departments(parent_id);
   CREATE INDEX idx_departments_leader ON departments(leader_user_id);
   CREATE INDEX idx_users_department ON users(department_id);
   CREATE INDEX idx_users_leader ON users(leader_user_id);
   CREATE INDEX idx_user_departments_dept ON user_departments(department_id);
   ```

2. **编写数据库迁移脚本**（1小时）
   - 文件: `/identity-hub/backend/migrations/add_org_structure.py`
   - 兼容SQLite和MySQL
   - 包含回滚逻辑

3. **初始化基础权限数据**（1小时）
   ```sql
   -- 插入系统角色
   INSERT INTO roles (role_id, role_name, description, is_system) VALUES
   ('super_admin', '超级管理员', '系统最高权限', 1),
   ('dept_manager', '部门管理员', '管理本部门人员和任务', 1),
   ('engineer', '普通工程师', '查看和处理自己的任务', 1);

   -- 插入基础权限
   INSERT INTO permissions (permission_id, resource, action, description) VALUES
   ('task:create', 'task', 'create', '创建派工'),
   ('task:read', 'task', 'read', '查看派工'),
   ('task:update', 'task', 'update', '修改派工'),
   ('task:delete', 'task', 'delete', '删除派工'),
   ('task:assign', 'task', 'assign', '分配派工'),
   ('user:read', 'user', 'read', '查看用户信息'),
   ('user:manage', 'user', 'manage', '管理用户'),
   ('dept:read', 'department', 'read', '查看部门'),
   ('dept:manage', 'department', 'manage', '管理部门');

   -- 配置角色权限
   -- 超级管理员：所有权限
   INSERT INTO role_permissions (role_id, permission_id)
   SELECT 'super_admin', permission_id FROM permissions;

   -- 部门管理员：部门内的任务和人员管理
   INSERT INTO role_permissions (role_id, permission_id) VALUES
   ('dept_manager', 'task:create'),
   ('dept_manager', 'task:read'),
   ('dept_manager', 'task:update'),
   ('dept_manager', 'task:assign'),
   ('dept_manager', 'user:read'),
   ('dept_manager', 'dept:read');

   -- 普通工程师：只能查看和处理自己的任务
   INSERT INTO role_permissions (role_id, permission_id) VALUES
   ('engineer', 'task:read'),
   ('engineer', 'task:update');
   ```

4. **执行迁移并验证**（1小时）
   ```bash
   cd /home/jian/code/identity-hub/backend
   python migrations/add_org_structure.py
   python -c "from task_db import get_db_connection; \
              with get_db_connection() as c: \
              print('departments:', c.execute('SELECT COUNT(*) FROM departments').fetchone()[0])"
   ```

**验收标准**:
- ✅ 所有表创建成功
- ✅ 索引创建成功
- ✅ 基础数据插入成功（3个角色、9个权限）
- ✅ 外键约束验证通过

---

### Phase 4.2: Identity Hub端 - 飞书组织架构同步

**时间**: 第2天（6小时）
**负责**: 后端开发
**输出**: 组织架构同步模块 + API端点

#### 任务清单

1. **实现飞书组织架构读取器**（3小时）

   文件: `/identity-hub/backend/feishu_org_sync.py`

   ```python
   """飞书组织架构同步模块"""

   import requests
   import logging
   from typing import List, Dict, Any

   logger = logging.getLogger(__name__)


   class FeishuOrgSync:
       """飞书组织架构同步器"""

       def __init__(self, app_id: str, app_secret: str):
           self.app_id = app_id
           self.app_secret = app_secret
           self.access_token = None

       def get_tenant_access_token(self) -> str:
           """获取tenant_access_token"""
           # 实现逻辑（已有代码可复用）
           pass

       def sync_departments(self) -> List[Dict[str, Any]]:
           """
           同步所有部门

           Returns:
               部门列表，包含层级关系
           """
           url = "https://open.feishu.cn/open-apis/contact/v3/departments"
           headers = {"Authorization": f"Bearer {self.access_token}"}

           all_departments = []
           page_token = None

           while True:
               params = {"page_size": 50}
               if page_token:
                   params["page_token"] = page_token

               response = requests.get(url, headers=headers, params=params)
               data = response.json()

               if data.get("code") != 0:
                   raise Exception(f"获取部门失败: {data.get('msg')}")

               departments = data["data"]["items"]
               all_departments.extend(departments)

               page_token = data["data"].get("page_token")
               if not page_token:
                   break

           logger.info(f"从飞书获取了{len(all_departments)}个部门")
           return all_departments

       def sync_users_with_departments(self) -> List[Dict[str, Any]]:
           """
           同步用户及其部门关系

           Returns:
               用户列表，包含部门信息
           """
           url = "https://open.feishu.cn/open-apis/contact/v3/users"
           headers = {"Authorization": f"Bearer {self.access_token}"}

           all_users = []
           page_token = None

           while True:
               params = {
                   "page_size": 50,
                   "user_id_type": "open_id",
                   "department_id_type": "department_id"
               }
               if page_token:
                   params["page_token"] = page_token

               response = requests.get(url, headers=headers, params=params)
               data = response.json()

               if data.get("code") != 0:
                   raise Exception(f"获取用户失败: {data.get('msg')}")

               users = data["data"]["items"]
               all_users.extend(users)

               page_token = data["data"].get("page_token")
               if not page_token:
                   break

           logger.info(f"从飞书获取了{len(all_users)}个用户")
           return all_users

       def build_department_tree(
           self,
           departments: List[Dict[str, Any]]
       ) -> Dict[str, Any]:
           """
           构建部门树

           计算每个部门的：
           - full_path（完整路径）
           - level（层级深度）
           - member_count（成员数量）
           """
           dept_map = {d["department_id"]: d for d in departments}

           for dept in departments:
               # 计算full_path
               path_parts = [dept["name"]]
               parent_id = dept.get("parent_department_id")
               level = 0

               while parent_id and parent_id in dept_map:
                   parent = dept_map[parent_id]
                   path_parts.insert(0, parent["name"])
                   parent_id = parent.get("parent_department_id")
                   level += 1

               dept["full_path"] = "/" + "/".join(path_parts)
               dept["level"] = level

           return dept_map

       def save_to_database(
           self,
           departments: List[Dict[str, Any]],
           users: List[Dict[str, Any]]
       ):
           """保存到数据库"""
           from task_db import get_db_connection

           with get_db_connection() as conn:
               cursor = conn.cursor()

               # 1. 保存部门
               for dept in departments:
                   cursor.execute("""
                       INSERT OR REPLACE INTO departments
                       (department_id, name, parent_id, leader_user_id,
                        full_path, level, status, order_num, member_count, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   """, (
                       dept["department_id"],
                       dept["name"],
                       dept.get("parent_department_id"),
                       dept.get("leader_user_id"),
                       dept["full_path"],
                       dept["level"],
                       1 if dept.get("status", {}).get("is_deleted") == False else 0,
                       dept.get("order", 0),
                       dept.get("member_count", 0)
                   ))

               # 2. 更新用户表
               for user in users:
                   # 获取主部门（第一个部门）
                   primary_dept = user.get("department_ids", [None])[0]

                   cursor.execute("""
                       UPDATE users SET
                           department_id = ?,
                           employee_no = ?,
                           job_title = ?,
                           leader_user_id = ?,
                           join_time = ?,
                           avatar_url = ?,
                           mobile = ?,
                           work_status = ?,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE user_id = ?
                   """, (
                       primary_dept,
                       user.get("employee_no"),
                       user.get("job_title"),
                       user.get("leader_user_id"),
                       user.get("join_time"),
                       user.get("avatar", {}).get("avatar_240"),
                       user.get("mobile"),
                       1 if user.get("status", {}).get("is_activated") else 0,
                       user["open_id"]
                   ))

               # 3. 保存用户-部门关系
               cursor.execute("DELETE FROM user_departments")  # 清空旧数据

               for user in users:
                   dept_ids = user.get("department_ids", [])
                   for idx, dept_id in enumerate(dept_ids):
                       cursor.execute("""
                           INSERT INTO user_departments
                           (user_id, department_id, is_primary)
                           VALUES (?, ?, ?)
                       """, (
                           user["open_id"],
                           dept_id,
                           1 if idx == 0 else 0  # 第一个为主部门
                       ))

               conn.commit()

               logger.info(f"保存{len(departments)}个部门，{len(users)}个用户到数据库")
   ```

2. **创建同步API端点**（2小时）

   文件: `/identity-hub/backend/routers/org.py`

   ```python
   """组织架构路由"""

   from fastapi import APIRouter, HTTPException
   import logging
   from datetime import datetime

   from feishu_org_sync import FeishuOrgSync
   from config import settings

   logger = logging.getLogger(__name__)

   router = APIRouter(prefix="/api/org", tags=["organization"])


   @router.post("/sync")
   async def sync_org_structure():
       """
       从飞书同步组织架构

       同步内容：
       - 部门层级结构
       - 用户完整信息
       - 用户-部门关系

       Returns:
           {
               "success": true,
               "departments_synced": 10,
               "users_synced": 50,
               "timestamp": "2025-10-31T12:00:00"
           }
       """
       logger.info("开始同步组织架构...")

       try:
           syncer = FeishuOrgSync(
               settings.feishu.app_id,
               settings.feishu.app_secret
           )

           # 1. 获取token
           syncer.access_token = syncer.get_tenant_access_token()

           # 2. 同步部门
           departments = syncer.sync_departments()
           dept_tree = syncer.build_department_tree(departments)

           # 3. 同步用户
           users = syncer.sync_users_with_departments()

           # 4. 保存到数据库
           syncer.save_to_database(list(dept_tree.values()), users)

           return {
               "success": True,
               "departments_synced": len(departments),
               "users_synced": len(users),
               "timestamp": datetime.now().isoformat()
           }

       except Exception as e:
           logger.exception("组织架构同步失败")
           raise HTTPException(
               status_code=500,
               detail=f"同步失败: {str(e)}"
           )
   ```

3. **实现定时同步任务**（1小时）

   文件: `/identity-hub/backend/scheduler.py`

   ```python
   """定时任务调度器"""

   import schedule
   import time
   import logging
   from feishu_org_sync import FeishuOrgSync
   from config import settings

   logger = logging.getLogger(__name__)


   def sync_org_job():
       """组织架构同步任务"""
       logger.info("定时任务: 开始同步组织架构")

       try:
           syncer = FeishuOrgSync(
               settings.feishu.app_id,
               settings.feishu.app_secret
           )
           syncer.access_token = syncer.get_tenant_access_token()

           departments = syncer.sync_departments()
           dept_tree = syncer.build_department_tree(departments)
           users = syncer.sync_users_with_departments()
           syncer.save_to_database(list(dept_tree.values()), users)

           logger.info("定时任务: 组织架构同步完成")
       except Exception as e:
           logger.exception("定时任务: 组织架构同步失败")


   # 每天凌晨2点执行
   schedule.every().day.at("02:00").do(sync_org_job)


   def run_scheduler():
       """运行调度器"""
       logger.info("启动定时任务调度器")

       while True:
           schedule.run_pending()
           time.sleep(60)  # 每分钟检查一次
   ```

**验收标准**:
- ✅ 能成功从飞书获取部门和用户数据
- ✅ 部门树构建正确（full_path, level）
- ✅ 数据保存到数据库无错误
- ✅ API端点返回正确的同步结果

---

### Phase 4.3: Identity Hub端 - 组织架构查询API

**时间**: 第3天（4小时）
**负责**: 后端开发
**输出**: 6个查询API端点

#### API端点列表

```python
# 文件: /identity-hub/backend/routers/org.py (扩展)

@router.get("/departments")
async def get_departments(
    parent_id: Optional[str] = None,
    include_children: bool = False
):
    """
    获取部门列表

    Args:
        parent_id: 父部门ID（不提供则返回顶级部门）
        include_children: 是否包含子部门

    Returns:
        [
            {
                "department_id": "dept001",
                "name": "技术部",
                "parent_id": null,
                "full_path": "/公司/技术部",
                "level": 1,
                "member_count": 20,
                "leader": {
                    "user_id": "user001",
                    "name": "张三"
                }
            }
        ]
    """
    pass


@router.get("/departments/tree")
async def get_department_tree():
    """
    获取完整部门树

    Returns:
        {
            "department_id": "root",
            "name": "公司",
            "children": [
                {
                    "department_id": "dept001",
                    "name": "技术部",
                    "children": [...]
                }
            ]
        }
    """
    pass


@router.get("/users")
async def get_users(
    department_id: Optional[str] = None,
    work_status: int = 1,
    page: int = 1,
    page_size: int = 50
):
    """
    获取用户列表

    Args:
        department_id: 部门ID（不提供则返回所有）
        work_status: 工作状态（1-在职，0-离职）
        page: 页码
        page_size: 每页数量

    Returns:
        {
            "total": 100,
            "page": 1,
            "page_size": 50,
            "items": [
                {
                    "user_id": "user001",
                    "name": "张三",
                    "email": "zhangsan@example.com",
                    "mobile": "13800138000",
                    "department": {
                        "department_id": "dept001",
                        "name": "技术部"
                    },
                    "job_title": "高级工程师",
                    "leader": {
                        "user_id": "user002",
                        "name": "李四"
                    }
                }
            ]
        }
    """
    pass


@router.get("/users/{user_id}")
async def get_user_detail(user_id: str):
    """
    获取用户详细信息

    Returns:
        {
            "user_id": "user001",
            "name": "张三",
            "email": "zhangsan@example.com",
            "departments": [
                {
                    "department_id": "dept001",
                    "name": "技术部",
                    "is_primary": true
                }
            ],
            "roles": [
                {
                    "role_id": "engineer",
                    "role_name": "普通工程师"
                }
            ],
            "permissions": [
                "task:read",
                "task:update"
            ]
        }
    """
    pass


@router.get("/permissions/check")
async def check_permission(
    user_id: str,
    permission: str,
    resource_id: Optional[str] = None
):
    """
    检查用户权限

    Args:
        user_id: 用户ID
        permission: 权限（如：task:create）
        resource_id: 资源ID（可选，用于数据权限）

    Returns:
        {
            "allowed": true,
            "reason": "用户拥有task:create权限"
        }
    """
    pass
```

**验收标准**:
- ✅ 所有6个端点实现完成
- ✅ 返回数据格式正确
- ✅ 分页逻辑正确
- ✅ 权限检查逻辑正确

---

### Phase 4.4: 派工系统端 - 缓存层改造

**时间**: 第4天（5小时）
**负责**: 后端开发
**输出**: 派工系统同步逻辑 + 缓存更新机制

#### 任务清单

1. **扩展engineers表**（1小时）

   文件: `/Task_feishu/backend/migrations/extend_engineers_table.py`

   ```sql
   ALTER TABLE engineers ADD COLUMN department_name TEXT;  -- 部门名称（冗余）
   ALTER TABLE engineers ADD COLUMN sync_at TIMESTAMP;     -- 最后同步时间
   ```

2. **实现同步逻辑**（2小时）

   文件: `/Task_feishu/backend/identity_hub_client.py` (扩展)

   ```python
   class IdentityHubClient:
       """Identity Hub客户端（扩展）"""

       def get_users(self, department_id: Optional[str] = None):
           """从Identity Hub获取用户列表"""
           url = f"{self.hub_url}/api/org/users"
           params = {"work_status": 1}
           if department_id:
               params["department_id"] = department_id

           response = requests.get(url, params=params)
           return response.json()

       def get_user_detail(self, user_id: str):
           """获取用户详细信息"""
           url = f"{self.hub_url}/api/org/users/{user_id}"
           response = requests.get(url)
           return response.json()

       def check_permission(self, user_id: str, permission: str):
           """检查用户权限"""
           url = f"{self.hub_url}/api/permissions/check"
           params = {"user_id": user_id, "permission": permission}
           response = requests.get(url, params=params)
           return response.json()["allowed"]
   ```

   文件: `/Task_feishu/backend/sync_engineers_from_hub.py`

   ```python
   """从Identity Hub同步工程师数据"""

   from identity_hub_client import IdentityHubClient
   from task_db import get_db_connection
   import logging

   logger = logging.getLogger(__name__)


   def sync_engineers_from_identity_hub():
       """从Identity Hub同步工程师列表"""
       client = IdentityHubClient()

       # 获取所有在职用户
       response = client.get_users()
       users = response["items"]

       with get_db_connection() as conn:
           cursor = conn.cursor()

           for user in users:
               dept = user.get("department", {})

               cursor.execute("""
                   INSERT OR REPLACE INTO engineers
                   (user_id, name, email, mobile, department_name,
                    status, sync_at)
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               """, (
                   user["user_id"],
                   user["name"],
                   user.get("email"),
                   user.get("mobile"),
                   dept.get("name"),
                   1  # 在职
               ))

           conn.commit()
           logger.info(f"同步了{len(users)}个工程师")
   ```

3. **创建同步API端点**（1小时）

   文件: `/Task_feishu/backend/routers/org.py` (新建)

   ```python
   @router.post("/api/org/sync-from-hub")
   async def sync_from_identity_hub():
       """从Identity Hub同步工程师数据"""
       from sync_engineers_from_hub import sync_engineers_from_identity_hub

       try:
           sync_engineers_from_identity_hub()
           return {"success": True}
       except Exception as e:
           raise HTTPException(500, str(e))
   ```

4. **实现用户登录时同步**（1小时）

   修改: `/Task_feishu/backend/auth_routes.py`

   ```python
   @router.get("/callback")
   async def callback(code: str, state: str, request: Request):
       """OAuth回调（扩展）"""

       # ... 原有逻辑 ...

       # 新增：同步当前用户信息
       user_id = user_info["sub"]
       client = IdentityHubClient()
       user_detail = client.get_user_detail(user_id)

       # 更新本地缓存
       with get_db_connection() as conn:
           cursor = conn.cursor()
           cursor.execute("""
               INSERT OR REPLACE INTO engineers
               (user_id, name, email, mobile, department_name, sync_at)
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
           """, (
               user_id,
               user_detail["name"],
               user_detail["email"],
               user_detail.get("mobile"),
               user_detail["departments"][0]["name"]
           ))
           conn.commit()
   ```

**验收标准**:
- ✅ 能从Identity Hub获取用户列表
- ✅ 数据正确保存到本地engineers表
- ✅ 用户登录时自动同步个人信息
- ✅ 定时任务每天凌晨3点执行

---

### Phase 4.5: 权限体系集成

**时间**: 第5天（6小时）
**负责**: 后端开发 + 前端开发
**输出**: 权限装饰器 + 前端权限控制

#### 后端权限装饰器（3小时）

文件: `/Task_feishu/backend/auth_permission.py`

```python
"""权限验证装饰器"""

from functools import wraps
from fastapi import HTTPException, Request
from identity_hub_client import IdentityHubClient

# 权限缓存（内存缓存30分钟）
_permission_cache = {}


def require_permission(permission: str):
    """
    权限验证装饰器

    使用:
        @router.post("/api/approvals")
        @require_permission("task:create")
        async def create_approval(...):
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request, **kwargs):
            # 从session获取user_id
            session_id = request.cookies.get("session_id")
            if not session_id:
                raise HTTPException(401, "未登录")

            user_id = get_user_from_session(session_id)

            # 检查缓存
            cache_key = f"{user_id}:{permission}"
            if cache_key in _permission_cache:
                if _permission_cache[cache_key]["expires_at"] > time.time():
                    if not _permission_cache[cache_key]["allowed"]:
                        raise HTTPException(403, "权限不足")
                    return await func(*args, request=request, **kwargs)

            # 调用Identity Hub检查权限
            client = IdentityHubClient()
            allowed = client.check_permission(user_id, permission)

            # 缓存结果（30分钟）
            _permission_cache[cache_key] = {
                "allowed": allowed,
                "expires_at": time.time() + 1800
            }

            if not allowed:
                raise HTTPException(403, "权限不足")

            return await func(*args, request=request, **kwargs)

        return wrapper
    return decorator
```

应用到端点:

```python
# 文件: /Task_feishu/backend/routers/approvals.py

from auth_permission import require_permission

@router.post("")
@require_permission("task:create")
async def create_approval(...):
    """创建派工（需要task:create权限）"""
    pass

@router.put("/{instance_code}")
@require_permission("task:update")
async def update_approval(...):
    """修改派工（需要task:update权限）"""
    pass

@router.delete("/{instance_code}")
@require_permission("task:delete")
async def delete_approval(...):
    """删除派工（需要task:delete权限）"""
    pass
```

#### 前端权限控制（3小时）

文件: `/Task_feishu/frontend/src/utils/permission.js`

```javascript
/**
 * 权限工具函数
 */

// 从localStorage获取用户权限列表
export function getUserPermissions() {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
  return userInfo.permissions || [];
}

// 检查是否有指定权限
export function hasPermission(permission) {
  const permissions = getUserPermissions();
  return permissions.includes(permission);
}

// 检查是否有任一权限
export function hasAnyPermission(permissionList) {
  const permissions = getUserPermissions();
  return permissionList.some(p => permissions.includes(p));
}

// 权限控制高阶组件
export function withPermission(Component, requiredPermission) {
  return function PermissionWrappedComponent(props) {
    if (!hasPermission(requiredPermission)) {
      return <div>权限不足</div>;
    }
    return <Component {...props} />;
  };
}
```

使用示例:

```jsx
// 条件渲染按钮
import { hasPermission } from './utils/permission';

function DispatchPanel() {
  return (
    <div>
      {hasPermission('task:create') && (
        <button onClick={handleCreate}>新建派工</button>
      )}

      {hasPermission('task:delete') && (
        <button onClick={handleDelete}>删除派工</button>
      )}
    </div>
  );
}
```

**验收标准**:
- ✅ 后端权限装饰器工作正常
- ✅ 无权限时返回403错误
- ✅ 前端根据权限显示/隐藏按钮
- ✅ 权限缓存正常工作

---

### Phase 4.6: 集成测试与文档

**时间**: 第6天（4小时）
**负责**: QA + 开发
**输出**: 测试报告 + 使用文档

#### 测试用例

1. **组织架构同步测试**
   - 从飞书同步部门和用户
   - 验证数据完整性
   - 验证部门树结构

2. **权限检查测试**
   - 超级管理员拥有所有权限
   - 部门管理员拥有部门权限
   - 普通工程师仅有基础权限

3. **缓存测试**
   - 派工系统本地缓存正确
   - 用户登录时同步个人信息
   - 定时任务正常执行

4. **API测试**
   - Identity Hub所有端点正常
   - 派工系统权限装饰器正常
   - 前端权限控制正常

---

## 风险控制

### 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| Identity Hub不可用 | 派工系统无法验证权限 | 1. 本地缓存权限信息<br>2. 降级策略：允许基础操作 |
| 飞书API限流 | 同步失败 | 1. 分批同步<br>2. 重试机制 |
| 数据不一致 | 权限判断错误 | 1. 定时对账<br>2. 手动同步接口 |

### 业务风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 权限配置错误 | 用户无法操作 | 1. 超级管理员绕过权限<br>2. 审计日志追踪 |
| 大量用户同时登录 | 同步压力大 | 1. 异步队列<br>2. 限流 |

---

## 验收标准

### 功能验收

- ✅ Identity Hub能同步飞书组织架构
- ✅ 派工系统能缓存工程师信息
- ✅ 权限检查正确工作
- ✅ 前端根据权限显示功能

### 性能验收

- ✅ 权限检查响应时间 < 100ms（有缓存）
- ✅ 组织架构同步时间 < 5分钟（100个部门、500个用户）
- ✅ 用户登录同步时间 < 500ms

### 文档验收

- ✅ Identity Hub API文档完整
- ✅ 权限配置文档完整
- ✅ 部署文档完整

---

## 下一步计划

完成Phase 4后，可以继续：

1. **Phase 5**: 细粒度权限（数据权限、字段权限）
2. **Phase 6**: 审批流引擎（基于组织架构的多级审批）
3. **Phase 7**: 统一管理后台（用户管理、角色管理、权限管理）

---

**文档版本**: v1.0
**最后更新**: 2025-10-31
**状态**: 待执行
