# 工单系统 + 身份认证 - 完整数据库结构文档

**生成时间**: 2025-11-09
**数据库类型**: SQLite
**数据库文件**: `./data/db/tasks.db`

---

## 一、核心表结构总览

系统包含以下6个核心表：

1. **tasks** - 工单任务主表
2. **engineers** - 工程师信息表
3. **roles** - 角色定义表
4. **user_roles** - 用户角色关联表

---

## 二、详细表结构

### 1. tasks 表（工单任务）

**用途**: 存储所有派工任务数据，包括飞书同步的工单和本地创建的任务

```sql
CREATE TABLE tasks (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 基础信息
    record_id TEXT NOT NULL,              -- 飞书记录ID
    task_name TEXT NOT NULL,              -- 任务名称
    assignee TEXT NOT NULL,               -- 指派人（工程师姓名）

    -- 状态和优先级
    status TEXT NOT NULL,                 -- 展示状态（进行中/已结束/优先级）
    priority TEXT NOT NULL,               -- 原始优先级
    application_status TEXT,              -- 申请状态

    -- 日期字段（支持跨天任务）
    date TEXT NOT NULL,                   -- 任务在这一天展示 (YYYY-MM-DD)
    start_date TEXT,                      -- 任务实际开始日期 (YYYY-MM-DD)
    end_date TEXT,                        -- 任务实际结束日期 (YYYY-MM-DD)
    weekday TEXT NOT NULL,                -- monday, tuesday, weekend, unknown_date

    -- 发起人信息（Phase 4.6新增）
    creator_id TEXT,                      -- 任务发起人user_id
    creator_name TEXT,                    -- 任务发起人姓名

    -- 审批相关字段
    approval_instance_code TEXT,          -- 审批实例ID
    approval_status TEXT,                 -- 审批状态

    -- 元数据
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    UNIQUE(record_id, date)               -- 防止重复插入同一天的同一条记录
);

-- 索引
CREATE INDEX idx_tasks_weekday ON tasks (weekday);
CREATE INDEX idx_tasks_date ON tasks (date);
CREATE INDEX idx_tasks_creator ON tasks (creator_id);
CREATE INDEX idx_tasks_approval_instance ON tasks (approval_instance_code);
CREATE INDEX idx_tasks_assignee_approval_status ON tasks (assignee, approval_status);
```

**字段说明**:
- `record_id + date` 组合唯一：一个飞书记录在每一天只有一条任务记录
- `weekday` 可能值: monday, tuesday, wednesday, thursday, friday, weekend, unknown_date
- `status` 可能值: 进行中, 已结束, P0, P1, P2, P3
- 跨天任务会在每一天都创建一条记录，共享同一个`record_id`

---

### 2. engineers 表（工程师信息）

**用途**: 存储从飞书通讯录同步的工程师人员信息

```sql
CREATE TABLE engineers (
    -- 主键
    user_id TEXT PRIMARY KEY,             -- 飞书user_id

    -- 基础信息
    name TEXT NOT NULL,                   -- 工程师姓名
    department_ids TEXT,                  -- 部门ID列表(JSON数组字符串)
    department_name TEXT,                 -- 部门名称
    mobile TEXT,                          -- 手机号
    email TEXT,                           -- 邮箱

    -- 状态
    status INTEGER DEFAULT 1,             -- 状态: 1=在职, 0=离职

    -- 同步时间
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    UNIQUE(user_id)
);

-- 索引
CREATE INDEX idx_engineers_name ON engineers (name);
CREATE INDEX idx_engineers_status ON engineers (status);
```

**字段说明**:
- `user_id` 来自飞书用户唯一标识
- `department_ids` 存储JSON数组，如: `["od-123", "od-456"]`
- `status=1` 表示在职，`status=0` 表示离职

---

### 3. roles 表（角色定义）

**用途**: 定义系统中的用户角色和权限配置（Phase 4.6权限管理）

```sql
CREATE TABLE roles (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 角色标识
    role_key TEXT UNIQUE NOT NULL,        -- 角色标识: 'system_admin', 'manager', 'regular_user'
    role_name TEXT NOT NULL,              -- 角色名称: '系统管理员', '管理者', '普通人员'
    description TEXT,                     -- 角色描述

    -- 权限配置
    permissions TEXT,                     -- JSON数组: ["task:create", "task:read", ...]
    data_scope TEXT DEFAULT 'all',        -- 数据范围: 'all'(全部), 'self'(仅自己相关)

    -- 系统标识
    is_system BOOLEAN DEFAULT 0,          -- 是否系统内置角色（不可删除）

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_roles_key ON roles(role_key);
```

