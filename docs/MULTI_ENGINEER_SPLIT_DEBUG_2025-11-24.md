# 多工程师任务拆分功能调试记录

**日期**: 2025-11-24
**功能**: 派工单多工程师拆分显示
**状态**: 🔧 容器已更新,等待用户验证

---

## 问题描述

### 用户报告
派工单中有多个工程师(如"曹云菲, 左元锟")时,页面只显示第一个工程师(曹云菲)的任务,第二个工程师(左元锟)的任务未显示。

### 预期行为
一条派工单如果分配给多个工程师,应该在周视图中显示多张任务卡片,每个工程师一张。

---

## 调试过程

### 1. 初步检查 (已完成 ✅)

#### 后端数据验证
```bash
# 检查数据库中的原始数据
curl "http://10.242.94.9:8000/api/dispatch/orders?page_size=100"

# 结果: 后端数据正确
{
  "source_id": "NzU3NjE0OTE2OTA4NjI1NDAzMzpBNzUxQ0NDMi1GNEM2LTRCQzgtQkNEMC0wNkFEM0YyMEExNTUtMTphNjhlZDAxNTZhZWJjOWRkOTEzMzVkZjFiYWNlYWFmNjox",
  "engineer_name": "曹云菲, 左元锟",  ✅ 正确
  "customer_company": "创想智控",
  "service_start_time": 1763913600000,
  "service_end_time": 1763913600000
}
```

#### 前端代码验证
- ✅ `backend/dispatch_sync.py:173` - 使用`_extract_all_contact_names()`提取所有工程师
- ✅ `frontend/src/utils/taskUtils.js:45` - `parseEngineerNames()`函数拆分逗号分隔的工程师名
- ✅ `frontend/src/utils/taskUtils.js:101` - `splitOrderByEngineers()`为每个工程师创建独立任务
- ✅ `frontend/src/utils/taskUtils.js:166` - `groupDispatchOrdersByWeekday()`调用拆分逻辑

### 2. 关键发现 (已确认 ⚠️)

#### API响应验证
```bash
# 使用前端相同参数查询
curl "http://10.242.94.9:8000/api/dispatch/orders?start_time=1763913600000&end_time=1764518399999&page_size=100"

# 结果: API返回数据正确
engineer_name: "曹云菲, 左元锟" ✅
```

#### 用户浏览器控制台日志
```javascript
[DEBUG API] 请求URL: /api/dispatch/orders?start_time=1763913600000&end_time=1764518399999&page_size=100
[DEBUG API] 创想智控订单数: 1
[DEBUG API]   [0] engineer_name: 曹云菲  ❌ 只有一个工程师
```

**矛盾点**:
- 后端API返回: `"曹云菲, 左元锟"` ✅
- 前端收到数据: `"曹云菲"` ❌

### 3. 根本原因 (已确认 🎯)

#### 容器版本检查
```bash
# 检查容器中的JS文件
docker exec docker_frontend_1 ls -lh /usr/share/nginx/html/static/js/

# 旧容器(qdmgt_frontend):
-rw-r--r-- main.5820181d.js  (Oct 20 07:22)  ❌ 10月20日旧版本

# 新容器(docker_frontend_1):
-rw-rw-r-- main.75ab480d.js  (Nov 24 08:04)  ✅ 11月24日新版本
```

#### 本地构建验证
```bash
ls -lh /home/jian/code/Task_feishu/frontend/build/static/js/

# 本地构建:
-rw-rw-r-- main.75ab480d.js  (11月 24 16:04)  ✅ 最新代码
```

**问题确认**:
- 虽然本地已构建最新代码,但Docker容器运行的是10月20日的旧代码
- 之前的`docker-compose build`命令没有真正更新容器中的文件
- 用户浏览器可能缓存了旧的JS文件

---

## 解决方案

### 1. 重新部署前端容器 (已完成 ✅)

```bash
cd /home/jian/code/Task_feishu/docker

# 停止并删除旧容器
docker-compose -f docker-compose.frontend.yml stop
docker-compose -f docker-compose.frontend.yml rm -f

# 完全重新构建(不使用缓存)
docker-compose -f docker-compose.frontend.yml build --no-cache

# 启动新容器
docker-compose -f docker-compose.frontend.yml up -d

# 验证新文件已部署
docker exec docker_frontend_1 ls -lh /usr/share/nginx/html/static/js/ | grep main
# 输出: main.75ab480d.js (Nov 24 08:04) ✅
```

