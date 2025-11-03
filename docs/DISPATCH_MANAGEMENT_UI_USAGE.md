# 工单管理UI组件使用指南

**创建时间**: 2025-10-22

## 概述

本文档说明如何使用新创建的5个工单管理UI组件。这些组件提供了完整的派工生命周期管理界面。

## 组件清单

### 1. ConfirmDialog - 通用确认对话框
**文件**: `/home/jian/code/Task_feishu/frontend/src/components/ConfirmDialog.js`

**功能**:
- 通用模态确认对话框
- 可选输入框(用于填写原因/备注)
- 自定义标题、消息、按钮文本
- 支持危险操作样式

**Props**:
```javascript
{
  isOpen: PropTypes.bool.isRequired,           // 是否显示
  onClose: PropTypes.func.isRequired,          // 关闭回调
  onConfirm: PropTypes.func.isRequired,        // 确认回调 (inputValue) => void
  title: PropTypes.string,                     // 标题(默认"确认操作")
  message: PropTypes.string,                   // 消息(默认"确定要执行此操作吗?")
  confirmText: PropTypes.string,               // 确认按钮文本(默认"确认")
  cancelText: PropTypes.string,                // 取消按钮文本(默认"取消")
  showInput: PropTypes.bool,                   // 是否显示输入框(默认false)
  inputPlaceholder: PropTypes.string,          // 输入框占位符
  confirmButtonClass: PropTypes.string,        // 确认按钮样式类(默认蓝色)
}
```

**使用示例**:
```javascript
import ConfirmDialog from './components/ConfirmDialog';

function MyComponent() {
  const [showDialog, setShowDialog] = useState(false);

  const handleConfirm = (inputValue) => {
    console.log('用户确认,输入:', inputValue);
    // 执行操作...
  };

  return (
    <>
      <button onClick={() => setShowDialog(true)}>删除</button>

      <ConfirmDialog
        isOpen={showDialog}
        onClose={() => setShowDialog(false)}
        onConfirm={handleConfirm}
        title="确认删除"
        message="删除后无法恢复,确定要删除吗?"
        confirmText="确认删除"
        confirmButtonClass="bg-red-600 hover:bg-red-700"
        showInput
        inputPlaceholder="请输入删除原因(可选)"
      />
    </>
  );
}
```

---

### 2. UpdateDispatchModal - 修改工单弹窗
**文件**: `/home/jian/code/Task_feishu/frontend/src/components/UpdateDispatchModal.js`

**功能**:
- 修改现有工单
- 预填充当前数据
- 可修改: 工程师、优先级、开始/结束时间
- 表单验证
- 调用`updateDispatch` API

**Props**:
```javascript
{
  isOpen: PropTypes.bool.isRequired,           // 是否显示
  onClose: PropTypes.func.isRequired,          // 关闭回调
  dispatch: PropTypes.shape({                  // 工单对象
    instance_code: PropTypes.string.isRequired,
    task_name: PropTypes.string,
    assignee: PropTypes.string,
    priority: PropTypes.string,
    start_date: PropTypes.string,
    end_date: PropTypes.string,
  }),
  onSuccess: PropTypes.func,                   // 成功回调 (result) => void
}
```

**使用示例**:
```javascript
import UpdateDispatchModal from './components/UpdateDispatchModal';

function MyComponent() {
  const [showModal, setShowModal] = useState(false);
  const dispatch = {
    instance_code: '123456',
    task_name: '网络故障排查',
    assignee: '张三',
    priority: '紧急',
    start_date: '2025-10-22',
    end_date: '2025-10-23',
  };

  const handleSuccess = (result) => {
    console.log('修改成功:', result);
    // 刷新列表...
  };

  return (
    <>
      <button onClick={() => setShowModal(true)}>修改</button>

      <UpdateDispatchModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        dispatch={dispatch}
        onSuccess={handleSuccess}
      />
    </>
  );
}
```

---

### 3. TransferDispatchModal - 转交工单弹窗
**文件**: `/home/jian/code/Task_feishu/frontend/src/components/TransferDispatchModal.js`

**功能**:
- 转交工单给其他工程师
- 选择新工程师(使用EngineerSelector)
- 填写转交原因(可选)
- 验证新工程师不能与当前工程师相同
- 调用`transferDispatch` API

**Props**:
```javascript
{
  isOpen: PropTypes.bool.isRequired,           // 是否显示
  onClose: PropTypes.func.isRequired,          // 关闭回调
  dispatch: PropTypes.shape({                  // 工单对象
    instance_code: PropTypes.string.isRequired,
    task_name: PropTypes.string,
    assignee: PropTypes.string,
  }),
  onSuccess: PropTypes.func,                   // 成功回调 (result) => void
}
```

