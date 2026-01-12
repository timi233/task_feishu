# 飞书组织架构用户同步功能

**日期**: 2025-11-03
**功能**: 从飞书组织架构同步所有用户到系统

---

## 功能概述

实现了从飞书组织架构完整同步所有用户的功能，替代了之前从任务数据中提取工程师的临时方案。

### 核心功能
1. **遍历组织架构**：自动遍历飞书所有部门，递归获取完整组织结构
2. **用户去重**：自动去除重复用户（同一用户在多个部门的情况）
3. **完整信息**：同步用户的姓名、邮箱、手机号、部门信息、在职状态
4. **权限控制**：需要系统管理员权限才能执行同步

---

## 实现细节

### 1. 后端实现

#### 新增文件
- **`backend/sync_users_from_feishu_full.py`**
  - 核心类：`FeishuOrgReader`
  - 功能：
    - `get_all_departments()`: 递归遍历获取所有部门
    - `get_users_in_department()`: 获取指定部门的用户
    - `get_all_users()`: 汇总所有用户并去重
  - 数据流程：
    ```
    飞书API → 获取部门树 → 遍历各部门 → 获取用户 → 去重 → 同步到engineers表
    ```

#### API端点更新
- **`POST /api/users/sync/feishu`**
  - 更新为调用`sync_users_from_feishu_org()`
  - 返回同步结果统计（总用户数、新增数、更新数）

#### 飞书API调用
使用的飞书开放平台API：
1. **部门API**: `GET /open-apis/contact/v3/departments`
   - 获取组织架构树
   - 支持分页
   - 从根部门（`parent_department_id="0"`）开始递归遍历

2. **用户API**: `GET /open-apis/contact/v3/users`
   - 按部门获取用户列表
   - 支持分页
   - 返回用户详细信息（姓名、邮箱、手机、部门、状态等）

### 2. 前端实现

#### UserManagement组件更新
```javascript
// frontend/src/components/UserManagement.js
<button
  className="sync-button"
  onClick={() => handleSyncUsers('feishu')}
  disabled={syncing}
  title="从飞书组织架构同步所有用户（遍历所有部门）"
>
  {syncing ? '同步中...' : '同步飞书组织架构'}
</button>
```

移除了之前的：
- "同步 (Identity Hub)" 按钮
- "同步 (任务数据)" 按钮

---

## 测试结果

### 同步测试
**测试时间**: 2025-11-03 17:45
**测试结果**: ✅ 成功

```
✅ 成功获取tenant_access_token
✅ 共获取 10 个部门
  - 售后技术部
  - 爱数销售
  - IPG销售
  - 亿格云销售
  - 后勤
  - 运营
  - 集成 (x2)
  - 运维
  - 分销
✅ 共获取 24 个唯一用户
```

### 同步性能
- 获取10个部门：约3秒
- 获取24个用户：约6秒
- 总耗时：约9秒

---

## 使用指南

### 系统管理员操作步骤

1. **登录系统**
   - 访问 http://10.242.94.9:3000
   - 使用OAuth登录（需要有系统管理员角色）

2. **进入用户管理页面**
   - 点击顶部导航栏的"用户管理"按钮
   - （仅系统管理员可见此按钮）

3. **执行同步**
   - 点击"同步飞书组织架构"按钮
   - 等待10-20秒（取决于组织规模）
   - 查看同步结果提示

4. **查看用户列表**
   - 点击"刷新"按钮
   - 所有飞书组织架构中的用户将显示
   - 可以使用搜索框筛选用户

5. **分配角色**
   - 点击用户行的"管理角色"按钮
   - 选择要分配的角色
   - 保存更改

---

## 数据结构

### Engineers表字段
```sql
CREATE TABLE engineers (
    user_id TEXT PRIMARY KEY,       -- 飞书user_id
    name TEXT,                      -- 用户姓名
    email TEXT,                     -- 邮箱
    mobile TEXT,                    -- 手机号
    department_name TEXT,           -- 部门名称
    status INTEGER DEFAULT 1,       -- 状态：1=在职，0=离职
    synced_at TIMESTAMP             -- 同步时间
)
```

### 用户状态判断逻辑
```python
# 判断用户是否在职
is_activated = status_info.get("is_activated", False)
is_resigned = status_info.get("is_resigned", False)
is_frozen = status_info.get("is_frozen", False)

# 在职条件：已激活 且 未离职 且 未冻结
status = 1 if (is_activated and not is_resigned and not is_frozen) else 0
```

---

## 飞书权限配置

### 必须开通的权限
在飞书开放平台应用管理中，需要开通以下权限：

1. **获取部门基础信息**
   - 权限代码：`contact:department:read`
   - 用途：获取组织架构树

2. **获取用户基本信息**
   - 权限代码：`contact:user:read`
   - 用途：获取用户详细信息

### 权限配置步骤
1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 进入"应用管理" → 选择您的应用
3. 点击"权限管理"
4. 搜索并开通上述权限
5. 保存并发布版本

---

## 常见问题

### Q1: 同步失败，提示"attempt to write a readonly database"
**原因**: 数据库文件权限不足
**解决**:
```bash
sudo chown -R <your-user>:<your-group> data/db/
chmod 666 data/db/tasks.db
```

### Q2: 只同步到1个用户
**原因**: 飞书权限未开通或权限范围受限
**解决**: 检查飞书应用权限配置，确保开通了`contact:department:read`和`contact:user:read`权限

### Q3: 同步速度慢
**原因**: 组织架构层级深或用户数量多
**优化**:
- 已添加分页支持（每页50条）
- 已添加去重逻辑
- 已添加0.1秒延迟避免API限流

### Q4: 用户部门信息不准确
**说明**: 当前只记录用户在第一个被遍历到的部门名称
**计划**: 未来版本可增加多部门支持

---

## API文档

### POST /api/users/sync/feishu
从飞书组织架构同步所有用户

**权限**: role:assign (系统管理员)

**请求**:
```http
POST /api/users/sync/feishu HTTP/1.1
Cookie: task_session_id=<session_id>
```

**响应**:
```json
{
  "success": true,
  "message": "同步完成: 新增10，更新14",
  "total_users": 24,
  "created": 10,
  "updated": 14,
  "errors": []
}
```

---

## 未来改进

### 1. 增量同步
当前每次同步会遍历所有部门和用户，未来可以：
- 记录上次同步时间
- 使用飞书的变更通知API
- 只同步有变化的数据

### 2. 多部门支持
当前只记录用户在第一个被遍历到的部门，未来可以：
- 支持用户多部门归属
- 记录所有部门信息（JSON数组）
- 区分主部门和兼职部门

### 3. 定时同步
当前需要手动触发，未来可以：
- 添加定时任务（如每天凌晨自动同步）
- 支持配置同步频率
- 添加同步历史记录

### 4. 同步日志
当前只在控制台输出日志，未来可以：
- 记录详细的同步日志到数据库
- 提供同步历史查看界面
- 统计同步失败原因

---

## 相关文件

### 后端文件
- `backend/sync_users_from_feishu_full.py` - 主同步逻辑
- `backend/routers/user_sync.py` - API路由
- `backend/feishu_contacts.py` - 飞书通讯录API封装
- `backend/task_db.py` - 数据库操作

### 前端文件
- `frontend/src/components/UserManagement.js` - 用户管理界面
- `frontend/src/components/UserManagement.css` - 样式

### 文档文件
- `docs/USER_SYNC_FROM_FEISHU_ORG.md` - 本文档
- `docs/IDENTITY_HUB_PHASE3_REPORT.md` - 整体功能报告
