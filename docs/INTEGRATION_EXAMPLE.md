# 工单管理UI集成示例

**创建时间**: 2025-10-22

## 快速集成步骤

### 1. 在App.js中添加工单管理面板

```javascript
// frontend/src/App.js
import React, { useState } from 'react';
import DispatchManagementPanel from './components/DispatchManagementPanel';
import CreateDispatchModal from './components/CreateDispatchModal';
// ... 其他导入

function App() {
  const [showManagementPanel, setShowManagementPanel] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // 创建派工成功回调
  const handleCreateSuccess = (result) => {
    console.log('派工创建成功:', result);

    // 保存到localStorage供工单管理面板使用
    if (result.success && result.instance_code) {
      const newDispatch = {
        instance_code: result.instance_code,
        task_name: result.task_name || '未命名任务',
        assignee: result.assignee,
        customer_name: result.customer_name,
        start_date: result.start_date,
        end_date: result.end_date,
        priority: result.priority,
        status: 'pending', // 初始状态
        approval_url: result.approval_url,
      };

      // 从localStorage读取现有数据
      const existing = JSON.parse(
        localStorage.getItem('created_dispatches') || '[]'
      );

      // 添加到列表开头
      existing.unshift(newDispatch);

      // 只保留最近100条
      localStorage.setItem(
        'created_dispatches',
        JSON.stringify(existing.slice(0, 100))
      );
    }

    // 可选: 自动打开工单管理面板
    // setShowManagementPanel(true);
  };

  return (
    <div className="App">
      {/* 现有的Header和其他内容 */}

      {/* 浮动按钮组 */}
      <div className="fixed bottom-6 right-6 flex flex-col gap-3">
        {/* 新建派工按钮 */}
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-green-600 text-white px-4 py-3 rounded-full shadow-lg hover:bg-green-700 transition flex items-center gap-2"
          title="新建派工"
        >
          <i className="fas fa-plus"></i>
          <span>新建派工</span>
        </button>

        {/* 工单管理按钮 */}
        <button
          onClick={() => setShowManagementPanel(true)}
          className="bg-blue-600 text-white px-4 py-3 rounded-full shadow-lg hover:bg-blue-700 transition flex items-center gap-2"
          title="工单管理"
        >
          <i className="fas fa-tasks"></i>
          <span>工单管理</span>
        </button>
      </div>

      {/* 新建派工弹窗 */}
      <CreateDispatchModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={handleCreateSuccess}
      />

      {/* 工单管理面板 */}
      <DispatchManagementPanel
        isOpen={showManagementPanel}
        onClose={() => setShowManagementPanel(false)}
      />
    </div>
  );
}

export default App;
```

---

### 2. 修改CreateDispatchModal的onSuccess处理

如果你想在`CreateDispatchModal.js`内部处理localStorage保存,可以这样修改:

```javascript
// frontend/src/components/CreateDispatchModal.js

const handleSubmit = async (event) => {
  event.preventDefault();
  setSubmitError(null);
  setGeneralError(null);

  const isValid = validate();
  if (!isValid) {
    return;
  }

  const payload = buildPayload();

  try {
    setIsSubmitting(true);
    const result = await createDispatch(approvalType, payload);
    setSubmissionResult(result);

    // 🆕 保存到localStorage
    if (result.success && result.instance_code) {
      saveDispatchToLocalStorage({
        instance_code: result.instance_code,
        task_name: payload.work_content || payload.customer_name,
        assignee: payload.assignee,
        customer_name: payload.customer_name,
        start_date: payload.start_date,
        end_date: payload.end_date,
        priority: payload.priority || '普通',
        status: 'pending',
        approval_url: result.approval_url,
      });
    }

    if (typeof onSuccess === 'function') {
      onSuccess(result);
    }
  } catch (error) {
    setSubmitError(error.message || '提交失败,请稍后重试');
  } finally {
    setIsSubmitting(false);
  }
};

// 🆕 工具函数: 保存到localStorage
function saveDispatchToLocalStorage(dispatch) {
  try {
    const existing = JSON.parse(
      localStorage.getItem('created_dispatches') || '[]'
    );
    existing.unshift(dispatch);
    localStorage.setItem(
      'created_dispatches',
      JSON.stringify(existing.slice(0, 100))
    );
  } catch (error) {
    console.error('保存工单到localStorage失败:', error);
  }
}
```

---

### 3. 在Header中添加工单管理入口

```javascript
// frontend/src/components/Header.js (示例)
import React from 'react';

export default function Header({ onOpenManagement }) {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">飞书派工系统</h1>

        <div className="flex items-center gap-3">
          {/* 工单管理按钮 */}
          <button
            onClick={onOpenManagement}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition"
          >
            <i className="fas fa-tasks mr-2"></i>
            工单管理
          </button>

          {/* 其他按钮... */}
        </div>
      </div>
    </header>
  );
}
```

---

### 4. 添加测试数据(开发阶段)

在浏览器控制台执行以下代码添加测试数据:

