# 飞书派工系统 Code Review 修复计划

**日期**: 2025-10-31
**Review By**: Linus-Style Code Review
**优先级**: P0 (致命) > P1 (严重) > P2 (代码质量) > P3 (优化)

---

## 📋 总体问题概述

| 问题等级 | 数量 | 状态 |
|---------|------|------|
| 🔴 P0 - 致命问题 | 3 | ⏳ 待修复 |
| 🟠 P1 - 严重bug | 4 | ⏳ 待修复 |
| 🟡 P2 - 代码质量 | 4 | ⏳ 待修复 |
| 🟢 P3 - 优化建议 | 3 | ⏳ 待修复 |

---

## 🔴 P0 - 致命问题 (必须立即修复)

### 1. 【P0】移除前端硬编码API Key

**文件**: `frontend/src/utils/api.js:2`

**问题描述**:
```javascript
const API_KEY = 'readonly-key-for-hr-system';  // 🚨 暴露给所有用户!
```
前端硬编码API Key，任何人打开浏览器开发者工具即可获取，完全绕过认证。

**影响**:
- 安全灾难级别
- 任何人都能通过这个Key访问所有需要认证的API
- 可能导致数据泄露、恶意操作

**修复方案**:
1. 删除前端的`const API_KEY`定义
2. 前端专用端点（如`/api/tasks`, `/api/engineers`）改为公开访问，不需要API Key
3. 外部系统专用端点（如`/api/tasks/by-engineer`）保留API Key认证
4. 前端调用时不发送`X-API-Key`头

**修复代码**:
```javascript
// frontend/src/utils/api.js
// ❌ 删除这一行
// const API_KEY = 'readonly-key-for-hr-system';

// ✓ 前端专用端点不需要API Key
export async function fetchTasks(startDate, endDate) {
    const response = await fetch(url);  // 不发送X-API-Key
    return response.json();
}

// ✓ 管理操作需要用户登录后的session token (OAuth)
export async function syncFromFeishu() {
    const response = await fetch(url, {
        method: 'POST',
        credentials: 'include'  // 使用session cookie
    });
    return response.json();
}
```

**后端调整**:
```python
# backend/main.py
@app.get("/api/tasks")  # 移除 dependencies=[Depends(verify_readonly_api_key)]
async def get_tasks(...):
    """前端专用，无需认证"""
    ...

@app.get("/api/tasks/by-engineer", dependencies=[Depends(verify_readonly_api_key)])
async def get_tasks_by_engineer(...):
    """外部系统专用，需要API Key"""
    ...
```

**验证方法**:
```bash
# 前端端点应该可以直接访问
curl http://localhost:8000/api/tasks

# 外部系统端点需要API Key
curl -H "X-API-Key: admin-key-1" http://localhost:8000/api/tasks/by-engineer?engineer=张三
```

---

### 2. 【P0】修复数据库并发问题

**文件**: `backend/task_db.py:166`

**问题描述**:
```python
cursor.execute("DELETE FROM tasks")  # 🚨 并发写入会丢数据
logger.info("Cleared existing processed tasks from database.")
```
全量删除后插入，在并发场景下会导致数据丢失。

**影响**:
- 两个同步任务并发执行时，后一个的DELETE会清空前一个刚插入的数据
- 用户查询可能看到空数据
- 审批实例Code关联丢失

**修复方案**:
使用 `INSERT OR REPLACE` (UPSERT逻辑)，不再全量删除。

**修复代码**:
```python
# backend/task_db.py:159
def save_processed_tasks_to_db(processed_tasks: Dict[str, List[Dict[str, Any]]]):
    """将处理后的任务数据保存到数据库 (使用UPSERT避免并发问题)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # ❌ 删除全量删除
        # cursor.execute("DELETE FROM tasks")

        # ✓ 使用UPSERT逻辑
        upsert_count = 0
        for weekday, tasks in processed_tasks.items():
            for task in tasks:
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks
                    (record_id, task_name, assignee, status, date, start_date, end_date,
                     weekday, priority, application_status, approval_instance_code,
                     approval_status, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
                    task.get("approval_instance_code"),
                    task.get("approval_status")
                ))
                upsert_count += 1

        logger.info("Successfully upserted %d tasks to database.", upsert_count)
```

**注意事项**:
- 需要确保`tasks`表有唯一约束：`UNIQUE(record_id, date)`（已存在）
- `INSERT OR REPLACE`会保留approval相关字段的更新

**验证方法**:
```python
# 测试并发同步
import threading

def sync_task():
    sync_feishu_data_to_db()

t1 = threading.Thread(target=sync_task)
t2 = threading.Thread(target=sync_task)

t1.start()
t2.start()
t1.join()
t2.join()

# 检查数据是否完整
assert get_task_count() > 0
```

---

### 3. 【P0】在需要认证的端点启用限流器