**默认角色**（系统内置，is_system=1）:

| role_key | role_name | data_scope | 权限说明 |
|----------|-----------|------------|---------|
| system_admin | 系统管理员 | all | 可管理用户权限、查看和操作所有数据 |
| manager | 管理者 | all | 可查看和操作所有派工数据，但不能管理用户权限 |
| regular_user | 普通人员 | self | 只能查看和操作与自己相关的派工数据 |

**permissions 字段可能值**:
- `user:read`, `user:write`, `user:delete` - 用户管理权限
- `role:assign`, `role:revoke` - 角色分配权限
- `task:read`, `task:create`, `task:update`, `task:delete` - 任务管理权限
- `approval:read`, `approval:create`, `approval:update`, `approval:delete` - 审批管理权限

---

### 4. user_roles 表（用户角色关联）

**用途**: 关联用户和角色，一个用户可以有多个角色

```sql
CREATE TABLE user_roles (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 关联信息
    user_id TEXT NOT NULL,                -- 飞书user_id
    role_id INTEGER NOT NULL,             -- 角色ID

    -- 分配信息
    assigned_by TEXT,                     -- 分配人user_id
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,

    -- 唯一约束
    UNIQUE(user_id, role_id)              -- 一个用户一个角色类型只能分配一次
);

-- 索引
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
```

**字段说明**:
- `user_id` 关联 engineers 表或飞书用户
- `role_id` 关联 roles 表
- `UNIQUE(user_id, role_id)` 确保同一用户不会重复分配同一角色

---

## 三、数据库迁移历史

### 迁移脚本执行顺序

执行所有迁移脚本需要按照以下顺序：

```bash
# 1. 初始化基础表（tasks, engineers）
# 由 task_db.init_db() 自动执行

# 2. 添加审批字段
python backend/migrations/add_approval_fields.py

# 3. 添加工程师部门名称字段
python backend/migrations/add_department_name_to_engineers.py

# 4. 添加任务发起人字段
python backend/migrations/add_creator_fields_to_tasks.py

# 5. 创建角色管理表
python backend/migrations/create_role_tables.py

# 6. 插入默认角色数据
python backend/migrations/insert_default_roles.py

# 7. 验证权限schema
python backend/migrations/verify_permission_schema.py
```

### 迁移脚本清单

| 脚本 | 功能 | 阶段 | 日期 |
|------|------|------|------|
| `add_approval_fields.py` | 添加approval_instance_code, approval_status字段到tasks表 | Phase 4.2 | 2025-10-17 |
| `add_approval_type_field.py` | 添加审批类型字段 | Phase 4.2 | 2025-10-17 |
| `add_engineers_table.py` | 创建engineers表（已废弃，由init_db创建） | Phase 4.4 | 2025-10-31 |
| `add_department_name_to_engineers.py` | 添加department_name字段到engineers表 | Phase 4.4 | 2025-10-31 |
| `add_creator_fields_to_tasks.py` | 添加creator_id, creator_name字段到tasks表 | Phase 4.6 | 2025-11-03 |
| `create_role_tables.py` | 创建roles, user_roles表 | Phase 4.6 | 2025-11-03 |
| `insert_default_roles.py` | 插入默认角色数据 | Phase 4.6 | 2025-11-03 |
| `verify_permission_schema.py` | 验证权限schema完整性 | Phase 4.6 | 2025-11-03 |

---

## 四、数据库配置

### 环境变量配置

```bash
# 数据库类型
DB_TYPE=sqlite                    # sqlite 或 mysql

# SQLite配置
DB_FILE=./data/db/tasks.db        # 数据库文件路径

# MySQL配置（可选）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=feishu_tasks
```

### Docker挂载配置

在 `docker-compose.yml` 中的数据库挂载：

```yaml
volumes:
  - ../data/db:/app/db            # 挂载数据库目录
```

**重要**:
- 容器内数据库路径: `/app/db/tasks.db`
- 宿主机数据库路径: `./data/db/tasks.db`
- 需要确保挂载目录的权限正确（读写权限）

---

## 五、常见数据库操作

### 1. 初始化数据库

```python
from task_db import init_db
init_db()
```

### 2. 查看表结构

```bash
# 查看所有表
sqlite3 data/db/tasks.db ".tables"

# 查看表结构
sqlite3 data/db/tasks.db ".schema tasks"
sqlite3 data/db/tasks.db ".schema roles"
```

### 3. 数据统计

