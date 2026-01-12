# 派工系统审批管理技术设计

**日期**: 2025-10-21
**版本**: v1.0
**设计原则**: Simple, Pragmatic, Backward Compatible

---

## 一、核心问题

### 1.1 现状
当前系统只具备**数据展示**能力:
- 从飞书多维表格同步任务数据到本地数据库
- 通过FastAPI后端和React前端展示周/月任务视图
- 支持筛选器和统计功能

### 1.2 缺失能力
完整的派工管理需要支持**全生命周期操作**:
- ✅ 新建派工
- ✅ 修改派工(日期、内容、人员)
- ✅ 转交派工
- ✅ 关闭派工
- ✅ 完成派工

### 1.3 设计约束
- **零破坏**: 现有数据展示功能和API端点必须保持向后兼容
- **复用优先**: 使用飞书原生审批流程,避免重复开发审批引擎
- **最简实现**: 不引入复杂状态机,直接依赖飞书审批状态
- **数据一致性**: 确保审批实例、多维表格、本地数据库三者数据同步

---

## 二、架构设计

### 2.1 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                    数据流向(Data Flow)                        │
└─────────────────────────────────────────────────────────────┘

用户操作 → FastAPI审批API → 飞书审批实例(主数据源)
                                  ↓
                          飞书多维表格(副数据源) ← 审批通过后自动同步
                                  ↓
                          sync_feishu_to_db.py
                                  ↓
                          本地SQLite/MySQL(展示用)
                                  ↓
                          FastAPI查询API → 前端展示
```

**关键设计决策**:
1. **主数据源**: 飞书审批实例(权威来源,记录完整审批流程)
2. **副数据源**: 飞书多维表格(用于批量展示和历史归档)
3. **展示层缓存**: 本地数据库(快速查询,支持复杂筛选)

### 2.2 数据结构调整

#### 2.2.1 tasks表扩展(零破坏方案)

```sql
-- 现有字段保持不变
-- 新增字段(通过ALTER TABLE添加)

ALTER TABLE tasks ADD COLUMN approval_instance_code TEXT;
  -- 关联的飞书审批实例唯一标识
  -- 示例: "81D31358-93AF-92D6-7425-01A5D67C4E71"

ALTER TABLE tasks ADD COLUMN approval_status TEXT;
  -- 审批状态: PENDING/APPROVED/REJECTED/CANCELED/DELETED
  -- 用于前端展示审批进度
```

**向后兼容性**:
- 现有任务记录这两个字段为`NULL`
- API响应模型中这两个字段设为`Optional`
- 前端可选择性升级,无需强制修改

#### 2.2.2 数据库迁移策略

```python
# backend/migrations/add_approval_fields.py

def upgrade_sqlite(conn):
    """SQLite迁移"""
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE tasks ADD COLUMN approval_instance_code TEXT")
    cursor.execute("ALTER TABLE tasks ADD COLUMN approval_status TEXT")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_approval_instance ON tasks(approval_instance_code)")

def upgrade_mysql(conn):
    """MySQL迁移(语法略有不同)"""
    cursor = conn.cursor()
    cursor.execute("""
        ALTER TABLE tasks
        ADD COLUMN approval_instance_code VARCHAR(255),
        ADD COLUMN approval_status VARCHAR(50)
    """)
    cursor.execute("CREATE INDEX idx_tasks_approval_instance ON tasks(approval_instance_code)")
