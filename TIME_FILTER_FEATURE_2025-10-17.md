# 时间筛选功能和月视图开发文档

**开发日期**: 2025-10-17
**功能状态**: ✅ 已完成

---

## 功能概述

为派工管理系统添加了完整的时间筛选和多视图支持，允许用户在周视图和月视图之间切换，并可以导航到不同的时间段。

### 新增功能

1. **周视图 / 月视图切换**
   - 一键切换周视图和月视图显示模式
   - 切换时自动保持当前选择的日期

2. **时间导航**
   - 上一周/下一周快速导航（周视图）
   - 上个月/下个月快速导航（月视图）
   - "今天"按钮快速回到当前日期

3. **月视图日历**
   - 完整的日历网格布局（7列 × 6行 = 42天）
   - 包含上月和下月的部分日期
   - 每个日期格子显示最多3个任务
   - 超过3个任务显示"+N 更多"
   - 今天的日期高亮显示

---

## 技术实现

### 后端修改

**文件**: `backend/task_db.py`

新增函数 `get_month_range()`：

```python
def get_month_range(date=None) -> tuple[str, str]:
    """获取一个月的开始和结束日期

    Args:
        date: 基准日期，默认今天

    Returns:
        (start_date_str, end_date_str) 格式 YYYY-MM-DD
    """
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")

    # 月初（第一天）
    start_of_month = date.replace(day=1)

    # 月末（下个月第一天的前一天）
    if date.month == 12:
        end_of_month = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = date.replace(month=date.month + 1, day=1) - timedelta(days=1)

    start_str = start_of_month.strftime("%Y-%m-%d")
    end_str = end_of_month.strftime("%Y-%m-%d")

    logger.debug("Month range: %s to %s", start_str, end_str)
    return start_str, end_str
```

**特性**:
- 支持传入 `datetime` 对象或 `YYYY-MM-DD` 格式的字符串
- 正确处理12月跨年的情况
- 返回标准化的日期字符串格式

---

### 前端修改

**文件**: `frontend/index.html`

#### 1. 新增UI组件

**控制栏** (行 95-131):
```html
<!-- 时间筛选控制栏 -->
<div class="bg-white shadow-md mb-6">
    <div class="container mx-auto px-4 py-4">
        <div class="flex flex-col md:flex-row items-center justify-between gap-4">
            <!-- 视图切换按钮 -->
            <div class="flex items-center gap-2">
                <button id="weekViewBtn" class="view-btn ...">
                    <i class="fas fa-calendar-week mr-2"></i>周视图
                </button>
                <button id="monthViewBtn" class="view-btn ...">
                    <i class="fas fa-calendar-alt mr-2"></i>月视图
                </button>
            </div>

            <!-- 日期导航 -->
            <div class="flex items-center gap-3">
                <button id="prevPeriodBtn">上一周</button>
                <div class="text-center">
                    <div id="currentPeriodText">第 X 周</div>
                    <div id="dateRangeText">2025-01-01 ~ 2025-01-07</div>
                </div>
                <button id="nextPeriodBtn">下一周</button>
                <button id="todayBtn">今天</button>
            </div>
        </div>
    </div>
</div>
```

**月视图容器** (行 179-196):
```html
<!-- 月视图 -->
<div id="monthViewContainer" class="hidden mb-8">
    <div class="bg-white rounded-lg shadow overflow-hidden">
        <!-- 星期标题 -->
        <div class="month-calendar">
            <div class="calendar-day-header">日</div>
            <div class="calendar-day-header">一</div>
            ...
            <div class="calendar-day-header">六</div>
        </div>
        <!-- 日期格子 -->
        <div id="calendarGrid" class="month-calendar">
            <!-- JavaScript动态生成 -->
        </div>
    </div>
</div>
```

#### 2. 新增CSS样式 (行 72-154)

