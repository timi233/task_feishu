# 派工数据同步问题修复记录

**日期**: 2025-12-02
**问题类型**: 数据同步不完整
**严重程度**: 高
**状态**: 已修复

---

## 问题描述

用户反馈在系统页面上看不到最新的派工数据，特别是左元锟和杨宏宇本周的派工任务没有显示。

### 现象
- 飞书多维表格中有最新数据（包括12月1日、12月2日的派工）
- 系统页面只显示部分数据，缺少部分工程师的派工记录
- 后台日志显示定时同步正常执行

---

## 问题排查过程

### 1. 检查定时同步状态
```bash
docker logs docker-app-1 2>&1 | grep -E "Sleeping|Running data sync"
```
结果：定时同步每30分钟执行一次，日志显示正常。

### 2. 检查数据库数据
发现系统有**两个数据表**存储派工数据：

| 数据表 | 记录数 | 最新数据日期 | 用途 |
|--------|--------|-------------|------|
| `tasks` | 676条 | 2025-12-05 | 旧版数据存储 |
| `dispatch_orders` | 104条 | 2025-12-01 | **前端当前使用** |

### 3. 检查同步脚本
`scripts/start.sh` 中的定时任务只调用了 `sync_once.py`：
```bash
run_sync(){
    python sync_once.py  # 只同步 tasks 表
}
```

而 `sync_once.py` 只同步 `tasks` 表，**没有调用 `dispatch_sync.py` 同步 `dispatch_orders` 表**。

### 4. 确认前端使用的API
前端页面调用的是 `/api/dispatch/orders`，读取 `dispatch_orders` 表的数据。

---

## 根本原因

**定时同步脚本不完整**：`start.sh` 中的定时任务只同步了 `tasks` 表，没有同步前端实际使用的 `dispatch_orders` 表。

### 数据流对比

```
旧数据流（sync_once.py）:
飞书多维表格 → process_feishu_records() → tasks 表 → /api/tasks

新数据流（dispatch_sync.py）:
飞书多维表格 → _map_record_to_order() → dispatch_orders 表 → /api/dispatch/orders
                                                              ↑
                                                         前端使用这个
```

---

## 修复方案

### 修改 `scripts/start.sh`

**修改前**：
```bash
run_sync(){
    echo "Running data sync at $(date)"
    python sync_once.py
}
```

**修改后**：
```bash
run_sync(){
    echo "Running data sync at $(date)"
    python sync_once.py
    echo "Running dispatch sync at $(date)"
    python -c "from dispatch_sync import sync_all; sync_all()"
}
```

### 生效步骤

1. 修改已完成（文件路径：`/opt/task_feishu/prod_192.168.101.13/scripts/start.sh`）

2. 重启容器使修改生效：
```bash
cd /opt/task_feishu/prod_192.168.101.13/docker
docker-compose restart app
```

---

## 临时解决方案（已执行）

在修复生效前，手动执行了一次 dispatch 同步：
```bash
docker exec docker-app-1 python3 -c "from dispatch_sync import sync_all; sync_all()"
```

结果：
```
{'eisoo_dispatch': 14, 'work_order': 81}
```

---

## 验证结果

修复后，左元锟和杨宏宇本周的派工数据已正常显示：

| 日期 | 工程师 | 客户 | 类型 |
|------|--------|------|------|
| 2025-12-02 | 杨宏宇 | 济南铁路局 | work_order |
| 2025-12-02 | 左元锟 | 石大胜华 | work_order |
| 2025-12-01 | 左元锟 | 创想智控 | work_order |
| 2025-12-01 | 左元锟 | 骏马道机械有限公司 | work_order |

---

## 系统架构说明

### 数据同步架构

```
┌─────────────────────────────────────────────────────────────┐
│                     飞书多维表格                              │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ 公司派单         │    │ 厂家派工         │                │
│  │ tbl6CuEM97ybgRri│    │ tbl8DESrT22JYvfS│                │
│  └────────┬────────┘    └────────┬────────┘                │
└───────────┼─────────────────────┼──────────────────────────┘
            │                     │
            ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    定时同步任务 (每30分钟)                    │
│                                                             │
│  sync_once.py          dispatch_sync.py                     │
│       │                      │                              │
│       ▼                      ▼                              │
│  ┌─────────┐           ┌──────────────┐                    │
│  │ tasks   │           │dispatch_orders│ ← 前端使用        │
│  │   表    │           │      表       │                    │
│  └─────────┘           └──────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### 定时同步机制

使用 Shell 脚本后台循环实现（`scripts/start.sh`）：

```bash
(
    while true; do
        sleep $((SYNC_INTERVAL_MINUTES * 60))
        run_sync
    done
) &
```

- 默认同步间隔：30分钟（可通过 `SYNC_INTERVAL_MINUTES` 环境变量配置）
- 容器启动时会先执行一次初始同步

---

## 后续建议

1. **监控同步状态**：建议添加同步成功/失败的监控告警
2. **统一数据表**：考虑统一使用 `dispatch_orders` 表，废弃旧的 `tasks` 表
3. **同步日志**：增加同步结果的详细日志，便于排查问题
4. **API 同步入口**：除了手动触发 `/api/sync/dispatch`，还应支持管理后台一键同步

---

## 相关文件

- `scripts/start.sh` - 容器启动脚本（已修改）
- `backend/sync_once.py` - tasks 表同步脚本
- `backend/dispatch_sync.py` - dispatch_orders 表同步脚本
- `backend/routers/sync.py` - 同步 API 路由
- `backend/routers/dispatch.py` - 派工单 API 路由
