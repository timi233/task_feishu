# P1-5: 错误处理机制设计

**日期**: 2025-10-31
**状态**: ✅ 已实现（可选使用）

---

## Linus的三个问题

### 1. 这是真实问题吗？

**观察到的重复**:
```python
# 审批相关端点中的重复模式（6处）
except ApprovalAPIError as exc:
    logger.exception("...: %s", exc)
    raise HTTPException(status_code=502, detail=str(exc)) from exc
except Exception as exc:
    logger.exception("...: %s", exc)
    raise HTTPException(status_code=500, detail="...") from exc
```

**答案**: ⚠️ **半真实问题**
- 有重复代码，但每个端点的错误消息都不同
- 当前代码清晰易懂，每个端点的错误处理一目了然
- 过早抽象可能降低可读性

### 2. 有更简单的方法吗？

**选项1: 装饰器** (❌ 不推荐)
```python
@handle_api_errors("Create dispatch")
async def create_dispatch(...):
    ...
```
- ❌ 增加函数嵌套层次
- ❌ 违反Linus的"扁平化"原则
- ❌ 装饰器顺序问题复杂

**选项2: FastAPI Exception Handler** (✅ 推荐)
```python
@app.exception_handler(ApprovalAPIError)
async def handler(request, exc):
    return JSONResponse(...)
```
- ✅ 更符合FastAPI架构
- ✅ 集中管理异常映射
- ✅ 不增加函数嵌套

**选项3: 保持现状** (✅ 也推荐)
```python
try:
    ...
except ApprovalAPIError as exc:
    logger.exception("Create dispatch failed: %s", exc)
    raise HTTPException(status_code=502, detail=str(exc)) from exc
```
- ✅ 清晰明了
- ✅ 端点特定的错误消息
- ✅ 调试简单
- ⚠️ 有重复代码

### 3. 这会破坏什么？

**使用全局handler的风险**:
- ⚠️ 丢失端点特定的错误上下文
- ⚠️ 错误消息变得通用化
- ⚠️ 调试时不知道是哪个端点出错
- ⚠️ 难以为不同端点定制错误响应

---

## 设计决策

### 方案: 提供可选的Exception Handler，不强制使用

**理由**:
1. Linus说："代码清晰比代码短更重要"
2. 当前try-except模式虽然重复，但非常清晰
3. 端点特定的错误消息对调试很有帮助

### 实施策略

**1. 创建`utils/errors.py`模块** ✅
- 定义全局exception handlers
- 提供`register_exception_handlers(app)`函数
- 供新端点或未来重构使用

**2. 保持main.py现有错误处理** ✅
- 不修改现有端点的try-except块
- 保留端点特定的错误消息
- 避免破坏现有行为

**3. 提供使用指南**
- 文档说明何时使用全局handler
- 何时保留端点特定的异常处理

---

## 实现细节

### 文件结构

```
backend/
├── utils/
│   ├── __init__.py
│   └── errors.py         # 全局异常处理器（可选使用）
└── main.py               # 保持现有try-except模式
```

### utils/errors.py

提供以下功能：
1. `approval_api_error_handler` - 处理ApprovalAPIError → 502
2. `validation_error_handler` - 处理ValueError → 400
3. `generic_exception_handler` - 通用异常 → 500
4. `register_exception_handlers(app)` - 注册到FastAPI app

### 使用方式（可选）

```python
# backend/main.py (可选启用)
from utils.errors import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)  # 启用全局handlers

# 这样endpoint可以不写try-except，异常会被全局handler捕获
@app.post("/api/approvals")
async def create_dispatch(payload: CreateDispatchRequest):
    # 不需要try-except，ApprovalAPIError会被全局handler处理
    manager = get_effective_manager()
    instance_code = manager.create_instance(...)
    return {"success": True, "instance_code": instance_code}
```

---

## 使用建议

### 何时使用全局Exception Handler

✅ **适合使用**:
- 新的简单CRUD端点
- 错误处理逻辑完全一致的端点
- 不需要端点特定错误消息的场景

### 何时保留端点特定的try-except

✅ **推荐保留**:
- 复杂的业务逻辑端点（当前main.py的审批端点）
- 需要端点特定错误消息的场景
- 需要在catch块中做额外操作的情况
- 已有的稳定代码（不要为了减少几行代码而重构）

---

## 当前状态

### 已完成
- ✅ 创建`utils/errors.py`模块
- ✅ 实现三个全局exception handlers
- ✅ 提供`register_exception_handlers`函数

### 未修改（保持现状）
- ✅ main.py中的端点保持现有try-except模式
- ✅ 不强制使用全局handlers
- ✅ 保留端点特定的错误消息

### 建议
- ⏸️ 不建议立即重构现有端点
- ⏸️ 等待实际需求再决定是否启用
- ⏸️ 新端点可选择性使用全局handlers

---

## Linus可能会说

> "代码重复不一定是坏事。如果每个try-except块都清楚地表达了它要做什么，
> 那它就是好代码。不要为了减少几行代码而增加间接层。
>
> 如果你在看代码时需要跳转到另一个文件才能理解错误处理逻辑，
> 那这个抽象就是失败的。"

---

## 总结

**P1-5完成情况**:
- ✅ 已实现统一的错误处理机制（`utils/errors.py`）
- ✅ 提供可选的全局exception handlers
- ✅ 保持现有代码不变（避免过度重构）
- ✅ 提供清晰的使用指南

**最终建议**:
- 将`utils/errors.py`作为工具库保留
- 不在main.py中强制启用
- 新端点根据需要选择性使用
- 重复的try-except如果清晰明了，保留即可

**Linus原则应用**:
1. ✅ 代码清晰 > 代码短
2. ✅ 不增加不必要的间接层
3. ✅ 保持调试友好