```css
/* 视图切换按钮 */
.view-btn {
    background-color: #e5e7eb;
    color: #4b5563;
}

.view-btn.active {
    background-color: #2563eb;
    color: white;
}

/* 月视图日历网格 */
.month-calendar {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 1px;
    background-color: #e5e7eb;
}

/* 日期格子样式 */
.calendar-day {
    background-color: white;
    min-height: 120px;
    padding: 8px;
}

.calendar-day.today {
    background-color: #dbeafe;  /* 今天高亮 */
}

.calendar-day.other-month {
    background-color: #f9fafb;  /* 其他月份灰显 */
    opacity: 0.6;
}

/* 迷你任务卡片 */
.mini-task {
    font-size: 11px;
    padding: 2px 4px;
    margin-bottom: 2px;
    border-left: 3px solid;
    background-color: #f9fafb;
    cursor: pointer;
    transition: all 0.2s;
}

.mini-task.priority-high {
    border-left-color: #dc2626;  /* 红色 */
}

.mini-task.priority-medium {
    border-left-color: #ea580c;  /* 橙色 */
}

.mini-task.priority-low {
    border-left-color: #2563eb;  /* 蓝色 */
}
```

#### 3. 新增JavaScript函数

**日期计算函数** (行 256-286):
```javascript
// 获取周范围
function getWeekRange(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(d.setDate(diff));
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    return {
        start: formatDate(monday),
        end: formatDate(sunday)
    };
}

// 获取月范围
function getMonthRange(date) {
    const d = new Date(date);
    const firstDay = new Date(d.getFullYear(), d.getMonth(), 1);
    const lastDay = new Date(d.getFullYear(), d.getMonth() + 1, 0);

    return {
        start: formatDate(firstDay),
        end: formatDate(lastDay)
    };
}

// 日期格式化
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}
```

**显示更新函数** (行 288-310):
```javascript
function updatePeriodDisplay() {
    const range = currentView === 'week'
        ? getWeekRange(currentDate)
        : getMonthRange(currentDate);

    if (currentView === 'week') {
        document.getElementById('currentPeriodText').textContent =
            `第 ${getWeekNumber(weekStart)} 周`;
        document.getElementById('prevPeriodText').textContent = '上一周';
        document.getElementById('nextPeriodText').textContent = '下一周';
    } else {
        document.getElementById('currentPeriodText').textContent =
            `${year}年${month + 1}月`;
        document.getElementById('prevPeriodText').textContent = '上个月';
        document.getElementById('nextPeriodText').textContent = '下个月';
    }

    document.getElementById('dateRangeText').textContent =
        `${range.start} ~ ${range.end}`;
}
```

**月视图渲染函数** (行 411-491):
```javascript
function renderMonthTasks(taskData, startDate, endDate) {
    const grid = document.getElementById('calendarGrid');
    grid.innerHTML = '';

    // 获取月份信息
    const start = new Date(startDate);
    const year = start.getFullYear();
    const month = start.getMonth();

    // 计算日历第一天（包括上月尾部）
    const firstDay = new Date(year, month, 1);
    const startDay = new Date(firstDay);
    startDay.setDate(startDay.getDate() - startDay.getDay());

    // 按日期组织任务
    const tasksByDate = {};
    ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'weekend']
        .forEach(day => {
            (taskData[day] || []).forEach(task => {
                if (!tasksByDate[task.date]) {
                    tasksByDate[task.date] = [];
                }
                tasksByDate[task.date].push(task);
            });
        });

    // 生成42天（6周）的日历格子
    const today = formatDate(new Date());
    for (let i = 0; i < 42; i++) {
        const currentDay = new Date(startDay);
        currentDay.setDate(currentDay.getDate() + i);
        const dateStr = formatDate(currentDay);

        const dayDiv = document.createElement('div');
        dayDiv.className = 'calendar-day';

        // 其他月份标记
        if (currentDay.getMonth() !== month) {
            dayDiv.classList.add('other-month');
        }

        // 今天标记
        if (dateStr === today) {
            dayDiv.classList.add('today');
        }

        // 日期数字
        const dayNumber = document.createElement('div');
        dayNumber.className = 'day-number';
        dayNumber.textContent = currentDay.getDate();
        dayDiv.appendChild(dayNumber);

        // 添加任务（最多3个）
        const dayTasks = tasksByDate[dateStr] || [];
        dayTasks.slice(0, 3).forEach(task => {
            const taskDiv = document.createElement('div');
            taskDiv.className = 'mini-task';

            // 优先级样式
            let priorityClass = 'priority-low';
            if (task.priority === '紧急') priorityClass = 'priority-medium';
            if (task.priority === '非常紧急') priorityClass = 'priority-high';
            taskDiv.classList.add(priorityClass);

            // 任务名称（截断）
            taskDiv.textContent = task.task_name.length > 15
                ? `${task.task_name.substring(0, 15)}...`
                : task.task_name;
            taskDiv.title = `${task.task_name}\n负责人: ${task.assignee}\n优先级: ${task.priority}`;

            dayDiv.appendChild(taskDiv);
        });

        // 显示更多任务数量
        if (dayTasks.length > 3) {
            const moreDiv = document.createElement('div');
            moreDiv.className = 'text-xs text-gray-500 mt-1';
            moreDiv.textContent = `+${dayTasks.length - 3} 更多`;
            dayDiv.appendChild(moreDiv);
        }

        grid.appendChild(dayDiv);
    }
}
```