**文件**: `backend/main.py`

**问题描述**:
`rate_limit.py`已定义限流器，但没有在任何端点启用。API可被无限制调用，容易拖垮服务。

**影响**:
- 恶意用户可以暴力请求API
- 服务器资源被耗尽
- 正常用户无法访问

**修复方案**:
在所有需要API Key的端点添加限流依赖。

**修复代码**:
```python
# backend/main.py
from rate_limit import check_rate_limit

@app.get(
    "/api/tasks/by-engineer",
    response_model=TaskListResponse,
    dependencies=[Depends(verify_readonly_api_key), Depends(check_rate_limit)]  # ✓ 添加限流
)
async def get_tasks_by_engineer(
    engineer: str = Query(...),
    api_key: str = Depends(verify_readonly_api_key)
):
    ...

@app.post(
    "/api/sync",
    dependencies=[Depends(verify_readonly_api_key), Depends(check_rate_limit)]  # ✓ 添加限流
)
async def sync_from_feishu(api_key: str = Depends(verify_readonly_api_key)):
    ...

# 对所有需要认证的端点重复上述操作
```

**配置调整**:
```bash
# .env
API_RATE_LIMIT=100  # 每分钟100次请求
```

**验证方法**:
```bash
# 超过限流应该返回429
for i in {1..101}; do
    curl -H "X-API-Key: admin-key-1" http://localhost:8000/api/tasks/by-engineer?engineer=张三
done
# 第101次应该返回: {"detail":"Rate limit exceeded. Max 100 requests per minute."}
```

---

## 🟠 P1 - 严重Bug (影响用户体验)

### 4. 【P1】拆分main.py为routers/services/models结构

**文件**: `backend/main.py` (1472行)

**问题描述**:
单文件过长，违反单一职责原则，难以维护。

**修复方案**:
```
backend/
├── main.py              # app初始化 (~50行)
├── routers/
│   ├── __init__.py
│   ├── tasks.py         # 任务相关端点 (~200行)
│   ├── approvals.py     # 审批相关端点 (~300行)
│   ├── filters.py       # 筛选器端点 (~100行)
│   └── engineers.py     # 工程师端点 (~100行)
├── services/
│   ├── __init__.py
│   ├── task_service.py      # 任务业务逻辑
│   ├── approval_service.py  # 审批业务逻辑
│   └── sync_service.py      # 同步业务逻辑
├── models/
│   ├── __init__.py
│   └── schemas.py       # Pydantic模型
└── utils/
    ├── __init__.py
    ├── errors.py        # 统一错误处理
    └── dependencies.py  # 依赖注入
```

**修复步骤**: 见后续实施部分

---

### 5. 【P1】提取错误处理装饰器

**问题**: 重复的try-except代码块

**修复方案**:
```python
# backend/utils/errors.py
from functools import wraps
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def handle_api_errors(operation: str):
    """统一API错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ValueError as e:
                logger.error(f"{operation} validation error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except ApprovalAPIError as e:
                logger.error(f"{operation} approval API error: {e}")
                raise HTTPException(status_code=502, detail=str(e))
            except Exception as e:
                logger.exception(f"{operation} unexpected error: {e}")
                raise HTTPException(status_code=500, detail=f"{operation} failed")
        return wrapper
    return decorator

# 使用方式
@app.post("/api/approvals")
@handle_api_errors("Create dispatch")
async def create_dispatch(payload: CreateDispatchRequest):
    # 不再需要try-except
    manager = get_effective_manager()
    instance_code = manager.create_instance(...)
    return {"success": True, "instance_code": instance_code}
```

---

### 6. 【P1】删除或启用feishu_records表

**问题**: `feishu_records`表被创建但从未使用

**选项1 - 删除表** (推荐，如果确实不需要审计):
```python
# backend/migrations/drop_feishu_records.py
def upgrade():
    conn.execute("DROP TABLE IF EXISTS feishu_records")
```

**选项2 - 实际使用表** (如果需要审计日志):
```python
# backend/task_db.py
def save_raw_feishu_records_to_db(raw_records: List[Dict]):
    """保存原始飞书数据用于审计"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for record in raw_records:
            cursor.execute("""
                INSERT OR REPLACE INTO feishu_records
                (record_id, fields, synced_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (record["record_id"], json.dumps(record["fields"])))
```

---

### 7. 【P1】使用数据库View优化跨天任务展开逻辑

**问题**: 跨天任务物理存储多行，导致数据冗余

