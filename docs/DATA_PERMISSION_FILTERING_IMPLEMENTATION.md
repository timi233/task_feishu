# 数据权限过滤实现报告

**日期**: 2025-11-03
**阶段**: Phase 4.6 - 数据权限过滤

## 实现概述

实现了基于用户角色的数据权限过滤功能，确保用户只能查看与自己相关的任务数据。

## 核心需求

1. **未登录用户**: 页面不显示任何任务数据
2. **普通用户**: 只能看到自己作为发起人或指派工程师的任务
3. **管理者/系统管理员**: 可以查看所有任务

## 实现细节

### 1. 后端API修改

#### 文件: `backend/routers/tasks.py`

**修改内容**:

1. **添加用户认证检查**:
   - 导入 `get_current_user_optional` 和 `get_user_data_scope`
   - 在 `get_tasks` 端点添加 `Request` 参数
   - 使用 `get_current_user_optional` 获取当前登录用户

2. **未登录处理**:
   ```python
   # 如果未登录，返回空任务组
   if not current_user:
       logger.info("未登录用户访问任务列表，返回空数据")
       return TaskGroup(
           monday=[], tuesday=[], wednesday=[], thursday=[],
           friday=[], weekend=[], unknown_date=[]
       )
   ```

3. **数据权限过滤**:
   ```python
   # 获取用户的数据范围
   data_scope = get_user_data_scope(user_id)

   if data_scope == "self":
       # 普通用户：只能看到自己作为发起人或指派工程师的任务
       permission_filtered_tasks = []
       for task in filtered_tasks:
           creator_id = task.get("creator_id")
           assignee = task.get("assignee")

           # 检查是否为发起人
           is_creator = (creator_id == user_id)
           if not is_creator and creator_id:
               # 通过姓名匹配（处理ID格式不一致的情况）
               with get_db_connection() as conn:
                   cursor = conn.cursor()
                   cursor.execute("SELECT name FROM engineers WHERE user_id = ?", (creator_id,))
                   creator_row = cursor.fetchone()
                   if creator_row and creator_row["name"] == user_name:
                       is_creator = True

           # 检查是否为指派工程师
           is_assignee = (assignee == user_name)

           if is_creator or is_assignee:
               permission_filtered_tasks.append(task)

       filtered_tasks = permission_filtered_tasks
   else:
       # 管理者/系统管理员：可以看到所有任务
       logger.info(f"管理者/系统管理员 {user_name} 可以查看所有任务")
   ```

### 2. 权限范围判断

#### 文件: `backend/auth_permission.py`

**新增函数**: `get_user_data_scope(user_id: str) -> str`

功能:
- 查询用户的所有角色
- 返回最高权限的数据范围（all > department > self）
- 如果用户没有角色，默认返回 "self"

优先级:
1. `all` - 系统管理员、管理者
2. `department` - 部门管理者（预留）
3. `self` - 普通用户

## 测试场景

### 场景1: 未登录用户访问

**预期行为**:
- 页面不显示任何任务数据
- API返回空的任务组

**测试方法**:
1. 清除浏览器Cookie
2. 访问 `http://10.242.94.9:3000`
3. 验证页面显示为空

### 场景2: 系统管理员访问

**测试用户**: 张健（系统管理员）

**预期行为**:
- 可以看到所有任务数据
- 不受发起人和指派工程师限制

**测试方法**:
1. 使用张健账号登录
2. 查看任务列表
3. 验证显示所有任务

**日志输出**:
```
2025-11-03 16:36:25 - auth_permission - INFO - 用户 张健(ou_ad883f9af7460763443f4b8b234e25b2) 访问任务列表
2025-11-03 16:36:25 - auth_permission - INFO - 用户 张健 的数据范围: all
2025-11-03 16:36:25 - auth_permission - INFO - 管理者/系统管理员 张健 可以查看所有任务
```

### 场景3: 普通用户访问

**测试用户**: 任意普通用户（非管理员）

**预期行为**:
- 只能看到自己作为发起人的任务
- 只能看到自己作为指派工程师的任务
- 其他任务不显示

**测试方法**:
1. 创建一个普通用户（不分配管理员角色）
2. 使用该用户登录
3. 查看任务列表
4. 验证只显示相关任务