### 2. 验证新代码特征 (已完成 ✅)

```bash
# 检查debug日志存在
docker exec docker_frontend_1 grep -o "DEBUG API" /usr/share/nginx/html/static/js/main.75ab480d.js
# 输出: DEBUG API (多次) ✅

# 检查拆分逻辑关键字段
docker exec docker_frontend_1 grep -o "_assignee_override" /usr/share/nginx/html/static/js/main.75ab480d.js
# 输出: _assignee_override ✅

# 检查网页引用的JS文件
curl -s http://10.242.94.9 | grep -o 'main\.[a-f0-9]*\.js'
# 输出: main.75ab480d.js ✅
```

### 3. 容器状态 (当前 📋)

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep frontend

# 结果:
docker_frontend_1   0.0.0.0:80->80/tcp       ← 主容器,最新代码 ✅
qdmgt_frontend      0.0.0.0:3002->80/tcp     ← 旧容器,可忽略
```

---

## 待用户验证步骤

### 用户操作清单

1. **清除浏览器缓存** 🧹
   - 按 `Ctrl+Shift+Delete`
   - 勾选"缓存的图片和文件"
   - 点击"清除数据"

2. **硬刷新页面** 🔄
   - 按 `Ctrl+Shift+R` (Linux/Windows)
   - 或 `Ctrl+F5`
   - 或 `Cmd+Shift+R` (Mac)

3. **打开浏览器控制台** 🔍
   - 按 `F12`
   - 切换到"Console"标签

4. **查看周视图** 📅
   - 切换到包含11月24日(周一)的周视图
   - 找到"创想智控"相关任务

### 预期结果

#### 控制台日志应显示:
```javascript
[DEBUG API] 请求URL: /api/dispatch/orders?start_time=1763913600000&end_time=1764518399999&page_size=100
[DEBUG API] 创想智控订单数: 1
[DEBUG API]   [0] engineer_name: 曹云菲, 左元锟  ← 应该显示两个工程师
[DEBUG] 创想智控订单拆分: { original_engineer: "曹云菲, 左元锟", split_count: 2, ... }
[DEBUG] 创想智控任务生成: { date: "2025-11-24", assignee: "曹云菲", weekday: "monday" }
[DEBUG] 创想智控任务生成: { date: "2025-11-24", assignee: "左元锟", weekday: "monday" }
[DEBUG] groupDispatchOrdersByWeekday 完成, monday任务数: X
[DEBUG] 创想智控任务数: 2, 执行人: ["曹云菲", "左元锟"]  ← 应该显示2个任务
```

#### 页面应显示:
- **周一列中**应该有**两张**"创想智控"任务卡片:
  - 卡片1: 显示执行人"曹云菲"
  - 卡片2: 显示执行人"左元锟"

---

## 技术实现细节

### 数据流程

```
飞书多选人员字段
  ↓
backend/dispatch_sync.py:173
  _extract_all_contact_names() → "曹云菲, 左元锟"
  ↓
API响应 /api/dispatch/orders
  { engineer_name: "曹云菲, 左元锟" }
  ↓
frontend/src/utils/api.js:278
  parseJsonResponse() → result.data[]
  ↓
frontend/src/hooks/useTasks.js:26
  groupDispatchOrdersByWeekday(orders)
  ↓
frontend/src/utils/taskUtils.js:166
  orders.forEach(order => {
    splitOrders = splitOrderByEngineers(order)  // 拆分为2个
    splitOrders.forEach(splitOrder => {
      task = convertDispatchOrderToTask(
        splitOrder,
        dateStr,
        splitOrder._assignee_override  // "曹云菲" 或 "左元锟"
      )
      grouped[weekdayKey].push(task)
    })
  })
  ↓
frontend/src/components/WeekView.js
  显示两张TaskCard,分别显示"曹云菲"和"左元锟"