```sql
-- 任务总数
SELECT COUNT(*) FROM tasks;

-- 在职工程师数量
SELECT COUNT(*) FROM engineers WHERE status = 1;

-- 角色分配统计
SELECT r.role_name, COUNT(ur.user_id) as user_count
FROM roles r
LEFT JOIN user_roles ur ON r.id = ur.role_id
GROUP BY r.id;

-- 每个人的任务数量
SELECT assignee, COUNT(*) as task_count
FROM tasks
WHERE date >= date('now', 'start of month')
GROUP BY assignee
ORDER BY task_count DESC;
```

### 4. 备份和恢复

```bash
# 备份数据库
cp data/db/tasks.db data/db/tasks.db.backup.$(date +%Y%m%d_%H%M%S)

# 使用sqlite3导出SQL
sqlite3 data/db/tasks.db .dump > backup.sql

# 从SQL恢复
sqlite3 new_tasks.db < backup.sql
```

---

## 六、数据迁移检查清单

### 迁移前检查

- [ ] 确认源数据库文件存在且可访问
- [ ] 检查源数据库表结构是否完整
- [ ] 确认所有迁移脚本已执行
- [ ] 备份当前数据库

### 迁移执行

- [ ] 复制数据库文件到新服务器
- [ ] 检查文件权限（chmod 644 tasks.db）
- [ ] 检查目录权限（chmod 755 data/db）
- [ ] 确认环境变量配置正确

### 迁移后验证

- [ ] 验证表结构：所有表都存在
- [ ] 验证数据完整性：记录数量一致
- [ ] 验证索引：所有索引都已创建
- [ ] 验证外键约束：外键关系正确
- [ ] 运行应用测试：API正常工作

---

## 七、问题排查

### 常见问题

1. **数据库文件只读错误**
   ```
   sqlite3.OperationalError: attempt to write a readonly database
   ```
   **解决**:
   ```bash
   chmod 644 data/db/tasks.db
   chmod 755 data/db
   ```

2. **表不存在错误**
   ```
   sqlite3.OperationalError: no such table: roles
   ```
   **解决**: 运行缺失的迁移脚本
   ```bash
   python backend/migrations/create_role_tables.py
   ```

3. **字段不存在错误**
   ```
   sqlite3.OperationalError: no such column: creator_id
   ```
   **解决**: 运行字段添加迁移
   ```bash
   python backend/migrations/add_creator_fields_to_tasks.py
   ```

4. **数据库锁定错误**
   ```
   sqlite3.OperationalError: database is locked
   ```
   **解决**:
   - 关闭所有数据库连接
   - 删除WAL文件: `rm data/db/tasks.db-wal`

---

## 八、数据库性能优化

### 索引策略

当前已创建的索引：

```sql
-- tasks表索引
idx_tasks_weekday                    -- 按星期查询
idx_tasks_date                       -- 按日期查询
idx_tasks_creator                    -- 按发起人查询
idx_tasks_approval_instance          -- 按审批实例查询
idx_tasks_assignee_approval_status   -- 复合索引：按指派人和审批状态查询

-- engineers表索引
idx_engineers_name                   -- 按姓名查询
idx_engineers_status                 -- 按状态查询

-- roles表索引
idx_roles_key                        -- 按角色标识查询

-- user_roles表索引
idx_user_roles_user                  -- 按用户查询
idx_user_roles_role                  -- 按角色查询
```

### 查询优化建议

1. **使用日期范围查询**而不是全表扫描
   ```python
   # 好
   get_tasks_from_db(start_date='2025-11-01', end_date='2025-11-30')

   # 不好
   get_tasks_from_db()  # 返回所有数据
   ```

2. **使用UPSERT**避免DELETE+INSERT
   ```python
   # 已实现: save_processed_tasks_to_db() 使用 INSERT OR REPLACE
   ```

3. **启用WAL模式**提高并发性能
   ```python
   # 已启用: get_db_connection() 自动执行 PRAGMA journal_mode=WAL
   ```

---

## 九、安全注意事项

1. **文件权限**
   - 数据库文件: `chmod 644 tasks.db`
   - 数据库目录: `chmod 755 db/`
   - 所有者应为运行应用的用户

2. **备份策略**
   - 每日自动备份
   - 保留最近7天的备份
   - 迁移前必须手动备份

3. **敏感数据**
   - 不要在日志中输出完整SQL查询（可能包含敏感数据）
   - 数据库文件不要提交到git仓库
   - 生产环境考虑加密数据库文件

---

## 十、相关代码文件

- `backend/task_db.py` - 数据库操作核心模块
- `backend/config.py` - 数据库配置
- `backend/migrations/*.py` - 数据库迁移脚本
- `docker-compose.yml` - Docker数据库挂载配置

---

**文档维护**: 当数据库结构变更时，请更新此文档
