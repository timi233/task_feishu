# 筛选器API文档

## 筛选器配置

筛选器配置存储在 `filter_config.json` 文件中，包含以下结构：

```json
{
  "filters": {
    "筛选器名称": {
      "enabled": true/false,
      "conditions": [
        {
          "field": "字段名",
          "operator": "操作符",
          "value": "值"
        }
      ],
      "logic": "and/or"  // 多条件逻辑关系
    }
  },
  "active_filter": "当前激活的筛选器名称"
}
```

## 支持的操作符

- `equals`: 等于
- `not_equals`: 不等于
- `contains`: 包含
- `not_contains`: 不包含
- `in`: 在列表中
- `not_in`: 不在列表中
- `greater_than`: 大于
- `less_than`: 小于
- `not_empty`: 非空
- `is_empty`: 为空

## API端点

### 获取任务列表（支持筛选）
```
GET /api/tasks
```

参数：
- `start_date` (可选): 开始日期 (YYYY-MM-DD)
- `end_date` (可选): 结束日期 (YYYY-MM-DD)
- `filter_name` (可选): 筛选器名称

### 获取所有筛选器
```
GET /api/filters
```

### 激活筛选器
```
POST /api/filters/activate?filter_name={筛选器名称}
```

### 添加筛选器
```
POST /api/filters/add
```
参数：
- `name`: 筛选器名称
- `conditions`: 条件列表
- `enabled` (可选): 是否启用，默认为true
- `logic` (可选): 逻辑关系(and/or)，默认为and

### 更新筛选器
```
PUT /api/filters/{筛选器名称}
```
参数：
- `conditions` (可选): 条件列表
- `enabled` (可选): 是否启用
- `logic` (可选): 逻辑关系(and/or)

### 删除筛选器
```
DELETE /api/filters/{筛选器名称}
```