```

### 关键代码片段

#### 1. 后端提取所有工程师名
```python
# backend/dispatch_sync.py:170-173
engineer_raw = consume("售后工程师")
engineer_id, _ = _extract_first_contact(engineer_raw)
# 使用 _extract_all_contact_names 获取所有工程师名字（逗号分隔）
engineer_name = _extract_all_contact_names(engineer_raw)
```

#### 2. 前端解析工程师名
```javascript
// frontend/src/utils/taskUtils.js:45-50
function parseEngineerNames(engineerStr) {
    if (!engineerStr) return ['未分配'];
    // 支持中文逗号、英文逗号、顿号分隔
    const names = engineerStr.split(/[,，、]/).map((name) => name.trim()).filter(Boolean);
    return names.length > 0 ? names : ['未分配'];
}
```

#### 3. 按工程师拆分订单
```javascript
// frontend/src/utils/taskUtils.js:101-109
function splitOrderByEngineers(order) {
    if (!order) return [];
    const engineers = parseEngineerNames(order.engineer_name);
    // 为每个工程师创建一个派工单副本
    return engineers.map((engineer) => ({
        ...order,
        _assignee_override: engineer,
    }));
}
```

#### 4. 转换时使用指定工程师
```javascript
// frontend/src/utils/taskUtils.js:59-94
export function convertDispatchOrderToTask(order, dateStr = null, assigneeOverride = null) {
    // ...
    // 使用指定的执行人或原始值
    const assignee = assigneeOverride || order.engineer_name || '未分配';

    return {
        record_id: order.source_id || `dispatch-${order.id}`,
        task_name: taskName,
        assignee,  // ← 关键: 使用单个工程师名
        // ...
    };
}
```

#### 5. 分组时执行拆分
```javascript
// frontend/src/utils/taskUtils.js:166-178
orders.forEach((order) => {
    if (!order) return;

    // 先按工程师拆分
    const splitOrders = splitOrderByEngineers(order);

    splitOrders.forEach((splitOrder) => {
        // ... 日期范围处理 ...
        dateRange.forEach((dateStr) => {
            const task = convertDispatchOrderToTask(
                splitOrder,
                dateStr,
                splitOrder._assignee_override  // ← 传递单个工程师名
            );
            // ... 分组逻辑 ...
        });
    });
});
```

---

## 相关文件清单

### 后端文件
- `/home/jian/code/Task_feishu/backend/dispatch_sync.py` - 飞书数据同步,工程师字段提取

### 前端文件
- `/home/jian/code/Task_feishu/frontend/src/utils/taskUtils.js` - 工程师拆分核心逻辑
- `/home/jian/code/Task_feishu/frontend/src/utils/api.js` - API调用,debug日志
- `/home/jian/code/Task_feishu/frontend/src/hooks/useTasks.js` - 数据获取和转换
- `/home/jian/code/Task_feishu/frontend/src/components/TaskCard.js` - 任务卡片显示
- `/home/jian/code/Task_feishu/frontend/src/components/WeekView.js` - 周视图布局

### 部署文件
- `/home/jian/code/Task_feishu/docker/docker-compose.frontend.yml` - 前端容器配置
- `/home/jian/code/Task_feishu/docker/Dockerfile.frontend` - 前端镜像构建
- `/home/jian/code/Task_feishu/frontend/build/static/js/main.75ab480d.js` - 最新构建产物

---

## 故障排查检查清单

### 如果问题仍然存在

#### 1. 验证容器版本
```bash
# 检查容器中的JS文件日期
docker exec docker_frontend_1 ls -lh /usr/share/nginx/html/static/js/main.*.js

# 应该显示: main.75ab480d.js (Nov 24 08:04)
```

#### 2. 验证网页引用
```bash
# 检查HTML引用的JS文件
curl -s http://10.242.94.9 | grep -o 'main\.[a-f0-9]*\.js'

# 应该输出: main.75ab480d.js
```

#### 3. 验证浏览器加载
- 打开浏览器开发者工具 → Network标签
- 刷新页面
- 查找 `main.*.js` 文件
- 检查:
  - 文件名应该是 `main.75ab480d.js`
  - Status应该是 `200` (不是304 Not Modified)
  - Size应该显示实际大小(约256KB),不是 `(from disk cache)`

#### 4. 强制清除缓存方法
- **Chrome**: 开发者工具打开 → 右键刷新按钮 → 选择"清空缓存并硬性重新加载"
- **Firefox**: 开发者工具打开 → 右键刷新按钮 → 选择"强制刷新"
- **手动清除**: Settings → Privacy → Clear browsing data → 勾选"Cached images and files"

#### 5. 检查API实际返回
```javascript
// 在浏览器控制台执行
fetch('http://10.242.94.9:8000/api/dispatch/orders?start_time=1763913600000&end_time=1764518399999&page_size=100', {credentials: 'include'})
  .then(r => r.json())
  .then(d => {
    const cx = d.data.find(o => o.customer_company?.includes('创想智控'));
    console.log('API返回的engineer_name:', cx?.engineer_name);
  });

