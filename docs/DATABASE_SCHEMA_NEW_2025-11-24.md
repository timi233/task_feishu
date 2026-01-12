# 新数据存储设计方案

**日期**: 2025-11-24
**目标**: 整合爱数原厂派单和工单数据到统一存储

## 数据源

| 表格名称 | Table ID | 记录数 | 字段数 |
|---------|----------|--------|--------|
| 爱数原厂派单 | tbl8DESrT22JYvfS | 10 | 46 |
| 工单 | tbl6CuEM97ybgRri | 69 | 42 |

Base ID: `U7eAb65luaX1zKscoOzcgcednlh`

## 设计方案

### 核心表: `dispatch_orders`

统一存储两种派工单，通过 `order_type` 区分类型。

```sql
CREATE TABLE dispatch_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 唯一标识
    source_id TEXT NOT NULL UNIQUE,      -- 飞书SourceID，全局唯一
    order_type TEXT NOT NULL,            -- 类型: eisoo_dispatch(爱数原厂派单) / work_order(工单)

    -- 审批基本信息
    approval_code TEXT,                  -- 申请编号
    approval_status TEXT,                -- 申请状态
    approval_flow TEXT,                  -- 审批流程
    approval_node TEXT,                  -- 审批节点

    -- 时间信息
    submit_time INTEGER,                 -- 发起时间(时间戳)
    complete_time INTEGER,               -- 完成时间(时间戳)

    -- 发起人信息
    submitter_id TEXT,                   -- 发起人ID
    submitter_name TEXT,                 -- 发起人姓名
    submitter_department TEXT,           -- 发起人部门
    current_handler TEXT,                -- 当前处理人

    -- 产品信息
    product_category TEXT,               -- 产品分类
    product_model TEXT,                  -- 产品型号
    work_type TEXT,                      -- 工作类型
    work_method TEXT,                    -- 工作方式
    priority TEXT,                       -- 优先级

    -- 服务时间
    service_start_time INTEGER,          -- 服务开始时间(时间戳)
    service_start_period TEXT,           -- 服务开始时间段
    service_end_time INTEGER,            -- 服务结束时间(时间戳)
    service_end_period TEXT,             -- 服务结束时间段

    -- 工程师信息
    engineer_id TEXT,                    -- 售后工程师ID
    engineer_name TEXT,                  -- 售后工程师姓名
    engineer_identity TEXT,              -- 工程师身份

    -- 客户信息
    customer_company TEXT,               -- 客户公司名称
    customer_contact TEXT,               -- 客户联系人
    customer_phone TEXT,                 -- 客户联系方式

    -- 渠道信息
    has_channel TEXT,                    -- 是否有渠道
    channel_name TEXT,                   -- 渠道名称
    channel_contact TEXT,                -- 渠道联系人
    channel_phone TEXT,                  -- 渠道联系人联系方式

    -- 工作内容
    work_content TEXT,                   -- 工作内容
    work_duration REAL,                  -- 时长(小时)

    -- 工单特有
    order_status TEXT,                   -- 工单状态(仅工单类型)

    -- 爱数原厂派单特有
    vendor_contact TEXT,                 -- 厂家对接人(仅爱数原厂派单)

    -- 扩展字段(JSON存储其他字段)
    extra_data TEXT,                     -- JSON格式存储其他字段

    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_dispatch_orders_type ON dispatch_orders(order_type);
CREATE INDEX idx_dispatch_orders_status ON dispatch_orders(approval_status);
CREATE INDEX idx_dispatch_orders_engineer ON dispatch_orders(engineer_name);
CREATE INDEX idx_dispatch_orders_submit_time ON dispatch_orders(submit_time);
CREATE INDEX idx_dispatch_orders_service_start ON dispatch_orders(service_start_time);
```

### 视图: 用于前端展示

