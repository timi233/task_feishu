# P1-6: feishu_records表清理报告

**日期**: 2025-10-31
**问题**: 代码中引用了不存在的feishu_records表
**状态**: ✅ 已分析，准备清理

---

## 调查结果

### 数据库实际情况
```bash
$ sqlite3 ./data/db/tasks.db ".tables"
engineers  tasks
```

**结论**: 数据库中只有`engineers`和`tasks`两个表，**没有feishu_records表**

### 代码引用分析

**真实使用** (函数名，非表名):
- `process_feishu_data.py::process_feishu_records()` - 处理内存中的飞书记录
- `sync_feishu_to_db.py` - 调用process_feishu_records函数
- `sync_once.py` - 调用process_feishu_records函数
- `main.py` - 调用process_feishu_records函数

**过期引用** (查询不存在的表):
- `check_db.py` - 查询feishu_records表
- `check_raw_db.py` - 查询feishu_records表
- `check_date_fields.py` - 查询feishu_records表
- `check_service_start_time.py` - 查询feishu_records表
- `debug_empty_dates.py` - 查询feishu_records表
- `migrate_to_mysql.py` - 尝试迁移feishu_records表

---

## Linus的三个问题

### 1. 这是真实问题还是想象的？
✅ **真实问题**:
- 调试脚本引用不存在的表，运行会报错
- 增加认知负担，让人误以为这个表应该存在
- "死代码"违反Linus的"代码应该做有用的事"原则

### 2. 有没有更简单的方法？
✅ **最简单的方法**:
- 移动过期调试脚本到`backend/legacy/`目录
- 添加README说明这些脚本已过期
- 保留函数`process_feishu_records()`（这是正常代码）

### 3. 这会破坏什么？
✅ **零风险**:
- 这些脚本都是调试工具，不在生产代码路径中
- 核心业务逻辑不依赖feishu_records表
- 可以随时从git历史恢复

---

## 清理方案

### 方案1: 移动到legacy目录（推荐）

**优点**:
- 保留调试脚本供参考
- 明确标记为过期代码
- 减少主目录混乱

**操作**:
```bash
mkdir -p backend/legacy
mv backend/check_db.py backend/legacy/
mv backend/check_raw_db.py backend/legacy/
mv backend/check_date_fields.py backend/legacy/
mv backend/check_service_start_time.py backend/legacy/
mv backend/debug_empty_dates.py backend/legacy/
mv backend/migrate_to_mysql.py backend/legacy/

# 创建README
cat > backend/legacy/README.md << 'EOF'
# 过期调试脚本

这些脚本引用了早期设计中的`feishu_records`表，该表在当前实现中不存在。

**数据库实际表**: `tasks`, `engineers`

这些脚本保留用于参考，但无法在当前系统上运行。
EOF
```

### 方案2: 直接删除（激进）

**Linus可能会说**: "如果代码不工作，就删掉它。Git会记住历史。"

```bash
rm backend/check_db.py
rm backend/check_raw_db.py
rm backend/check_date_fields.py
rm backend/check_service_start_time.py
rm backend/debug_empty_dates.py
rm backend/migrate_to_mysql.py
```

---

## 决策：采用方案1（移动到legacy）

**理由**:
1. 这些脚本可能包含有用的调试思路
2. 移动比删除更保守，更容易回滚
3. 减少backend/目录的混乱
4. 符合"不要随意删除可能有用的工具"原则

---

## 保留的调试脚本（正常工作）

这些脚本查询实际存在的表，应保留：
- ✅ `check_cross_day_tasks.py` - 检查跨天任务
- ✅ `check_current_week_view.py` - 检查本周视图
- ✅ `check_filter_data.py` - 检查筛选器
- ✅ `check_filtered_tasks.py` - 检查筛选后的任务
- ✅ `check_week_data.py` - 检查周数据
- ✅ `check_db_week.py` - 检查数据库周数据

---

## 执行清理

执行方案1的命令，然后提交：
```bash
git add backend/legacy/
git commit -m "refactor: 移动过期调试脚本到legacy目录

- 这些脚本引用不存在的feishu_records表
- 实际数据库只有tasks和engineers两个表
- 保留脚本供参考，但标记为过期代码"
```

---

## 验证

清理后运行测试确保核心功能不受影响：
```bash
cd /home/jian/code/Task_feishu/backend
python3 test_p0_upsert.py
python3 test_p0_api.py
```
