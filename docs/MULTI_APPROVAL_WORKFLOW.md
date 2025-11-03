# 多审批流程设计文档

**日期**: 2025-10-21
**版本**: v1.1
**设计原则**: 配置化、零破坏、简洁优先

---

## 一、需求背景

### 1.1 业务需求
系统需要支持两种不同类型的工单:
1. **公司日常工单**: 内部售后工单,包含一般性技术支持和问题处理
2. **爱数原厂派单**: 爱数原厂技术支持派单,涉及原厂产品的技术问题和售后服务

不同工单类型需要:
- **不同的审批流程**(对应不同的飞书审批定义)
- **不同的表单字段**(信息填写内容不同)
- **统一的数据管理**(存储在同一张tasks表)

### 1.2 核心挑战
- 如何在不破坏现有API的前提下增加工单类型选择?
- 如何让前端动态展示不同工单类型的表单?
- 如何确保数据库可以区分和查询不同类型的工单?

---

## 二、架构设计

### 2.1 配置化方案

通过**配置文件**而非硬编码实现工单类型管理:

```python
# backend/approval_config.py
APPROVAL_TYPES = {
    "daily_work": {
        "name": "公司日常工单",
        "approval_code_env": "FEISHU_APPROVAL_CODE",
        "required_fields": ["task_name", "assignee", "priority", ...],
        "field_labels": {...}
    },
    "eisoo_vendor": {
        "name": "爱数原厂派单",
        "approval_code_env": "FEISHU_APPROVAL_CODE_EISOO",
        "required_fields": ["customer_name", "issue_type", ...],
        "field_labels": {...}
    }
}
```

**优势**:
- ✅ 新增工单类型只需修改配置,无需改代码
- ✅ 前端可通过`GET /api/approvals/types`动态获取工单类型列表
- ✅ 字段验证规则集中管理

### 2.2 数据库Schema扩展

**tasks表新增字段**:
```sql
ALTER TABLE tasks ADD COLUMN approval_type VARCHAR(50) DEFAULT 'daily_work';
```

**设计考量**:
- 默认值`daily_work`保证向后兼容(现有记录自动归类为日常工单)
- 索引优化: `CREATE INDEX idx_tasks_approval_type ON tasks(approval_type)`
- 复合索引: `CREATE INDEX idx_tasks_approval_type_status ON tasks(approval_type, approval_status)`

### 2.3 API向后兼容策略

**关键设计**: `approval_type`参数设为可选,默认值为`daily_work`

```python
# POST /api/approvals
class CreateDispatchRequest(BaseModel):
    approval_type: str = "daily_work"  # 默认值
    task_name: str
    assignee: str
    # ... 其他字段
```

**兼容性保证**:
- 旧的API调用(不传`approval_type`)自动使用`daily_work`
- 新的API调用可以明确指定工单类型
- 飞书审批Code在运行时动态解析,支持多环境配置

---

## 三、工单类型定义

### 3.1 公司日常工单 (daily_work)

**审批定义Code**: 由环境变量`FEISHU_APPROVAL_CODE`指定

**必填字段**:
| 字段ID | 字段名称 | 类型 | 说明 |
|--------|---------|------|------|
| task_name | 任务名称 | 文本 | 工作任务简要描述 |
| assignee | 派工人员 | 人员 | 负责处理的工程师 |
| priority | 优先级 | 单选 | 非常紧急/紧急/重要/普通 |
| start_date | 服务开始时间 | 日期 | 任务开始日期 |
| end_date | 服务结束时间 | 日期 | 任务结束日期 |

**选填字段**:
| 字段ID | 字段名称 | 类型 | 说明 |
|--------|---------|------|------|
| description | 工作内容 | 多行文本 | 详细工作描述 |
| customer_name | 客户公司名称 | 文本 | 客户信息(可选) |

**适用场景**:
- 内部技术支持
- 日常维护工作
- 问题排查与修复
- 一般性客户服务

### 3.2 爱数原厂派单 (eisoo_vendor)

**审批定义Code**: `1258F9D1-FFEB-4C1F-A0ED-200A7807261A` (由环境变量`FEISHU_APPROVAL_CODE_EISOO`指定)

**必填字段**:
| 字段ID | 字段名称 | 类型 | 说明 |
|--------|---------|------|------|
| customer_name | 客户名称 | 文本 | 最终客户名称 |
| issue_type | 问题类型 | 单选 | 硬件故障/软件故障/性能问题等 |
| urgency | 紧急程度 | 单选 | 紧急/高/中/低 |
| contact_person | 联系人 | 文本 | 客户联系人姓名 |
| contact_phone | 联系电话 | 文本 | 客户联系方式 |
| assignee | 处理工程师 | 人员 | 负责工程师 |
| start_date | 预计开始时间 | 日期 | 预计开始处理时间 |
| end_date | 预计完成时间 | 日期 | 预计完成时间 |