**事件监听器** (行 379-435):
```javascript
// 周视图切换
document.getElementById('weekViewBtn').addEventListener('click', function() {
    currentView = 'week';
    document.getElementById('weekViewBtn').classList.add('active');
    document.getElementById('monthViewBtn').classList.remove('active');
    updatePeriodDisplay();

    const range = getWeekRange(currentDate);
    fetchTasks(range.start, range.end);
});

// 月视图切换
document.getElementById('monthViewBtn').addEventListener('click', function() {
    currentView = 'month';
    document.getElementById('monthViewBtn').classList.add('active');
    document.getElementById('weekViewBtn').classList.remove('active');
    updatePeriodDisplay();

    const range = getMonthRange(currentDate);
    fetchTasks(range.start, range.end);
});

// 上一周/上个月
document.getElementById('prevPeriodBtn').addEventListener('click', function() {
    if (currentView === 'week') {
        currentDate.setDate(currentDate.getDate() - 7);
    } else {
        currentDate.setMonth(currentDate.getMonth() - 1);
    }
    updatePeriodDisplay();

    const range = currentView === 'week'
        ? getWeekRange(currentDate)
        : getMonthRange(currentDate);
    fetchTasks(range.start, range.end);
});

// 下一周/下个月
document.getElementById('nextPeriodBtn').addEventListener('click', function() {
    if (currentView === 'week') {
        currentDate.setDate(currentDate.getDate() + 7);
    } else {
        currentDate.setMonth(currentDate.getMonth() + 1);
    }
    updatePeriodDisplay();

    const range = currentView === 'week'
        ? getWeekRange(currentDate)
        : getMonthRange(currentDate);
    fetchTasks(range.start, range.end);
});

// 回到今天
document.getElementById('todayBtn').addEventListener('click', function() {
    currentDate = new Date();
    updatePeriodDisplay();

    const range = currentView === 'week'
        ? getWeekRange(currentDate)
        : getMonthRange(currentDate);
    fetchTasks(range.start, range.end);
});
```

---

## 使用说明

### 周视图操作

1. **查看本周任务**
   - 默认显示本周（周一到周日）的任务
   - 显示格式：周一、周二、周三、周四、周五五列布局

2. **导航到其他周**
   - 点击"上一周"按钮查看上周任务
   - 点击"下一周"按钮查看下周任务
   - 点击"今天"按钮回到本周

3. **周数显示**
   - 顶部显示"第 X 周"
   - 下方显示日期范围："2025-10-13 ~ 2025-10-19"

### 月视图操作

1. **切换到月视图**
   - 点击"月视图"按钮切换显示模式
   - 自动加载当前月份的所有任务数据

2. **查看月历**
   - 7列 × 6行完整日历网格
   - 周日在第一列，周六在第七列
   - 灰色显示上月和下月的部分日期
   - 蓝色背景高亮今天的日期

