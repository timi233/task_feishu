# P1-4: main.py拆分重构计划

**日期**: 2025-10-31
**目标**: 将1427行main.py拆分为模块化结构
**原则**: Linus风格 - 不过度设计，保持简单

---

## Linus的三个问题

### 1. 这是真实问题吗？
✅ **是的**: 1427行单文件严重违反单一职责原则
- 包含25个路由端点
- 混合了路由、业务逻辑、数据模型
- 任何修改都需要重新阅读整个文件

### 2. 有更简单的方法吗？
✅ **最小化拆分**:
- 只拆分router层（不要立即引入service/model层）
- 按功能模块分组路由
- 保持业务逻辑在router中（后续再重构）

### 3. 这会破坏什么？
⚠️ **风险点**:
- 导入顺序问题可能导致循环依赖
- 依赖注入(Depends)需要调整导入
- CORS/middleware配置需要在主文件中

---

## 当前结构分析

### 路由分组 (25个路由)

| 分组 | 路由数 | 端点列表 | 建议拆分 |
|-----|-------|---------|---------|
| **基础** | 2 | `/`, `/health` | 保留在main.py |
| **中间件** | 2 | http middleware (2个) | 保留在main.py |
| **任务** | 5 | `/api/tasks`, `/api/tasks/by-engineer`, by-date, stats, search | tasks.py |
| **筛选器** | 5 | `/api/filters` + CRUD操作 | filters.py |
| **工程师** | 2 | `/api/engineers`, `/api/engineers/sync` | engineers.py |
| **同步** | 1 | `/api/sync` | sync.py |
| **审批** | 7 | `/api/approvals` + CRUD + transfer/complete | approvals.py |

### Pydantic模型统计

```bash
$ grep "class.*BaseModel" backend/main.py | wc -l
14
```

14个Pydantic模型定义在main.py中，需要移到独立的models/schemas.py

---

## 重构方案

### 阶段1: 最小化拆分（本次实施）

```
backend/
├── main.py                    # ~100行: app初始化、CORS、基础端点
├── routers/
│   ├── __init__.py
│   ├── tasks.py               # 任务查询端点 (~200行)
│   ├── approvals.py           # 审批管理端点 (~400行)
│   ├── filters.py             # 筛选器管理 (~150行)
│   ├── engineers.py           # 工程师管理 (~100行)
│   └── sync.py                # 数据同步端点 (~100行)
└── models/
    ├── __init__.py
    └── schemas.py             # Pydantic模型 (~200行)
```

**总计**: 1427行 → 7个文件 (主文件100行)

### 阶段2: 业务逻辑分离（后续可选）

```
backend/
├── services/
│   ├── task_service.py        # 任务业务逻辑
│   ├── approval_service.py    # 审批业务逻辑
│   └── sync_service.py        # 同步业务逻辑
└── utils/
    ├── dependencies.py        # 依赖注入函数
    └── helpers.py             # 辅助函数
```

**本次不实施** - Linus说："不要为未来编码，等真正需要时再重构"

---

## 实施步骤

### 步骤1: 创建目录结构
```bash
mkdir -p backend/routers
mkdir -p backend/models
touch backend/routers/__init__.py
touch backend/models/__init__.py
```

### 步骤2: 提取Pydantic模型
创建`backend/models/schemas.py`，移动所有`class XXXBaseModel`

### 步骤3: 拆分路由文件
按优先级顺序（最独立的先拆）:
1. filters.py - 最独立
2. engineers.py - 依赖少
3. sync.py - 独立同步逻辑
4. tasks.py - 核心查询逻辑
5. approvals.py - 最复杂，依赖多

### 步骤4: 重构main.py
- 移除已拆分的端点
- 添加router注册
```python
from routers import tasks, approvals, filters, engineers, sync

app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(filters.router)
app.include_router(engineers.router)
app.include_router(sync.router)
```

### 步骤5: 测试验证
- 运行所有P0测试
- 检查API端点路径不变
- 验证Docker容器启动

---

## 代码迁移模板

### router文件模板

```python
"""
XXX管理路由

提供XXX相关的API端点
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from models.schemas import XXXRequest, XXXResponse
from auth import verify_readonly_api_key
from rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["xxx"]
)


@router.get("/xxx")
async def get_xxx():
    """获取XXX"""
    try:
        # ... 业务逻辑
        return {...}
    except Exception as e:
        logger.exception("Failed to get xxx: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 循环依赖预防

### 依赖关系图

```
main.py
  ↓ import
routers/*.py
  ↓ import
models/schemas.py
  ↓ import (避免反向导入routers)
无其他依赖
```

### 规则
1. ✅ main.py → routers → models → 无
2. ❌ models → routers (禁止)
3. ❌ routers → main.py (禁止)
4. ✅ routers → auth, rate_limit, task_db (允许)

---

## 测试计划

### 单元测试（已存在）
```bash
python3 test_p0_upsert.py
python3 test_p0_api.py
```

### 手动测试清单
- [ ] GET /health 返回200
- [ ] GET /api/tasks 返回任务列表
- [ ] POST /api/sync 可以同步数据
- [ ] GET /api/filters 返回筛选器列表
- [ ] GET /api/engineers 返回工程师列表
- [ ] POST /api/approvals 可以创建审批
- [ ] Docker容器启动成功

---

## 预期结果

### 拆分后的main.py (~100行)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入路由
from routers import tasks, approvals, filters, engineers, sync

app = FastAPI(title="飞书派工系统")

# CORS配置
app.add_middleware(CORSMiddleware, ...)

# 基础端点
@app.get("/")
def root():
    return {"message": "飞书派工系统API"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# 注册路由
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(filters.router)
app.include_router(engineers.router)
app.include_router(sync.router)
```

### 对比
- **之前**: 1427行单文件
- **之后**: 主文件100行 + 5个router文件
- **收益**: 易于定位、修改、测试

---

## 风险缓解

### 1. 保持API端点路径不变
- 所有路由保持`/api/xxx`前缀
- 不修改请求/响应格式
- 客户端无感知

### 2. 分步提交
- 每拆分一个router，立即测试
- 出问题可快速回滚
- Git提交粒度：每个router一次提交

### 3. 保留main.py备份
```bash
cp backend/main.py backend/main.py.backup_20251031
```

---

## 下一步行动

开始实施阶段1，按以下顺序：
1. 创建目录结构 ✓
2. 提取Pydantic模型到models/schemas.py
3. 拆分filters.py（最简单）
4. 拆分engineers.py
5. 拆分sync.py
6. 拆分tasks.py
7. 拆分approvals.py（最复杂）
8. 重构main.py
9. 全面测试

**预计时间**: 1-2小时
**风险**: 中等（有完整测试覆盖）