**修复方案**:
```sql
-- backend/migrations/create_daily_tasks_view.sql
CREATE VIEW IF NOT EXISTS daily_tasks AS
WITH RECURSIVE date_series AS (
    SELECT
        record_id,
        task_name,
        assignee,
        status,
        priority,
        application_status,
        start_date as current_date,
        end_date,
        0 as day_offset
    FROM tasks
    WHERE start_date IS NOT NULL AND end_date IS NOT NULL

    UNION ALL

    SELECT
        record_id,
        task_name,
        assignee,
        status,
        priority,
        application_status,
        date(current_date, '+1 day') as current_date,
        end_date,
        day_offset + 1
    FROM date_series
    WHERE current_date < end_date AND day_offset < 365  -- 防止无限递归
)
SELECT
    record_id,
    task_name,
    assignee,
    status,
    priority,
    application_status,
    current_date as date,
    CASE CAST(strftime('%w', current_date) AS INTEGER)
        WHEN 0 THEN 'weekend'
        WHEN 1 THEN 'monday'
        WHEN 2 THEN 'tuesday'
        WHEN 3 THEN 'wednesday'
        WHEN 4 THEN 'thursday'
        WHEN 5 THEN 'friday'
        WHEN 6 THEN 'weekend'
    END as weekday
FROM date_series
ORDER BY record_id, current_date;
```

**修改代码**:
```python
# backend/task_db.py
def get_tasks_from_db(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """从数据库获取任务（使用View自动展开跨天任务）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if start_date and end_date:
            cursor.execute("""
                SELECT * FROM daily_tasks
                WHERE date BETWEEN ? AND ?
            """, (start_date, end_date))
        else:
            cursor.execute("SELECT * FROM daily_tasks")

        # ... 剩余逻辑相同
```

---

## 🟡 P2 - 代码质量问题

### 8. 【P2】简化process_feishu_data.py日期处理逻辑

**问题**: 第103-189行嵌套过深，难以理解

**修复方案**:
```python
# backend/process_feishu_data.py
from datetime import datetime, timedelta
from typing import List, Optional

def parse_timestamp(ts: Optional[int]) -> Optional[datetime]:
    """解析毫秒时间戳"""
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(ts / 1000.0)
    except (ValueError, OSError):
        logger.warning(f"Invalid timestamp: {ts}")
        return None

def expand_date_range(start: datetime, end: datetime) -> List[str]:
    """展开日期范围为日期列表"""
    if not start or not end or start > end:
        return []

    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

def create_task_item(record_id: str, fields: dict, date: str) -> dict:
    """创建单个任务项"""
    # 提取字段
    customer_name = fields.get(CUSTOMER_NAME_FIELD, "")
    task_content = fields.get(TASK_CONTENT_FIELD, "")
    task_name = f"{customer_name} {task_content}".strip()

    # 提取负责人
    assignee = extract_assignee(fields.get(ASSIGNEE_FIELD))

    # 提取状态
    priority = fields.get(PRIORITY_FIELD, "未知优先级")
    application_status = fields.get(APPLICATION_STATUS_FIELD, "")
    status = map_application_status(application_status, priority)

    return {
        "record_id": record_id,
        "task_name": task_name,
        "assignee": assignee,
        "status": status,
        "priority": priority,
        "application_status": application_status,
        "date": date,
        # ...
    }

def process_feishu_records(records: List[Dict]) -> Dict[str, List[Dict]]:
    """处理飞书记录（简化版）"""
    task_groups = {
        "monday": [], "tuesday": [], "wednesday": [],
        "thursday": [], "friday": [], "weekend": [], "unknown_date": []
    }

    for record in records:
        record_id = record.get("record_id", "")
        fields = record.get("fields", {})

        # 解析日期
        start = parse_timestamp(fields.get(START_DATE_FIELD))
        end = parse_timestamp(fields.get(END_DATE_FIELD))

        if not start or not end:
            # 添加到unknown_date
            task_item = create_task_item(record_id, fields, "")
            task_groups["unknown_date"].append(task_item)
            continue

        # 展开日期范围
        dates = expand_date_range(start, end)

        # 为每个日期创建任务
        for date_str in dates:
            task_item = create_task_item(record_id, fields, date_str)
            weekday = get_weekday_key(date_str)
            task_groups[weekday].append(task_item)

    return task_groups
```

---

### 9. 【P2】移除auth.py默认开发密钥

**文件**: `backend/auth.py:22`

**问题**:
```python
API_KEYS = os.getenv("API_KEYS", "default-dev-key")  # 🚨 生产风险
```

**修复**:
```python
# backend/auth.py
API_KEYS_STR = os.getenv("API_KEYS")
if not API_KEYS_STR:
    logger.error("API_KEYS environment variable is not set!")
    raise RuntimeError(
        "API_KEYS must be configured. "
        "Set API_KEYS environment variable before starting the application."
    )

API_KEYS = [key.strip() for key in API_KEYS_STR.split(",") if key.strip()]

if not API_KEYS:
    raise RuntimeError("API_KEYS cannot be empty")
```

---

### 10. 【P2】为sync_feishu_to_db.py添加重试机制