**选填字段**:
| 字段ID | 字段名称 | 类型 | 说明 |
|--------|---------|------|------|
| detailed_description | 问题详细描述 | 多行文本 | 问题详情 |
| attachment_urls | 附件链接 | 文本 | 相关附件URL |
| product_model | 产品型号 | 文本 | 爱数产品型号 |
| serial_number | 序列号 | 文本 | 设备序列号 |
| warranty_status | 保修状态 | 单选 | 保内/保外/延保 |

**适用场景**:
- 爱数原厂产品技术支持
- 原厂派单工单
- 需要原厂协助的复杂问题
- 硬件故障和软件升级

---

## 四、API接口调整

### 4.1 新增端点

#### GET /api/approvals/types

**功能**: 获取所有可用的审批类型列表

**认证**: 需要API Key

**请求示例**:
```bash
curl -H "X-API-Key: admin-key-1" \
  http://localhost:8000/api/approvals/types
```

**响应示例**:
```json
{
  "success": true,
  "approval_types": [
    {
      "type": "daily_work",
      "name": "公司日常工单",
      "description": "公司内部日常售后工单,包含一般性技术支持和问题处理"
    },
    {
      "type": "eisoo_vendor",
      "name": "爱数原厂派单",
      "description": "爱数原厂技术支持派单,涉及原厂产品的技术问题和售后服务"
    }
  ]
}
```

### 4.2 现有端点扩展

#### POST /api/approvals (创建派工)

**新增参数**: `approval_type`

**向后兼容**: 不提供`approval_type`时默认为`daily_work`

**公司日常工单示例**:
```bash
curl -X POST http://localhost:8000/api/approvals \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_type": "daily_work",
    "task_name": "网络故障排查",
    "assignee": "张三",
    "priority": "紧急",
    "start_date": "2025-10-22",
    "end_date": "2025-10-23",
    "description": "客户报告网络间歇性中断",
    "user_id": "f7cb567e"
  }'
```

**爱数原厂派单示例**:
```bash
curl -X POST http://localhost:8000/api/approvals \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_type": "eisoo_vendor",
    "customer_name": "XX科技有限公司",
    "issue_type": "硬件故障",
    "urgency": "紧急",
    "contact_person": "李四",
    "contact_phone": "13800138000",
    "assignee": "王五",
    "start_date": "2025-10-22",
    "end_date": "2025-10-23",
    "detailed_description": "AnyBackup设备磁盘阵列故障,需更换硬盘",
    "product_model": "AnyBackup A6000",
    "serial_number": "AB123456789",
    "user_id": "f7cb567e"
  }'
```

**响应示例**:
```json
{
  "success": true,
  "message": "派工申请已提交,等待审批",
  "instance_code": "92E42469-A4BG-33E7-8536-12B6D78D5F82",
  "approval_url": "https://applink.feishu.cn/client/approval/detail?approvalCode=1258F9D1-FFEB-4C1F-A0ED-200A7807261A&instanceCode=92E42469-A4BG-33E7-8536-12B6D78D5F82"
}
```

**字段验证**:
- 系统会根据`approval_type`自动验证必填字段
- 缺少必填字段时返回400错误,提示缺失字段名称
- 错误示例:
  ```json
  {
    "detail": "缺少必填字段: 客户名称, 联系电话"
  }
  ```

---

## 五、前端集成指南

### 5.1 工单类型选择器

```jsx
// 组件: ApprovalTypeSelector.js
import React, { useState, useEffect } from 'react';

function ApprovalTypeSelector({ value, onChange }) {
    const [types, setTypes] = useState([]);

    useEffect(() => {
        // 获取可用工单类型
        fetch('/api/approvals/types', {
            headers: { 'X-API-Key': API_KEY }
        })
        .then(res => res.json())
        .then(data => setTypes(data.approval_types));
    }, []);

    return (
        <div className="approval-type-selector">
            <label>工单类型:</label>
            <select value={value} onChange={e => onChange(e.target.value)}>
                {types.map(type => (
                    <option key={type.type} value={type.type}>
                        {type.name}
                    </option>
                ))}
            </select>
            <p className="description">
                {types.find(t => t.type === value)?.description}
            </p>
        </div>
    );
}
```

### 5.2 动态表单渲染