```

---

## 三、审批管理API设计

### 3.1 飞书审批API封装

**文件**: `backend/feishu_approval.py`

```python
class FeishuApprovalManager:
    """飞书原生审批管理器"""

    def __init__(self, app_id: str, app_secret: str, approval_code: str):
        """
        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            approval_code: 审批定义ID(需预先在飞书审批中心配置)
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.approval_code = approval_code
        self._token_cache = None

    def get_tenant_access_token(self) -> str:
        """获取tenant_access_token(复用FeishuBitableReader逻辑)"""
        pass

    def create_instance(self, user_id: str, form_data: dict, uuid: str) -> str:
        """
        创建审批实例

        Args:
            user_id: 发起人ID
            form_data: 表单数据,必须匹配审批定义的控件结构
            uuid: 幂等键,防止重复创建

        Returns:
            instance_code: 审批实例唯一标识

        API: POST /open-apis/approval/v4/instances
        """
        pass

    def cancel_instance(self, instance_code: str, user_id: str) -> bool:
        """
        撤回审批实例

        Args:
            instance_code: 审批实例ID
            user_id: 发起人ID(必须是实例创建者)

        Returns:
            成功返回True,失败抛出异常

        API: POST /open-apis/approval/v4/instances/cancel
        """
        pass

    def get_instance_detail(self, instance_code: str) -> dict:
        """
        获取审批实例详情

        Returns:
            {
                "approval_name": "派工申请",
                "status": "PENDING",
                "form": "[{...}]",
                "task_list": [{...}],
                "timeline": [{...}]
            }

        API: GET /open-apis/approval/v4/instances/{instance_code}
        """
        pass

    def cc_instance(self, instance_code: str, cc_user_ids: List[str], comment: str) -> bool:
        """
        抄送审批实例

        用例: 派工转交时通知原派工人

        API: POST /open-apis/approval/v4/instances/cc
        """
        pass
```

### 3.2 REST API端点设计

**文件**: `backend/main.py`

#### 3.2.1 创建派工

```python
@app.post("/api/approvals", dependencies=[Depends(verify_readonly_api_key)])
async def create_dispatch(
    task_name: str,
    assignee: str,
    priority: str,
    start_date: str,
    end_date: str,
    user_id: str,  # 发起人
    api_key: str = Depends(verify_readonly_api_key)
) -> dict:
    """
    新建派工(创建飞书审批实例)

    流程:
    1. 验证参数合法性(日期格式、工程师存在性)
    2. 构造审批表单数据
    3. 调用FeishuApprovalManager.create_instance()
    4. 将instance_code写入本地数据库(临时记录,等待审批通过后正式同步)
    5. 返回审批实例URL供用户跳转查看

    Request Body:
    {
        "task_name": "阿里巴巴网络故障排查",
        "assignee": "张三",
        "priority": "紧急",
        "start_date": "2025-10-22",
        "end_date": "2025-10-23",
        "user_id": "f7cb567e"
    }

    Response:
    {
        "success": true,
        "instance_code": "81D31358-93AF-92D6-7425-01A5D67C4E71",
        "approval_url": "https://applink.feishu.cn/client/approval/...",
        "message": "派工申请已提交,等待审批"
    }
    """
```

#### 3.2.2 修改派工

```python
@app.put("/api/approvals/{instance_code}", dependencies=[Depends(verify_readonly_api_key)])
async def update_dispatch(
    instance_code: str,
    task_name: Optional[str] = None,
    assignee: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: str = Query(...),
    api_key: str = Depends(verify_readonly_api_key)
) -> dict:
    """
    修改派工(撤回旧实例+创建新实例)

    流程:
    1. 查询原实例详情,获取现有表单数据
    2. 用新参数覆盖需要修改的字段
    3. 撤回原实例(cancel_instance)
    4. 创建新实例,并在备注中标注"修改自{old_instance_code}"
    5. 更新本地数据库的instance_code关联

    设计原则:
    - 飞书审批不支持直接修改已提交的实例
    - 采用"撤回+新建"模式,保持审批历史完整性
    - 新实例中通过modified_instance_code字段关联原实例

    Response:
    {
        "success": true,
        "old_instance_code": "81D31358-93AF-92D6-7425-01A5D67C4E71",
        "new_instance_code": "92E42469-A4BG-33E7-8536-12B6D78D5F82",
        "message": "派工已修改,等待审批"
    }
    """
```

#### 3.2.3 转交派工

```python
@app.post("/api/approvals/{instance_code}/transfer", dependencies=[Depends(verify_readonly_api_key)])
async def transfer_dispatch(
    instance_code: str,
    new_assignee: str,
    user_id: str,
    reason: Optional[str] = None,
    api_key: str = Depends(verify_readonly_api_key)
) -> dict:
    """
    转交派工(修改派工人员)

    流程:
    1. 撤回原实例
    2. 创建新实例,assignee字段替换为new_assignee
    3. 抄送原派工人(cc_instance),通知转交信息

    Request Body:
    {
        "new_assignee": "李四",
        "user_id": "f7cb567e",
        "reason": "张三请假,临时调整"
    }

    Response:
    {
        "success": true,
        "new_instance_code": "...",
        "message": "派工已转交至李四,已通知原派工人张三"
    }
    """
```

#### 3.2.4 关闭派工

```python
@app.delete("/api/approvals/{instance_code}", dependencies=[Depends(verify_readonly_api_key)])
async def close_dispatch(
    instance_code: str,
    user_id: str,
    reason: Optional[str] = None,
    api_key: str = Depends(verify_readonly_api_key)
) -> dict:
    """
    关闭派工(撤回审批实例)

    流程:
    1. 调用cancel_instance()撤回实例
    2. 更新本地数据库approval_status为CANCELED

    用例:
    - 任务取消
    - 客户临时取消服务请求

    Response:
    {
        "success": true,
        "message": "派工已关闭"
    }
    """
```

#### 3.2.5 完成派工

```python
@app.post("/api/approvals/{instance_code}/complete", dependencies=[Depends(verify_readonly_api_key)])
async def complete_dispatch(
    instance_code: str,
    user_id: str,
    completion_note: Optional[str] = None,
    api_key: str = Depends(verify_readonly_api_key)
) -> dict:
    """
    完成派工(标记任务完成)

    流程:
    1. 验证审批实例状态为APPROVED
    2. 更新多维表格中的"申请状态"字段为"已完成"
    3. 触发同步,更新本地数据库

    注意: 飞书审批实例本身不支持"完成"状态,需通过多维表格字段记录

    Request Body:
    {
        "user_id": "f7cb567e",
        "completion_note": "故障已排查,恢复正常"
    }

    Response:
    {
        "success": true,
        "message": "派工已标记为完成"
    }
    """
```

#### 3.2.6 查询审批详情

```python
@app.get("/api/approvals/{instance_code}", dependencies=[Depends(verify_readonly_api_key)])
async def get_approval_detail(
    instance_code: str,
    api_key: str = Depends(verify_readonly_api_key)
) -> dict:
    """
    查询审批实例详情

    返回:
    - 审批状态
    - 表单内容
    - 审批节点任务列表
    - 审批历史时间线

    Response:
    {
        "instance_code": "...",
        "approval_name": "派工申请",
        "status": "APPROVED",
        "form_data": {
            "task_name": "...",
            "assignee": "...",
            "priority": "...",
            ...
        },
        "task_list": [
            {
                "id": "1234",
                "user_id": "f7cb567e",
                "status": "PENDING",
                "node_name": "部门主管审批"
            }
        ],
        "timeline": [
            {
                "type": "PASS",
                "create_time": "1564590532967",
                "comment": "同意"
            }
        ]
    }
    """
```

---

## 四、数据同步机制

### 4.1 双向同步策略

```
┌──────────────────────────────────────────────────────────┐
│              数据同步流程(Sync Workflow)                   │
└──────────────────────────────────────────────────────────┘

【新建派工】
用户 → POST /api/approvals → 飞书审批实例(状态:PENDING)
                                    ↓
                            (人工审批或自动通过)
                                    ↓
                            审批通过(状态:APPROVED)
                                    ↓
                            飞书多维表格新增记录 ← 飞书自动化/webhook
                                    ↓
                            sync_feishu_to_db.py定时同步
                                    ↓
                            本地数据库更新

【修改派工】
用户 → PUT /api/approvals/{id} → 撤回旧实例 + 创建新实例
                                    ↓
                            飞书多维表格更新记录
                                    ↓
                            sync_feishu_to_db.py同步

【关闭派工】
用户 → DELETE /api/approvals/{id} → 撤回审批实例
                                    ↓
                            飞书多维表格标记为已取消
                                    ↓
                            本地数据库同步状态
```

### 4.2 同步逻辑增强

**文件**: `backend/process_feishu_data.py`

```python
def process_feishu_records(raw_records: List[dict]) -> Dict[str, List[dict]]:
    """
    处理飞书原始数据,增加审批实例关联

    修改点:
    1. 从fields中提取"审批实例ID"字段(如果存在)
    2. 提取"审批状态"字段(如果存在)
    3. 添加到处理后的任务记录中

    向后兼容:
    - 如果多维表格中没有这两个字段,设为None,不影响现有逻辑
    """

    APPROVAL_INSTANCE_FIELD = "审批实例ID"  # 多维表格中的字段名
    APPROVAL_STATUS_FIELD = "审批状态"

    for record in raw_records:
        fields = record.get("fields", {})

        # 提取审批关联信息
        approval_instance_code = fields.get(APPROVAL_INSTANCE_FIELD)
        approval_status = fields.get(APPROVAL_STATUS_FIELD)

        # 添加到任务记录
        task["approval_instance_code"] = approval_instance_code
        task["approval_status"] = approval_status
```

**文件**: `backend/task_db.py`

```python
def save_processed_tasks_to_db(processed_tasks: Dict[str, List[Dict[str, Any]]]):
    """
    保存任务到数据库,支持审批字段

    修改点:
    - INSERT语句增加approval_instance_code和approval_status字段
    """

    cursor.execute("""
        INSERT OR REPLACE INTO tasks
        (record_id, task_name, assignee, status, date, start_date, end_date, weekday,
         priority, application_status, approval_instance_code, approval_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task["record_id"],
        task["task_name"],
        task["assignee"],
        task["status"],
        task["date"],
        task.get("start_date"),
        task.get("end_date"),
        weekday,
        task.get("priority", ""),
        task.get("application_status", ""),
        task.get("approval_instance_code"),  # 新增
        task.get("approval_status")          # 新增
    ))