**问题**: 飞书API临时故障导致数据不同步

**修复方案**:
```python
# backend/sync_feishu_to_db.py
import time
from typing import Optional

def exponential_backoff_retry(
    func,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0
):
    """指数退避重试装饰器"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            delay = min(initial_delay * (2 ** attempt), max_delay)
            logger.warning(
                f"Attempt {attempt + 1} failed: {e}. "
                f"Retrying in {delay}s..."
            )
            time.sleep(delay)

def sync_feishu_data_to_db():
    """从飞书同步数据到数据库（带重试）"""
    logger.info(f"\n[SYNC] Starting data synchronization at {time.ctime()}")

    try:
        # 使用重试机制获取数据
        def fetch_data():
            reader = FeishuBitableReader(CONFIG["app_id"], CONFIG["app_secret"])
            return reader.get_records(CONFIG["app_token"], CONFIG["table_id"])

        raw_records = exponential_backoff_retry(fetch_data, max_retries=3)

        if not raw_records:
            logger.warning("[SYNC] No data fetched")
            return

        # 处理和保存数据
        processed_tasks = process_feishu_records(raw_records)
        save_processed_tasks_to_db(processed_tasks)

        logger.info("[SYNC] Completed successfully")

    except Exception as e:
        logger.error(f"[SYNC ERROR] Failed after retries: {e}")
```

---

### 11. 【P2】拆分前端App.js组件

**问题**: `frontend/src/App.js` 412行，职责不清

**修复方案**:
```
frontend/src/
├── App.js                    # 主应用 (~100行)
├── hooks/
│   ├── useTasks.js          # ✓ 已存在
│   ├── useTimeFilter.js     # ✓ 已存在
│   ├── useSync.js           # ✗ 新建：同步逻辑
│   └── useViewMode.js       # ✗ 新建：视图切换
├── components/
│   ├── SyncControl/         # ✗ 新建：同步控制组件
│   │   ├── SyncButton.js
│   │   ├── SyncStatus.js
│   │   └── AutoSyncToggle.js
│   └── ViewModeSwitcher.js  # ✗ 新建：视图切换器
```

**新建 useSync hook**:
```javascript
// frontend/src/hooks/useSync.js
export function useSync() {
    const [syncing, setSyncing] = useState(false);
    const [message, setMessage] = useState(null);
    const [autoEnabled, setAutoEnabled] = useState(true);
    const [nextSyncTime, setNextSyncTime] = useState(null);

    const handleSync = useCallback(async () => {
        setSyncing(true);
        try {
            const data = await syncFromFeishu();
            setMessage({ type: 'success', text: `同步成功！` });
        } catch (err) {
            setMessage({ type: 'error', text: `同步失败: ${err.message}` });
        } finally {
            setSyncing(false);
            setTimeout(() => setMessage(null), 3000);
        }
    }, []);

    return { syncing, message, autoEnabled, nextSyncTime, handleSync };
}
```

---

## 🟢 P3 - 优化建议

### 12. 【P3】添加API版本控制

```python
# backend/main.py
app = FastAPI(title="派工系统API", version="1.0.0")

# 添加版本前缀
@app.get("/api/v1/tasks")
async def get_tasks(...):
    ...
```

### 13. 【P3】创建数据库迁移脚本系统

```python
# backend/migrations/migration_runner.py
def get_current_version():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        return row[0] if row else 0

def apply_migration(version: int, sql: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executescript(sql)
        cursor.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (version,)
        )
```

### 14. 【P3】筛选器逻辑改为SQL WHERE子句

当前在内存中筛选，改为SQL WHERE以提高性能。

---

## 📊 修复进度追踪

- [ ] P0-1: 移除前端API Key
- [ ] P0-2: 修复数据库并发问题
- [ ] P0-3: 启用限流器
- [ ] P1-4: 拆分main.py
- [ ] P1-5: 提取错误处理
- [ ] P1-6: 处理feishu_records表
- [ ] P1-7: 优化跨天任务
- [ ] P2-8: 简化日期处理
- [ ] P2-9: 移除默认密钥
- [ ] P2-10: 添加重试机制
- [ ] P2-11: 拆分App.js
- [ ] P3-12: API版本控制
- [ ] P3-13: 数据库迁移
- [ ] P3-14: 筛选器优化

---

## 🎯 第一阶段实施计划 (今天完成)

**目标**: 修复所有P0问题，确保系统安全稳定

1. ✅ 创建修复计划文档
2. ⏳ 修复P0-1: 移除前端API Key
3. ⏳ 修复P0-2: 数据库并发问题
4. ⏳ 修复P0-3: 启用限流器
5. ⏳ 测试验证所有修复
6. ⏳ 提交代码并记录变更

**预计时间**: 2-3小时

---

**文档版本**: v1.0
**最后更新**: 2025-10-31