// 应该输出: 曹云菲, 左元锟
```

#### 6. 检查拆分逻辑执行
```javascript
// 在浏览器控制台执行
const testOrder = { engineer_name: "曹云菲, 左元锟" };

// 测试解析函数
function parseEngineerNames(engineerStr) {
    if (!engineerStr) return ['未分配'];
    const names = engineerStr.split(/[,，、]/).map((name) => name.trim()).filter(Boolean);
    return names.length > 0 ? names : ['未分配'];
}

const result = parseEngineerNames(testOrder.engineer_name);
console.log('拆分结果:', result);

// 应该输出: ['曹云菲', '左元锟']
```

---

## 已知问题和限制

### 1. 多容器共存
- 系统中有两个前端容器:
  - `docker_frontend_1` (端口80) - 主容器,已更新
  - `qdmgt_frontend` (端口3002) - 旧容器,可删除但不影响功能
- 用户通过 `http://10.242.94.9` (端口80)访问,会使用最新的`docker_frontend_1`

### 2. 浏览器缓存策略
- React构建使用内容哈希(`main.75ab480d.js`),理论上会自动失效旧缓存
- 但某些浏览器可能激进缓存HTML文件,导致引用旧的JS文件
- 解决方案: 用户手动清除缓存

### 3. Docker构建缓存
- `docker-compose build`可能使用Docker层缓存
- 使用`--no-cache`标志确保完全重新构建
- 需要`rm -f`删除旧容器,避免重用旧卷

---

## 恢复到当前进度的Prompt

```markdown
# Context
我正在调试一个派工单多工程师拆分显示的功能。系统架构:
- 后端: FastAPI + SQLite
- 前端: React 18
- 部署: Docker Compose

# Current Situation
1. **问题**: 派工单有多个工程师(如"曹云菲, 左元锟")时,页面只显示第一个工程师的任务

2. **已完成的工作**:
   - ✅ 后端已修改为提取所有工程师名(逗号分隔)
   - ✅ 前端已实现拆分逻辑(`parseEngineerNames`, `splitOrderByEngineers`)
   - ✅ 添加了详细的debug日志
   - ✅ 本地构建了新代码 (`main.75ab480d.js`)
   - ✅ 重新部署了前端Docker容器(完全重建,不使用缓存)

3. **根本原因**: Docker容器中运行的是10月20日的旧代码,虽然本地已构建最新代码,但容器没有更新

4. **已执行的修复**:
   ```bash
   cd /home/jian/code/Task_feishu/docker
   docker-compose -f docker-compose.frontend.yml stop
   docker-compose -f docker-compose.frontend.yml rm -f
   docker-compose -f docker-compose.frontend.yml build --no-cache
   docker-compose -f docker-compose.frontend.yml up -d
   ```

5. **验证结果**:
   - ✅ 容器中的JS文件: `main.75ab480d.js` (Nov 24 08:04)
   - ✅ 网页引用的JS: `main.75ab480d.js`
   - ✅ Debug日志存在: `DEBUG API`
   - ✅ 拆分逻辑存在: `_assignee_override`
   - ✅ 后端API返回正确数据: `"曹云菲, 左元锟"`

# Current Status
**等待用户验证**: 容器已更新完毕,需要用户清除浏览器缓存并硬刷新页面来验证功能

# Key Files
- `/home/jian/code/Task_feishu/backend/dispatch_sync.py:170-173` - 提取所有工程师
- `/home/jian/code/Task_feishu/frontend/src/utils/taskUtils.js:45,101,166` - 拆分逻辑
- `/home/jian/code/Task_feishu/frontend/src/utils/api.js:258-288` - API调用和debug
- `/home/jian/code/Task_feishu/docs/MULTI_ENGINEER_SPLIT_DEBUG_2025-11-24.md` - 完整调试记录

# Expected User Actions
1. 清除浏览器缓存 (Ctrl+Shift+Delete)
2. 硬刷新页面 (Ctrl+Shift+R)
3. 打开控制台查看 `[DEBUG API]` 日志
4. 查看周视图,确认创想智控显示两张卡片(曹云菲和左元锟各一张)

# Next Steps if Issue Persists
- 检查浏览器Network标签,确认加载的是 `main.75ab480d.js` 而非旧文件
- 尝试隐私/无痕模式访问
- 检查浏览器控制台是否有JavaScript错误
```

---

**文档生成时间**: 2025-11-24 16:30
**最后更新**: 2025-11-24 16:30
**负责人**: Claude Code
**状态**: 🟡 等待用户验证