```

### 4.3 飞书多维表格配置

**需要在飞书多维表格中添加以下字段**:

| 字段名         | 字段类型 | 说明                              | 示例值                                  |
|---------------|---------|----------------------------------|----------------------------------------|
| 审批实例ID     | 文本    | 关联的飞书审批instance_code       | 81D31358-93AF-92D6-7425-01A5D67C4E71   |
| 审批状态       | 单选    | PENDING/APPROVED/REJECTED/CANCELED| APPROVED                               |

**飞书自动化配置**(推荐):
- 触发条件: 审批通过
- 动作: 在多维表格中新增/更新记录,填充审批实例ID和状态

---

## 五、前端集成(可选)

### 5.1 任务卡片操作按钮

```jsx
// frontend/src/components/TaskCard.js

function TaskCard({ task }) {
  const handleModify = async () => {
    // 弹出修改表单
    const newData = await showModifyDialog(task);

    // 调用后端API
    const response = await fetch(`/api/approvals/${task.approval_instance_code}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
      },
      body: JSON.stringify(newData)
    });

    const result = await response.json();
    showNotification(result.message);
  };

  return (
    <div className="task-card">
      {/* 现有任务信息展示 */}

      {task.approval_instance_code && (
        <div className="task-actions">
          <button onClick={handleModify}>修改</button>
          <button onClick={handleTransfer}>转交</button>
          <button onClick={handleClose}>关闭</button>
          <button onClick={handleComplete}>完成</button>
        </div>
      )}
    </div>
  );
}
```

### 5.2 新建派工表单

```jsx
// frontend/src/components/CreateDispatch.js

function CreateDispatch() {
  const [formData, setFormData] = useState({
    task_name: '',
    assignee: '',
    priority: '紧急',
    start_date: '',
    end_date: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();

    const response = await fetch('/api/approvals', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
      },
      body: JSON.stringify({
        ...formData,
        user_id: currentUserId
      })
    });

    const result = await response.json();

    if (result.success) {
      showNotification('派工申请已提交');
      // 可选: 打开飞书审批URL
      window.open(result.approval_url, '_blank');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* 表单字段 */}
    </form>
  );
}
```

---

## 六、错误处理

### 6.1 审批API调用失败

```python
# backend/feishu_approval.py

def create_instance(self, user_id: str, form_data: dict, uuid: str) -> str:
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        if data.get("code") != 0:
            raise ApprovalAPIError(f"Feishu API error: {data.get('msg')}")

        return data["data"]["instance_code"]

    except requests.RequestException as e:
        logger.exception("Failed to create approval instance")
        raise ApprovalAPIError(f"Network error: {str(e)}")
```

### 6.2 幂等性保证

```python
@app.post("/api/approvals")
async def create_dispatch(...):
    # 生成UUID防止重复创建
    import uuid
    idempotency_key = str(uuid.uuid4())

    try:
        instance_code = approval_manager.create_instance(
            user_id=user_id,
            form_data=form_data,
            uuid=idempotency_key
        )
    except ApprovalAPIError as e:
        if "duplicate uuid" in str(e).lower():
            # 重复请求,返回已存在的实例
            return {"success": False, "message": "审批申请已提交,请勿重复操作"}
        raise
```

### 6.3 权限验证

```python
def verify_dispatch_permission(user_id: str, operation: str, target_instance: dict) -> bool:
    """
    验证用户是否有权限操作派工

    规则:
    - 修改/关闭: 仅限发起人或管理员
    - 转交: 仅限发起人、当前派工人或管理员
    - 完成: 仅限当前派工人或管理员
    """

    if is_admin(user_id):
        return True

    if operation in ["update", "close"]:
        return user_id == target_instance["creator_id"]

    if operation == "transfer":
        return user_id in [target_instance["creator_id"], target_instance["assignee_id"]]

    if operation == "complete":
        return user_id == target_instance["assignee_id"]

    return False
```

---

## 七、环境变量配置

```bash
# .env 文件

# 飞书审批配置
FEISHU_APPROVAL_CODE=4202AD96-9EC1-4284-9C48-B923CDC4F30B  # 审批定义ID
FEISHU_APPROVAL_ADMIN_USER_ID=f7cb567e  # 默认发起人ID(系统自动创建时使用)

# 多维表格配置(现有)
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_APP_TOKEN=xxx
FEISHU_TABLE_ID=tblxxx

# API认证(现有)
API_KEYS=admin-key-1,admin-key-2
READONLY_API_KEYS=readonly-key-1,readonly-key-2
```

**获取审批定义ID**:
1. 在飞书审批中心创建"派工申请"审批模板
2. 配置表单控件(任务名称、派工人、优先级、开始日期、结束日期等)
3. 配置审批流程(可设为自动通过或需要主管审批)
4. 在浏览器开发者工具中查看审批URL,提取`approval_code`参数

---

## 八、测试策略

### 8.1 单元测试

```python
# backend/test_feishu_approval.py

import pytest
from feishu_approval import FeishuApprovalManager

@pytest.fixture
def approval_manager():
    return FeishuApprovalManager(
        app_id=os.getenv("FEISHU_APP_ID"),
        app_secret=os.getenv("FEISHU_APP_SECRET"),
        approval_code=os.getenv("FEISHU_APPROVAL_CODE")
    )

def test_create_instance(approval_manager):
    """测试创建审批实例"""
    form_data = {
        "task_name": "测试任务",
        "assignee": "张三",
        "priority": "紧急",
        "start_date": "2025-10-22",
        "end_date": "2025-10-23"
    }

    instance_code = approval_manager.create_instance(
        user_id="f7cb567e",
        form_data=form_data,
        uuid="test-uuid-12345"
    )

    assert instance_code is not None
    assert len(instance_code) > 0

def test_cancel_instance(approval_manager):
    """测试撤回审批实例"""
    # 先创建实例
    instance_code = create_test_instance()

    # 撤回
    result = approval_manager.cancel_instance(instance_code, "f7cb567e")
    assert result is True

    # 验证状态
    detail = approval_manager.get_instance_detail(instance_code)
    assert detail["status"] == "CANCELED"
```

### 8.2 集成测试

```bash
# 测试完整派工流程

# 1. 创建派工
curl -X POST http://localhost:8000/api/approvals \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "测试任务",
    "assignee": "张三",
    "priority": "紧急",
    "start_date": "2025-10-22",
    "end_date": "2025-10-23",
    "user_id": "f7cb567e"
  }'

# 2. 查询审批详情
curl -H "X-API-Key: admin-key-1" \
  http://localhost:8000/api/approvals/81D31358-93AF-92D6-7425-01A5D67C4E71

# 3. 修改派工
curl -X PUT http://localhost:8000/api/approvals/81D31358-93AF-92D6-7425-01A5D67C4E71 \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "assignee": "李四",
    "user_id": "f7cb567e"
  }'

# 4. 转交派工
curl -X POST http://localhost:8000/api/approvals/81D31358-93AF-92D6-7425-01A5D67C4E71/transfer \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "new_assignee": "王五",
    "user_id": "f7cb567e",
    "reason": "临时调整"
  }'

# 5. 完成派工
curl -X POST http://localhost:8000/api/approvals/81D31358-93AF-92D6-7425-01A5D67C4E71/complete \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "f7cb567e",
    "completion_note": "任务已完成"
  }'

# 6. 关闭派工
curl -X DELETE http://localhost:8000/api/approvals/81D31358-93AF-92D6-7425-01A5D67C4E71 \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "f7cb567e",
    "reason": "客户取消"
  }'
```

---

## 九、性能考虑

### 9.1 API调用限流

飞书API有请求频率限制:
- 租户级别: 50 QPS
- 应用级别: 30 QPS

**应对策略**:
1. 在`feishu_approval.py`中添加令牌桶限流
2. 对于批量操作,使用队列异步处理
3. 缓存审批详情,减少重复查询

```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=30, period=1)  # 30次/秒
def _call_feishu_api(self, method: str, url: str, **kwargs):
    """飞书API调用包装,自动限流"""
    return requests.request(method, url, **kwargs)
```

### 9.2 数据库索引优化

```sql
-- 审批实例查询索引
CREATE INDEX idx_tasks_approval_instance ON tasks(approval_instance_code);

-- 复合索引(按工程师查询审批任务)
CREATE INDEX idx_tasks_assignee_approval_status ON tasks(assignee, approval_status);
```

---

## 十、安全注意事项

### 10.1 API Key管理

- **不要**在代码中硬编码API Key
- 使用环境变量或密钥管理服务(如AWS Secrets Manager)
- 定期轮换API Key

### 10.2 审批实例访问控制

```python
@app.get("/api/approvals/{instance_code}")
async def get_approval_detail(
    instance_code: str,
    api_key: str = Depends(verify_readonly_api_key)
):
    # 验证用户是否有权限查看该审批实例
    user_id = get_user_id_from_api_key(api_key)

    detail = approval_manager.get_instance_detail(instance_code)

    # 仅允许发起人、派工人或管理员查看
    allowed_users = [
        detail["user_id"],  # 发起人
        detail["form_data"]["assignee_id"],  # 派工人
    ]

    if user_id not in allowed_users and not is_admin(user_id):
        raise HTTPException(status_code=403, detail="无权限查看该审批")

    return detail
```

### 10.3 SQL注入防护

使用参数化查询(已在现有代码中实现):

```python
# ✅ 正确: 使用参数化查询
cursor.execute(
    "SELECT * FROM tasks WHERE approval_instance_code = ?",
    (instance_code,)
)

# ❌ 错误: 字符串拼接(易受SQL注入攻击)
cursor.execute(
    f"SELECT * FROM tasks WHERE approval_instance_code = '{instance_code}'"
)
```

---

## 十一、部署清单

### 11.1 飞书配置

- [ ] 在飞书审批中心创建"派工申请"审批模板
- [ ] 配置审批表单(字段名必须与代码中的常量对应)
- [ ] 配置审批流程(审批人/抄送人)
- [ ] 获取`approval_code`并配置到`.env`
- [ ] 在飞书多维表格中添加"审批实例ID"和"审批状态"字段
- [ ] (可选)配置飞书自动化,审批通过后自动更新多维表格

### 11.2 后端部署

- [ ] 运行数据库迁移脚本: `python backend/migrations/add_approval_fields.py`
- [ ] 更新`.env`文件,添加`FEISHU_APPROVAL_CODE`
- [ ] 部署`feishu_approval.py`模块
- [ ] 更新`main.py`,添加审批管理端点
- [ ] 重启FastAPI服务: `docker-compose restart backend`
- [ ] 验证API文档: 访问`http://localhost:8000/docs`,确认新端点可见

### 11.3 数据同步

- [ ] 修改`process_feishu_data.py`,增加审批字段提取逻辑
- [ ] 修改`task_db.py`,支持保存审批字段
- [ ] 手动触发一次同步验证: `python backend/sync_once.py`
- [ ] 检查数据库: `python backend/check_db.py`,确认审批字段已填充

### 11.4 前端集成(可选)

- [ ] 修改`TaskCard`组件,添加操作按钮
- [ ] 实现修改/转交/关闭/完成功能
- [ ] 添加新建派工表单页面
- [ ] 测试完整用户流程

---

## 十二、后续优化方向

### 12.1 审批流程可视化

在前端展示审批进度:
- 当前节点: 部门主管审批中
- 已通过节点: 发起 → 直属上级
- 待审批人: 张经理

### 12.2 批量派工

支持一次创建多个派工任务:
```python
@app.post("/api/approvals/batch")
async def create_batch_dispatches(tasks: List[DispatchTask]):
    """批量创建派工"""
    results = []
    for task in tasks:
        instance_code = approval_manager.create_instance(...)
        results.append(instance_code)
    return {"created": len(results), "instances": results}
```

### 12.3 审批通知

集成飞书消息推送:
- 审批通过 → 通知派工人
- 派工修改 → 通知相关人员
- 派工转交 → 通知原派工人和新派工人

### 12.4 统计报表

新增审批统计API:
- 本周新建派工数
- 各工程师审批通过率
- 平均审批耗时

---

## 十三、常见问题

### Q1: 如果飞书审批被拒绝,如何处理?

**A**: 审批状态会同步到本地数据库,前端可根据`approval_status=REJECTED`显示"已拒绝"标签。用户可选择修改后重新提交。

### Q2: 修改派工时,原审批历史是否保留?

**A**: 保留。通过`modified_instance_code`字段关联原实例,在审批详情中可查看完整变更历史。

### Q3: 多维表格和审批实例数据不一致怎么办?

**A**: 以审批实例为准。可通过`/api/approvals/{instance_code}`查询权威数据,并手动触发`/api/sync`同步到多维表格和本地数据库。

### Q4: 是否支持离线操作?

**A**: 不支持。所有审批操作都需要调用飞书API,需要网络连接。本地数据库仅用于展示查询。

### Q5: 如何防止派工重复创建?

**A**: 前端提交时生成`uuid`,后端检测到重复`uuid`时返回错误。建议前端添加防抖逻辑,避免用户重复点击。

---

## 十四、参考资料

- [飞书原生审批实例概述](https://open.feishu.cn/document/server-docs/approval-v4/instance/overview-approval-instance)
- [飞书开放平台API文档](https://open.feishu.cn/document/home/introduction-to-api-call-method/overview)
- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [SQLite ALTER TABLE语法](https://www.sqlite.org/lang_altertable.html)

---

**版本历史**

| 版本 | 日期       | 修改内容           | 作者  |
|-----|-----------|-------------------|------|
| v1.0| 2025-10-21| 初始版本           | Claude Code |