**使用示例**:
```javascript
import TransferDispatchModal from './components/TransferDispatchModal';

function MyComponent() {
  const [showModal, setShowModal] = useState(false);
  const dispatch = {
    instance_code: '123456',
    task_name: '网络故障排查',
    assignee: '张三',
  };

  const handleSuccess = (result) => {
    console.log('转交成功:', result);
    // 刷新列表...
  };

  return (
    <>
      <button onClick={() => setShowModal(true)}>转交</button>

      <TransferDispatchModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        dispatch={dispatch}
        onSuccess={handleSuccess}
      />
    </>
  );
}
```

---

### 4. DispatchOperationCard - 工单操作卡片
**文件**: `/home/jian/code/Task_feishu/frontend/src/components/DispatchOperationCard.js`

**功能**:
- 显示工单基本信息(任务名、客户、工程师、时间、状态)
- 根据状态显示对应的badge
- 提供操作按钮: 修改、转交、完成、关闭、查看详情、飞书审批链接
- 根据工单状态动态显示/隐藏按钮
- 集成其他4个组件(UpdateModal, TransferModal, ConfirmDialog)

**Props**:
```javascript
{
  dispatch: PropTypes.shape({                  // 工单对象
    instance_code: PropTypes.string.isRequired,
    task_name: PropTypes.string,
    assignee: PropTypes.string,
    customer_name: PropTypes.string,
    start_date: PropTypes.string,
    end_date: PropTypes.string,
    status: PropTypes.string,                  // pending/approved/rejected/completed/closed
    approval_url: PropTypes.string,
  }).isRequired,
  onUpdate: PropTypes.func,                    // 更新回调(刷新列表用)
}
```

**按钮显示规则**:
- **修改**: `status === 'pending' || status === 'approved'`
- **转交**: `status === 'pending' || status === 'approved'`
- **完成**: `status === 'approved'`
- **关闭**: `status !== 'completed' && status !== 'closed'`
- **查看详情**: 始终显示
- **飞书审批**: 如果有`approval_url`则显示

**使用示例**:
```javascript
import DispatchOperationCard from './components/DispatchOperationCard';

function DispatchList() {
  const dispatch = {
    instance_code: '123456',
    task_name: '网络故障排查',
    assignee: '张三',
    customer_name: '阿里巴巴',
    start_date: '2025-10-22',
    end_date: '2025-10-23',
    status: 'approved',
    approval_url: 'https://feishu.cn/approval/xxx',
  };

  const handleUpdate = () => {
    console.log('工单已更新,刷新列表');
    // 重新加载数据...
  };

  return (
    <DispatchOperationCard
      dispatch={dispatch}
      onUpdate={handleUpdate}
    />
  );
}
```

---

### 5. DispatchManagementPanel - 工单管理主面板
**文件**: `/home/jian/code/Task_feishu/frontend/src/components/DispatchManagementPanel.js`

**功能**:
- 右侧滑出式全屏面板
- 状态tabs筛选(全部/待审批/已通过/已完成/已关闭)
- 搜索功能(按任务名称/客户/工程师)
- 工单列表展示(使用DispatchOperationCard)
- 刷新按钮
- 数据从localStorage读取(模拟数据源)

**Props**:
```javascript
{
  isOpen: PropTypes.bool.isRequired,           // 是否显示
  onClose: PropTypes.func.isRequired,          // 关闭回调
}
```

**数据存储**:
- localStorage key: `created_dispatches`
- 格式: `Array<dispatch对象>`
- 注意: 目前使用本地存储,未来可替换为真实API

**使用示例**:
```javascript
import DispatchManagementPanel from './components/DispatchManagementPanel';

function App() {
  const [showPanel, setShowPanel] = useState(false);

  return (
    <>
      <button onClick={() => setShowPanel(true)}>
        打开工单管理
      </button>

      <DispatchManagementPanel
        isOpen={showPanel}
        onClose={() => setShowPanel(false)}
      />
    </>
  );
}
```

---

## 集成到主应用

### 步骤1: 在App.js中添加入口按钮

```javascript
// frontend/src/App.js
import { useState } from 'react';
import DispatchManagementPanel from './components/DispatchManagementPanel';

function App() {
  const [showManagementPanel, setShowManagementPanel] = useState(false);

  return (
    <div className="App">
      {/* 现有代码... */}

      {/* 工单管理按钮(放在Header或适当位置) */}
      <button
        onClick={() => setShowManagementPanel(true)}
        className="fixed bottom-6 right-6 bg-blue-600 text-white px-4 py-2 rounded-full shadow-lg hover:bg-blue-700 transition"
      >
        <i className="fas fa-tasks mr-2"></i>
        工单管理
      </button>

      {/* 工单管理面板 */}
      <DispatchManagementPanel
        isOpen={showManagementPanel}
        onClose={() => setShowManagementPanel(false)}
      />
    </div>
  );
}
```

### 步骤2: 保存新建派工到localStorage

在`CreateDispatchModal.js`的成功回调中添加保存逻辑:

```javascript
// frontend/src/components/CreateDispatchModal.js

const handleSubmit = async (event) => {
  // ... 现有代码 ...

  try {
    setIsSubmitting(true);
    const result = await createDispatch(approvalType, payload);
    setSubmissionResult(result);

    // 保存到localStorage
    if (result.success && result.instance_code) {
      const newDispatch = {
        instance_code: result.instance_code,
        task_name: payload.work_content,
        assignee: payload.assignee,
        customer_name: payload.customer_name,
        start_date: payload.start_date,
        end_date: payload.end_date,
        priority: payload.priority,
        status: 'pending',
        approval_url: result.approval_url,
      };

      const existing = JSON.parse(localStorage.getItem('created_dispatches') || '[]');
      existing.unshift(newDispatch); // 添加到列表开头
      localStorage.setItem('created_dispatches', JSON.stringify(existing.slice(0, 100))); // 只保留最近100条
    }

    if (typeof onSuccess === 'function') {
      onSuccess(result);
    }
  } catch (error) {
    // ... 错误处理 ...
  }
};
```

---

## 样式依赖

所有组件使用Tailwind CSS和Font Awesome图标,确保以下依赖已配置:

1. **Tailwind CSS**: 项目已配置
2. **Font Awesome**: 确保在`public/index.html`中引入:
   ```html
   <link
     rel="stylesheet"
     href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
   />
   ```

---

## API依赖

组件调用的API方法(已在`frontend/src/utils/api.js`中定义):

- `updateDispatch(instanceCode, formData)` - 修改工单
- `transferDispatch(instanceCode, newAssignee, reason)` - 转交工单
- `completeDispatch(instanceCode, completionNote)` - 完成工单
- `closeDispatch(instanceCode, reason)` - 关闭工单
- `fetchApprovalDetail(instanceCode)` - 查询审批详情

---

## 未来改进建议

1. **后端列表API**: 目前使用localStorage,建议添加`GET /api/approvals`端点返回工单列表
2. **实时状态同步**: 当前需手动刷新,可添加轮询或WebSocket实时更新
3. **分页**: 工单数量多时添加分页功能
4. **高级筛选**: 添加日期范围、优先级等更多筛选维度
5. **批量操作**: 支持批量转交、批量关闭等操作
6. **详情展示优化**: 当前审批详情以JSON显示,可优化为格式化的时间线视图

---

## 故障排查

### 问题1: 工单列表为空
**原因**: localStorage中没有数据
**解决**:
1. 创建新派工后检查localStorage是否保存
2. 使用浏览器开发者工具查看`localStorage.created_dispatches`
3. 手动添加测试数据:
   ```javascript
   localStorage.setItem('created_dispatches', JSON.stringify([
     {
       instance_code: 'test-001',
       task_name: '测试任务',
       assignee: '张三',
       customer_name: '测试客户',
       start_date: '2025-10-22',
       end_date: '2025-10-23',
       priority: '紧急',
       status: 'pending',
     }
   ]));
   ```

### 问题2: EngineerSelector无法加载工程师列表
**原因**: API端点`/api/engineers`未响应或环境变量未配置
**解决**:
1. 检查后端是否启动
2. 验证`REACT_APP_BACKEND_BASE_URL`环境变量
3. 查看浏览器控制台Network标签

### 问题3: 操作按钮点击无效
**原因**: API Key配置错误或后端返回错误
**解决**:
1. 检查`frontend/src/utils/api.js`中的`API_KEY`常量
2. 查看浏览器控制台Console标签的错误信息
3. 验证后端日志

---

## 组件依赖关系图

```
DispatchManagementPanel (主面板)
  └── DispatchOperationCard (工单卡片)
        ├── UpdateDispatchModal (修改弹窗)
        │     └── EngineerSelector (工程师选择器)
        ├── TransferDispatchModal (转交弹窗)
        │     └── EngineerSelector
        └── ConfirmDialog (确认对话框) × 3
              - 完成确认
              - 关闭确认
              - 详情展示
```

---

## 测试建议

### 单元测试
```bash
cd frontend
npm test -- ConfirmDialog.test.js
npm test -- UpdateDispatchModal.test.js
npm test -- TransferDispatchModal.test.js
npm test -- DispatchOperationCard.test.js
npm test -- DispatchManagementPanel.test.js
```

### 手动测试清单
- [ ] 打开工单管理面板
- [ ] 切换不同状态tabs
- [ ] 搜索功能测试
- [ ] 修改工单并验证
- [ ] 转交工单并验证
- [ ] 完成工单并验证
- [ ] 关闭工单并验证
- [ ] 查看审批详情
- [ ] 点击飞书审批链接
- [ ] 刷新按钮功能

---

**文档维护**: 如有更新,请同步修改本文档
**联系人**: 开发团队
**最后更新**: 2025-10-22