```javascript
// 添加测试工单数据
const testDispatches = [
  {
    instance_code: 'TEST-001',
    task_name: '网络故障排查',
    assignee: '张三',
    customer_name: '阿里巴巴',
    start_date: '2025-10-22',
    end_date: '2025-10-23',
    priority: '紧急',
    status: 'pending',
    approval_url: 'https://feishu.cn/approval/xxx',
  },
  {
    instance_code: 'TEST-002',
    task_name: '服务器维护',
    assignee: '李四',
    customer_name: '腾讯',
    start_date: '2025-10-23',
    end_date: '2025-10-24',
    priority: '普通',
    status: 'approved',
    approval_url: 'https://feishu.cn/approval/yyy',
  },
  {
    instance_code: 'TEST-003',
    task_name: '数据库优化',
    assignee: '王五',
    customer_name: '字节跳动',
    start_date: '2025-10-24',
    end_date: '2025-10-25',
    priority: '重要',
    status: 'completed',
    approval_url: 'https://feishu.cn/approval/zzz',
  },
];

localStorage.setItem('created_dispatches', JSON.stringify(testDispatches));
console.log('✅ 测试数据已添加到localStorage');
```

---

### 5. 环境检查清单

集成前请确保:

- [x] 后端API服务运行正常(`http://localhost:8000`)
- [x] `REACT_APP_BACKEND_BASE_URL`环境变量已配置
- [x] API_KEY在`frontend/src/utils/api.js`中正确配置
- [x] Font Awesome图标已引入(`public/index.html`)
- [x] Tailwind CSS已配置
- [x] `useEngineers` hook存在于`frontend/src/hooks/useEngineers.js`

---

### 6. 测试流程

#### 6.1 基础功能测试

1. **打开工单管理面板**
   - 点击浮动按钮或Header中的"工单管理"
   - 验证右侧滑出面板正常显示

2. **查看工单列表**
   - 验证测试数据正常显示
   - 检查工单信息(任务名、客户、工程师、时间、状态)

3. **状态筛选**
   - 点击不同tab(全部/待审批/已通过/已完成/已关闭)
   - 验证筛选结果正确

4. **搜索功能**
   - 输入任务名称搜索
   - 输入客户名称搜索
   - 输入工程师名称搜索
   - 验证搜索结果正确

5. **刷新功能**
   - 点击刷新按钮
   - 验证数据重新加载

#### 6.2 操作功能测试

1. **修改工单**
   - 点击工单卡片的"修改"按钮
   - 修改工程师、优先级、时间
   - 提交并验证成功

2. **转交工单**
   - 点击"转交"按钮
   - 选择新工程师
   - 填写原因(可选)
   - 提交并验证

3. **完成工单**
   - 点击"完成"按钮
   - 填写完成备注(可选)
   - 确认并验证

4. **关闭工单**
   - 点击"关闭"按钮
   - 填写关闭原因(可选)
   - 确认并验证

5. **查看详情**
   - 点击"查看详情"按钮
   - 验证审批详情显示

6. **飞书审批链接**
   - 点击"飞书审批"按钮
   - 验证在新标签页打开

---

### 7. 常见问题解决

#### 问题1: 工单管理面板打开后无法关闭
**解决**: 检查遮罩层点击事件是否正确绑定

#### 问题2: 工单列表为空
**解决**:
1. 检查localStorage是否有数据
2. 添加测试数据(见步骤4)
3. 创建新派工后检查是否保存到localStorage

#### 问题3: 操作按钮点击后无响应
**解决**:
1. 打开浏览器控制台查看错误
2. 检查API Key配置
3. 验证后端服务是否运行

#### 问题4: EngineerSelector无法加载工程师
**解决**:
1. 检查`/api/engineers`端点是否正常
2. 验证`useEngineers` hook实现
3. 检查CORS配置

---

### 8. 性能优化建议

1. **懒加载**: 使用React.lazy()延迟加载DispatchManagementPanel
   ```javascript
   const DispatchManagementPanel = React.lazy(() =>
     import('./components/DispatchManagementPanel')
   );
   ```

2. **缓存**: 使用React Query或SWR缓存API请求
   ```javascript
   import { useQuery } from 'react-query';

   const { data, refetch } = useQuery(
     'dispatches',
     fetchDispatchList,
     { staleTime: 5 * 60 * 1000 } // 5分钟缓存
   );
   ```

3. **虚拟滚动**: 工单数量多时使用react-window
   ```bash
   npm install react-window
   ```

---

### 9. 下一步计划

- [ ] 添加后端列表API(`GET /api/approvals`)
- [ ] 实现实时状态同步(WebSocket或轮询)
- [ ] 添加工单详情页面
- [ ] 支持批量操作
- [ ] 添加导出功能(Excel/CSV)
- [ ] 移动端适配优化
- [ ] 添加通知提醒功能

---

**集成完成检查**:
- [ ] 浮动按钮显示正常
- [ ] 工单管理面板可正常打开/关闭
- [ ] 工单列表正常显示
- [ ] 状态筛选功能正常
- [ ] 搜索功能正常
- [ ] 修改操作正常
- [ ] 转交操作正常
- [ ] 完成操作正常
- [ ] 关闭操作正常
- [ ] 查看详情正常
- [ ] 飞书审批链接正常

**文档维护**: 如有更新,请同步修改本文档
**联系人**: 开发团队
**最后更新**: 2025-10-22