**示例**:
如果普通用户"纪壮"登录，只能看到：
- 发起人为"纪壮"的任务
- 售后工程师为"纪壮"的任务

## 数据流程

```
用户请求 /api/tasks
    ↓
检查登录状态（get_current_user_optional）
    ↓
未登录 → 返回空数据
    ↓
已登录 → 获取用户数据范围（get_user_data_scope）
    ↓
data_scope = "all" → 返回所有任务
    ↓
data_scope = "self" → 过滤任务
    ↓
    - 检查 creator_id == user_id
    - 检查 assignee == user_name
    ↓
返回过滤后的任务
```

## 关键技术点

### 1. Cookie-based认证
- 使用 `task_session_id` Cookie
- 通过 `session_manager` 管理会话
- 支持可选认证（`get_current_user_optional`）

### 2. 角色与数据范围映射

| 角色 | role_key | data_scope | 权限描述 |
|------|----------|------------|----------|
| 系统管理员 | system_admin | all | 查看所有数据 |
| 管理者 | manager | all | 查看所有数据 |
| 普通用户 | regular | self | 仅查看相关数据 |

### 3. 创建人匹配策略

由于用户ID可能存在多种格式（飞书ID、Identity Hub ID等），采用双重匹配策略：
1. 直接匹配 `creator_id == user_id`
2. 通过 `engineers` 表查找姓名匹配

## 性能考虑

### 潜在性能问题
- 普通用户每个任务都需要查询 `engineers` 表
- 在大数据量时可能影响性能

### 优化建议
1. **在内存中缓存用户ID到姓名的映射**:
   ```python
   # 预先加载用户映射
   with get_db_connection() as conn:
       cursor = conn.cursor()
       cursor.execute("SELECT user_id, name FROM engineers")
       user_name_map = {row['user_id']: row['name'] for row in cursor.fetchall()}
   ```

2. **在数据库层面过滤**:
   - 将权限过滤逻辑移到SQL查询中
   - 使用 `WHERE (creator_id = ? OR assignee = ?)` 条件

3. **添加索引**:
   ```sql
   CREATE INDEX idx_tasks_creator_id ON tasks(creator_id);
   CREATE INDEX idx_tasks_assignee ON tasks(assignee);
   ```

## 后续改进

### 短期优化（P1）
- [ ] 优化普通用户的匹配逻辑，减少数据库查询
- [ ] 添加性能测试，评估大数据量下的响应时间
- [ ] 添加单元测试覆盖各种权限场景

### 中期优化（P2）
- [ ] 支持部门级数据范围（`data_scope = "department"`）
- [ ] 添加审计日志，记录所有数据访问
- [ ] 支持更细粒度的权限控制（如按优先级、状态过滤）

### 长期优化（P3）
- [ ] 实现基于属性的访问控制（ABAC）
- [ ] 支持动态权限规则配置
- [ ] 集成外部权限管理系统

## 安全性检查

✅ **已实现**:
- 未登录用户无法访问任何数据
- 普通用户只能访问相关数据
- 管理员权限通过数据库角色验证

✅ **防护措施**:
- Session验证
- 数据范围强制执行
- 日志记录所有访问

## 兼容性

### 向后兼容性
- ✅ 现有API调用不受影响（如果已登录）
- ✅ 前端无需修改（自动应用权限过滤）
- ⚠️ 未登录访问行为变化（从显示所有数据→显示空数据）

### API变更
- `GET /api/tasks` 端点添加了权限检查
- 响应格式保持不变
- 新增日志记录用户访问行为

## 验证清单

- [x] 未登录用户访问返回空数据
- [x] 系统管理员可以查看所有任务
- [x] 代码已部署到开发环境
- [x] 日志正常输出权限检查信息
- [ ] 创建普通用户并测试权限过滤
- [ ] 性能测试（响应时间 < 500ms）
- [ ] 单元测试覆盖率 > 80%

## 结论

数据权限过滤功能已成功实现并部署到开发环境。核心功能正常工作，但还需要：

1. 创建普通用户账号进行完整测试
2. 优化普通用户的匹配逻辑以提高性能
3. 添加自动化测试确保功能稳定性

**状态**: ✅ 已完成核心功能
**下一步**: 创建测试用户并进行完整的端到端测试
