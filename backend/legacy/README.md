# 过期调试脚本

**状态**: ⚠️ 这些脚本已过期，无法在当前系统上运行

---

## 原因

这些脚本引用了早期设计中的`feishu_records`表，但该表在当前实现中**不存在**。

### 数据库实际表结构

当前系统只有两个表：
- `tasks` - 存储处理后的任务数据（包括跨天展开后的任务）
- `engineers` - 存储工程师信息

### 设计变更历史

**早期设计** (未实施):
- `feishu_records` - 存储飞书API返回的原始JSON数据
- `tasks` - 存储处理后的任务数据

**当前实现**:
- 直接处理飞书API返回的数据，不存储原始JSON
- 只保留`tasks`表存储处理后的数据
- 使用`INSERT OR REPLACE (UPSERT)`逻辑避免并发问题

---

## 目录内容

### 过期的调试脚本

| 文件 | 原用途 | 过期原因 |
|------|--------|----------|
| `check_db.py` | 检查feishu_records表内容 | 表不存在 |
| `check_raw_db.py` | 查看原始飞书记录 | 表不存在 |
| `check_date_fields.py` | 调试日期字段解析 | 查询feishu_records表 |
| `check_service_start_time.py` | 检查服务开始时间字段 | 查询feishu_records表 |
| `debug_empty_dates.py` | 调试空日期问题 | 查询feishu_records表 |
| `migrate_to_mysql.py` | 迁移到MySQL | 尝试迁移不存在的表 |

### 仍然有效的调试脚本

这些脚本在`backend/`主目录中，可以正常使用：
- ✅ `check_cross_day_tasks.py` - 检查跨天任务展开
- ✅ `check_current_week_view.py` - 检查本周视图
- ✅ `check_filter_data.py` - 检查筛选器功能
- ✅ `check_filtered_tasks.py` - 检查筛选后的任务
- ✅ `check_week_data.py` - 检查周数据
- ✅ `check_db_week.py` - 检查数据库周数据

---

## 如果需要审计日志功能

如果未来需要保存飞书API的原始响应数据用于审计，可以：

### 方案1: 重新启用feishu_records表

```python
# backend/task_db.py - init_db()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS feishu_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT UNIQUE NOT NULL,
        fields JSON NOT NULL,
        created_time INTEGER,
        last_modified_time INTEGER,
        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# backend/sync_feishu_to_db.py
def save_raw_records(raw_records):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for record in raw_records:
            cursor.execute("""
                INSERT OR REPLACE INTO feishu_records
                (record_id, fields, created_time, last_modified_time)
                VALUES (?, ?, ?, ?)
            """, (
                record["record_id"],
                json.dumps(record["fields"]),
                record.get("created_time"),
                record.get("last_modified_time")
            ))
```

### 方案2: 使用日志文件（更简单）

```python
# backend/sync_feishu_to_db.py
import json
from datetime import datetime

def log_raw_response(raw_records):
    log_file = f"data/logs/feishu_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(raw_records, f, ensure_ascii=False, indent=2)
```

---

## 参考资料

- 数据库schema: `backend/task_db.py::init_db()`
- 数据处理逻辑: `backend/process_feishu_data.py::process_feishu_records()`
- P0-2 UPSERT修复: `docs/P0_FIXES_SUMMARY_2025-10-31.md`
- 清理报告: `docs/P1-6_FEISHU_RECORDS_CLEANUP.md`

---

**移动日期**: 2025-10-31
**决策依据**: Linus-Style Code Review P1-6