```jsx
// 组件: CreateDispatchForm.js
import React, { useState } from 'react';
import DailyWorkForm from './DailyWorkForm';
import EisooVendorForm from './EisooVendorForm';
import ApprovalTypeSelector from './ApprovalTypeSelector';

function CreateDispatchForm() {
    const [approvalType, setApprovalType] = useState('daily_work');
    const [formData, setFormData] = useState({});

    const handleSubmit = async () => {
        const response = await fetch('/api/approvals', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': API_KEY
            },
            body: JSON.stringify({
                approval_type: approvalType,
                ...formData
            })
        });

        const result = await response.json();
        if (result.success) {
            alert('派工创建成功!');
            // 可选: 打开审批链接
            window.open(result.approval_url, '_blank');
        }
    };

    return (
        <div className="create-dispatch-form">
            <ApprovalTypeSelector
                value={approvalType}
                onChange={setApprovalType}
            />

            {approvalType === 'daily_work' && (
                <DailyWorkForm
                    data={formData}
                    onChange={setFormData}
                />
            )}

            {approvalType === 'eisoo_vendor' && (
                <EisooVendorForm
                    data={formData}
                    onChange={setFormData}
                />
            )}

            <button onClick={handleSubmit}>提交派工申请</button>
        </div>
    );
}
```

### 5.3 表单组件示例

**公司日常工单表单**:
```jsx
// 组件: DailyWorkForm.js
function DailyWorkForm({ data, onChange }) {
    return (
        <div className="daily-work-form">
            <input
                placeholder="任务名称 *"
                value={data.task_name || ''}
                onChange={e => onChange({...data, task_name: e.target.value})}
            />
            <input
                placeholder="派工人员 *"
                value={data.assignee || ''}
                onChange={e => onChange({...data, assignee: e.target.value})}
            />
            <select
                value={data.priority || ''}
                onChange={e => onChange({...data, priority: e.target.value})}
            >
                <option value="">选择优先级 *</option>
                <option value="非常紧急">非常紧急</option>
                <option value="紧急">紧急</option>
                <option value="重要">重要</option>
                <option value="普通">普通</option>
            </select>
            <input
                type="date"
                value={data.start_date || ''}
                onChange={e => onChange({...data, start_date: e.target.value})}
            />
            <input
                type="date"
                value={data.end_date || ''}
                onChange={e => onChange({...data, end_date: e.target.value})}
            />
            <textarea
                placeholder="工作内容描述(可选)"
                value={data.description || ''}
                onChange={e => onChange({...data, description: e.target.value})}
            />
        </div>
    );
}
```

**爱数原厂派单表单**:
```jsx
// 组件: EisooVendorForm.js
function EisooVendorForm({ data, onChange }) {
    return (
        <div className="eisoo-vendor-form">
            <input
                placeholder="客户名称 *"
                value={data.customer_name || ''}
                onChange={e => onChange({...data, customer_name: e.target.value})}
            />
            <select
                value={data.issue_type || ''}
                onChange={e => onChange({...data, issue_type: e.target.value})}
            >
                <option value="">问题类型 *</option>
                <option value="硬件故障">硬件故障</option>
                <option value="软件故障">软件故障</option>
                <option value="性能问题">性能问题</option>
                <option value="配置调整">配置调整</option>
                <option value="升级维护">升级维护</option>
                <option value="咨询服务">咨询服务</option>
                <option value="其他">其他</option>
            </select>
            <input
                placeholder="联系人 *"
                value={data.contact_person || ''}
                onChange={e => onChange({...data, contact_person: e.target.value})}
            />
            <input
                placeholder="联系电话 *"
                value={data.contact_phone || ''}
                onChange={e => onChange({...data, contact_phone: e.target.value})}
            />
            <input
                placeholder="处理工程师 *"
                value={data.assignee || ''}
                onChange={e => onChange({...data, assignee: e.target.value})}
            />
            <input
                placeholder="产品型号(可选)"
                value={data.product_model || ''}
                onChange={e => onChange({...data, product_model: e.target.value})}
            />
            <textarea
                placeholder="问题详细描述(可选)"
                value={data.detailed_description || ''}
                onChange={e => onChange({...data, detailed_description: e.target.value})}
            />
        </div>
    );
}
```

---

## 六、部署配置

### 6.1 环境变量配置

**必须配置**:
```bash
# .env 文件

# 飞书应用凭证(共用)
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx

# 公司日常工单审批Code
FEISHU_APPROVAL_CODE=原有的审批定义Code

# 爱数原厂派单审批Code
FEISHU_APPROVAL_CODE_EISOO=1258F9D1-FFEB-4C1F-A0ED-200A7807261A

# 默认发起人ID
FEISHU_APPROVAL_ADMIN_USER_ID=f7cb567e
```

### 6.2 数据库迁移

```bash
# 执行迁移脚本
cd backend
python migrations/add_approval_type_field.py
```

**迁移内容**:
- 添加`approval_type`字段,默认值`daily_work`
- 将所有现有记录设置为`daily_work`(向后兼容)
- 创建索引优化查询性能

### 6.3 飞书审批配置

**公司日常工单**:
- 使用现有的审批定义(已配置)
- 确保环境变量`FEISHU_APPROVAL_CODE`已设置