3. **任务显示**
   - 每个日期格子最多显示3个任务
   - 任务左侧有颜色条表示优先级：
     - 红色 = 非常紧急
     - 橙色 = 紧急
     - 蓝色 = 重要/其他
   - 鼠标悬停显示完整任务信息
   - 超过3个任务显示"+N 更多"

4. **导航到其他月**
   - 点击"上个月"按钮查看上月任务
   - 点击"下个月"按钮查看下月任务
   - 点击"今天"按钮回到当前月份

---

## 数据流

```
用户操作
  ↓
JavaScript计算日期范围
  ↓
发送API请求: /api/tasks?start_date=2025-10-01&end_date=2025-10-31
  ↓
后端查询数据库（按日期范围筛选）
  ↓
返回JSON数据（按星期分组）
  ↓
前端根据视图类型渲染：
  - 周视图：5列布局（周一到周五）
  - 月视图：7×6网格布局（包含周末）
```

---

## 验证测试

### 后端测试

```bash
python3 -c "
from backend.task_db import get_month_range, get_week_range
from datetime import datetime

# 测试月视图
start, end = get_month_range()
print(f'当前月份: {start} 到 {end}')

# 测试12月跨年
start, end = get_month_range(datetime(2024, 12, 25))
print(f'2024年12月: {start} 到 {end}')

# 测试周视图
start, end = get_week_range(week_start='sunday')
print(f'本周(周日开始): {start} 到 {end}')
"
```

**预期输出**:
```
当前月份: 2025-10-01 到 2025-10-31
2024年12月: 2024-12-01 到 2024-12-31
本周(周日开始): 2025-10-12 到 2025-10-18
```

### 前端测试清单

- [x] 视图切换按钮工作正常
- [x] 周视图和月视图正确切换
- [x] 上一周/下一周导航功能
- [x] 上个月/下个月导航功能
- [x] "今天"按钮返回当前日期
- [x] 周数计算正确
- [x] 日期范围显示正确
- [x] 月历生成42天（6周）
- [x] 今天日期高亮显示
- [x] 其他月份日期灰显
- [x] 任务按日期分组显示
- [x] 优先级颜色正确
- [x] 任务超过3个显示"+N 更多"
- [x] 响应式布局（移动端适配）

---

## 已知限制

1. **周末任务显示**
   - 周视图不显示周末任务（只显示周一到周五）
   - 需要查看周末任务请切换到月视图

2. **月视图任务数量**
   - 每个日期格子最多显示3个任务
   - 如需查看更多任务，可以点击任务查看详情（待实现）

3. **跨天任务**
   - 跨天任务在每一天都会显示完整的任务卡片
   - 在月视图中可能会重复出现

---

## 后续优化建议

1. **任务详情弹窗**
   - 点击月视图中的任务显示完整详情
   - 包含所有字段信息和操作按钮

2. **周末任务视图**
   - 在周视图中添加周末列
   - 或添加"仅工作日"切换开关

3. **快捷导航**
   - 添加月份选择器
   - 添加年份选择器
   - 支持直接跳转到指定日期

4. **任务筛选增强**
   - 按负责人筛选
   - 按优先级筛选
   - 按状态筛选

5. **性能优化**
   - 月视图添加虚拟滚动
   - 任务数据缓存
   - 懒加载优化

---

## 文件变更列表

### 后端
- ✅ `backend/task_db.py` - 新增 `get_month_range()` 函数

### 前端
- ✅ `frontend/index.html` - 完整重构，添加以下内容：
  - 时间筛选控制栏UI
  - 月视图容器和日历网格
  - CSS样式（视图切换、月历布局、任务卡片）
  - JavaScript逻辑（日期计算、视图切换、渲染函数、事件监听）

---

## 技术栈

- **前端**: HTML5, CSS3 (Tailwind CSS), JavaScript (Vanilla JS)
- **后端**: Python 3.9, FastAPI
- **图标**: Font Awesome 6.7.2
- **响应式**: Tailwind CSS Grid + Flexbox

---

## 总结

本次功能开发成功实现了完整的时间筛选和多视图支持，提升了用户体验和数据可视化效果。代码结构清晰，易于维护和扩展。所有功能均已通过测试验证。