```sql
-- 任务视图(兼容现有前端)
CREATE VIEW v_tasks AS
SELECT
    source_id as record_id,
    COALESCE(work_content, product_category || ' - ' || customer_company) as task_name,
    engineer_name as assignee,
    CASE
        WHEN approval_status = '审批中' THEN '进行中'
        WHEN approval_status = '已完成' THEN '已结束'
        ELSE priority
    END as status,
    priority,
    approval_status as application_status,
    date(service_start_time/1000, 'unixepoch', 'localtime') as date,
    date(service_start_time/1000, 'unixepoch', 'localtime') as start_date,
    date(service_end_time/1000, 'unixepoch', 'localtime') as end_date,
    CASE strftime('%w', date(service_start_time/1000, 'unixepoch', 'localtime'))
        WHEN '0' THEN 'weekend'
        WHEN '1' THEN 'monday'
        WHEN '2' THEN 'tuesday'
        WHEN '3' THEN 'wednesday'
        WHEN '4' THEN 'thursday'
        WHEN '5' THEN 'friday'
        WHEN '6' THEN 'weekend'
    END as weekday,
    order_type
FROM dispatch_orders;
```

## 字段映射

### 爱数原厂派单 -> dispatch_orders

| 飞书字段 | 数据库字段 |
|---------|-----------|
| SourceID | source_id |
| 申请编号 | approval_code |
| 申请状态 | approval_status |
| 审批流程 | approval_flow |
| 发起时间 | submit_time |
| 完成时间 | complete_time |
| 发起人 | submitter_name |
| 发起人部门 | submitter_department |
| 当前处理人 | current_handler |
| 审批节点 | approval_node |
| 厂家对接人 | vendor_contact |
| 产品分类 | product_category |
| 产品型号 | product_model |
| 工作类型 | work_type |
| 工作方式 | work_method |
| 优先级 | priority |
| 服务开始时间 | service_start_time |
| 服务开始时间-时间段 | service_start_period |
| 服务结束时间 | service_end_time |
| 服务结束时间-时间段 | service_end_period |
| 售后工程师 | engineer_name |
| 工程师身份 | engineer_identity |
| 客户公司名称 | customer_company |
| 客户联系人 | customer_contact |
| 客户联系方式 | customer_phone |
| 是否有渠道 | has_channel |
| 渠道名称 | channel_name |
| 渠道联系人 | channel_contact |
| 渠道联系人联系方式 | channel_phone |
| 工作内容 | work_content |
| 其他字段 | extra_data (JSON) |

### 工单 -> dispatch_orders

| 飞书字段 | 数据库字段 |
|---------|-----------|
| SourceID | source_id |
| 申请编号 | approval_code |
| 申请状态 | approval_status |
| 审批流程 | approval_flow |
| 发起时间 | submit_time |
| 完成时间 | complete_time |
| 发起人 | submitter_name |
| 发起人部门 | submitter_department |
| 当前处理人 | current_handler |
| 审批节点 | approval_node |
| 产品分类 | product_category |
| 产品型号 | product_model |
| 工作类型 | work_type |
| 工作方式 | work_method |
| 优先级 | priority |
| 服务开始时间 | service_start_time |
| 服务开始时间-时间段 | service_start_period |
| 服务结束时间 | service_end_time |
| 服务结束时间-时间段 | service_end_period |
| 售后工程师 | engineer_name |
| 工程师身份 | engineer_identity |
| 客户公司名称 | customer_company |
| 客户联系人 | customer_contact |
| 客户联系方式 | customer_phone |
| 是否有渠道 | has_channel |
| 渠道名称 | channel_name |
| 渠道联系人 | channel_contact |
| 渠道联系人联系方式 | channel_phone |
| 工作内容 | work_content |
| 时长 | work_duration |
| 工单状态 | order_status |
| 其他字段 | extra_data (JSON) |

## 迁移计划

1. 创建新表 `dispatch_orders`
2. 实现飞书同步脚本
3. 同步数据到新表
4. 创建兼容视图
5. 修改API使用新表
6. 验证功能正常后删除旧表