**爱数原厂派单**:
1. 在飞书审批中心打开审批定义: `1258F9D1-FFEB-4C1F-A0ED-200A7807261A`
2. 确认表单字段与`approval_config.py`中定义的字段匹配
3. 配置审批流程(审批人/抄送人)
4. 在`.env`中设置`FEISHU_APPROVAL_CODE_EISOO=1258F9D1-FFEB-4C1F-A0ED-200A7807261A`

### 6.4 多维表格字段(可选)

如果需要在多维表格中区分工单类型,添加字段:
- **字段名**: "工单类型"
- **字段类型**: 单选
- **选项**: 公司日常工单, 爱数原厂派单

---

## 七、测试验证

### 7.1 配置验证

```bash
# 测试配置文件
python backend/approval_config.py

# 预期输出:
# === 审批类型配置测试 ===
# 1. 可用审批类型:
#    - 公司日常工单 (daily_work): ...
#    - 爱数原厂派单 (eisoo_vendor): ...
```

### 7.2 API测试

```bash
# 获取工单类型列表
curl -H "X-API-Key: admin-key-1" \
  http://localhost:8000/api/approvals/types

# 创建日常工单
curl -X POST http://localhost:8000/api/approvals \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_type": "daily_work",
    "task_name": "测试任务",
    "assignee": "张三",
    "priority": "普通",
    "start_date": "2025-10-22",
    "end_date": "2025-10-23",
    "user_id": "f7cb567e"
  }'

# 创建原厂派单
curl -X POST http://localhost:8000/api/approvals \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_type": "eisoo_vendor",
    "customer_name": "测试公司",
    "issue_type": "硬件故障",
    "urgency": "高",
    "contact_person": "李四",
    "contact_phone": "13800138000",
    "assignee": "王五",
    "start_date": "2025-10-22",
    "end_date": "2025-10-23",
    "user_id": "f7cb567e"
  }'
```

### 7.3 数据库验证

```bash
# 查询不同工单类型的数量
sqlite3 data/db/tasks.db "SELECT approval_type, COUNT(*) FROM tasks GROUP BY approval_type"

# 预期输出:
# daily_work|50
# eisoo_vendor|10
```

---

## 八、扩展性设计

### 8.1 新增工单类型

**步骤**:
1. 在`backend/approval_config.py`的`APPROVAL_TYPES`字典中添加新类型定义
2. 在飞书审批中心创建对应的审批定义
3. 在`.env`中添加新的环境变量`FEISHU_APPROVAL_CODE_新类型名`
4. 前端添加对应的表单组件
5. 重启服务

**示例**: 添加"供应商派单"类型

```python
# backend/approval_config.py
APPROVAL_TYPES = {
    # ... 现有类型 ...

    "vendor_dispatch": {
        "name": "供应商派单",
        "approval_code_env": "FEISHU_APPROVAL_CODE_VENDOR",
        "required_fields": ["vendor_name", "service_type", "contact_person", ...],
        "field_labels": {...}
    }
}
```

### 8.2 字段级权限控制

**未来扩展**: 不同工单类型可配置不同的权限规则

```python
APPROVAL_TYPES = {
    "eisoo_vendor": {
        # ... 现有配置 ...
        "permissions": {
            "create": ["admin", "eisoo_manager"],
            "modify": ["admin"],
            "view": ["admin", "eisoo_manager", "engineer"]
        }
    }
}
```

---

## 九、常见问题

### Q1: 如何查看某个工单的审批类型?

**A**: 通过`GET /api/approvals/{instance_code}`端点,返回的数据中包含`approval_type`字段。

### Q2: 可以修改工单的审批类型吗?

**A**: 不建议。审批类型与审批定义Code强绑定,修改类型相当于撤回旧审批并创建新审批,可能导致审批流程混乱。

### Q3: 前端如何动态显示字段标签?

**A**: 调用`GET /api/approvals/types`获取工单类型配置,从`field_labels`字段中读取中文标签。

### Q4: 如果环境变量`FEISHU_APPROVAL_CODE_EISOO`未配置会怎样?

**A**: 创建爱数原厂派单时会返回400错误,提示"Approval code not configured for type 'eisoo_vendor'"。

### Q5: 旧的API调用(不传approval_type)会报错吗?

**A**: 不会。`approval_type`默认值为`daily_work`,完全向后兼容。

---

## 十、版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|-----|------|---------|------|
| v1.0 | 2025-10-21 | 初始版本,支持单审批流程 | Claude Code |
| v1.1 | 2025-10-21 | 增加多审批流程支持(daily_work + eisoo_vendor) | Claude Code |

---

**参考文档**:
- [派工系统审批管理设计](DISPATCH_WORKFLOW_DESIGN.md)
- [飞书原生审批API](FEISHU_NATIVE_APPROVAL.md)
- [项目README](../CLAUDE.md)
