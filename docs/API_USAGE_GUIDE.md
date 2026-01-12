# 派工系统API使用指南

## 概述

派工系统提供RESTful API供其他内部系统调用,支持查询任务、统计数据等功能。

**基础URL**: `http://your-server:8000`

**认证方式**: API Key (HTTP Header)

**数据格式**: JSON

---

## 认证

所有API请求需要在HTTP Header中携带API Key:

```http
GET /api/tasks/by-engineer?engineer=张三
Host: your-server:8000
X-API-Key: your-readonly-key-here
Content-Type: application/json
```

### 获取API Key

联系派工系统管理员申请**只读API Key**(其他系统使用):

- 📧 邮件: admin@company.com
- 💬 企业微信: 派工系统管理员

---

## API端点列表

| 端点 | 方法 | 用途 | 限流 |
|------|------|------|------|
| `/health` | GET | 健康检查 | 无限制 |
| `/api/tasks/by-engineer` | GET | 按工程师查询任务 | 100次/分钟 |
| `/api/tasks/by-date` | GET | 按单日查询任务 | 100次/分钟 |
| `/api/tasks/stats` | GET | 获取统计数据 | 100次/分钟 |
| `/api/tasks/search` | GET | 搜索任务 | 100次/分钟 |
| `/api/engineers` | GET | 获取工程师列表 | 100次/分钟 |

---

## 详细文档

### 1. 健康检查

**端点**: `GET /health`

**用途**: 监控系统检测服务状态

**认证**: 无需API Key

**请求示例**:
```bash
curl http://your-server:8000/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "database": "connected",
  "task_count": 1234,
  "timestamp": "2025-10-20T10:30:00.123456"
}
```

**响应字段**:
- `status`: 服务状态 (`healthy` / `unhealthy`)
- `database`: 数据库连接状态
- `task_count`: 数据库中任务总数
- `timestamp`: 检查时间

---

### 2. 按工程师查询任务

**端点**: `GET /api/tasks/by-engineer`

**用途**: 查询特定工程师在指定日期范围内的所有任务

**认证**: 需要只读API Key

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `engineer` | string | ✅ | 工程师姓名 |
| `start_date` | string | ❌ | 开始日期 (YYYY-MM-DD),默认本周开始 |
| `end_date` | string | ❌ | 结束日期 (YYYY-MM-DD),默认本周结束 |

**请求示例**:
```bash
curl -X GET "http://your-server:8000/api/tasks/by-engineer?engineer=张三&start_date=2025-10-13&end_date=2025-10-19" \
  -H "X-API-Key: your-readonly-key"
```

**响应示例**:
```json
{
  "total": 5,
  "tasks": [
    {
      "record_id": "rec123",
      "task_name": "阿里巴巴 网络故障排查",
      "assignee": "张三",
      "status": "进行中",
      "priority": "紧急",
      "application_status": "审批中",
      "date": "2025-10-15",
      "start_date": "2025-10-15",
      "end_date": "2025-10-15",
      "weekday": "wednesday"
    }
  ]
}
```

**使用场景**:
- HR系统统计工程师工作量
- 其他系统查询某人本周任务

---

### 3. 按日期查询任务

**端点**: `GET /api/tasks/by-date`

**用途**: 查询某天的所有派工任务

**认证**: 需要只读API Key

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `date` | string | ✅ | 日期 (YYYY-MM-DD) |

**请求示例**:
```bash
curl -X GET "http://your-server:8000/api/tasks/by-date?date=2025-10-15" \
  -H "X-API-Key: your-readonly-key"
```

**响应示例**:
```json
{
  "total": 20,
  "tasks": [
    {
      "record_id": "rec456",
      "task_name": "腾讯 系统升级",
      "assignee": "李四",
      "status": "已结束",
      "priority": "重要",
      "date": "2025-10-15",
      ...
    }
  ]
}
```

**使用场景**:
- 日报系统获取当天所有派工
- 考勤系统核对工作安排

---

### 4. 获取统计数据

**端点**: `GET /api/tasks/stats`

**用途**: 获取指定时间范围内的任务统计信息

**认证**: 需要只读API Key

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `start_date` | string | ❌ | 开始日期,默认本周开始 |
| `end_date` | string | ❌ | 结束日期,默认本周结束 |

**请求示例**:
```bash
curl -X GET "http://your-server:8000/api/tasks/stats?start_date=2025-10-13&end_date=2025-10-19" \
  -H "X-API-Key: your-readonly-key"
```

**响应示例**:
```json
{
  "date_range": {
    "start": "2025-10-13",
    "end": "2025-10-19"
  },
  "by_engineer": [
    {
      "engineer": "张三",
      "total_tasks": 15,
      "very_urgent": 2,
      "urgent": 5,
      "important": 8
    },
    {
      "engineer": "李四",
      "total_tasks": 12,
      "very_urgent": 1,
      "urgent": 3,
      "important": 8
    }
  ],
  "by_priority": {
    "非常紧急": 10,
    "紧急": 20,
    "重要": 35
  }
}
```

**使用场景**:
- 管理仪表盘展示工作量分布
- 周报/月报自动生成

---

### 5. 搜索任务

**端点**: `GET /api/tasks/search`

**用途**: 全文搜索任务内容

**认证**: 需要只读API Key

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `keyword` | string | ✅ | 搜索关键词 |
| `limit` | int | ❌ | 最大返回数量,默认100 |

**请求示例**:
```bash
curl -X GET "http://your-server:8000/api/tasks/search?keyword=阿里巴巴&limit=10" \
  -H "X-API-Key: your-readonly-key"
```

**响应示例**:
```json
{
  "total": 3,
  "tasks": [
    {
      "record_id": "rec789",
      "task_name": "阿里巴巴 数据库优化",
      "assignee": "王五",
      "status": "进行中",
      ...
    }
  ]
}
```

**搜索范围**:
- 任务名称 (`task_name`)
- 工程师姓名 (`assignee`)

**使用场景**:
- 搜索特定客户的所有任务
- 搜索特定关键词相关派工

---

### 6. 获取工程师列表

**端点**: `GET /api/engineers`

**用途**: 获取系统中所有工程师名单

**认证**: 需要只读API Key

**参数**: 无

**请求示例**:
```bash
curl -X GET "http://your-server:8000/api/engineers" \
  -H "X-API-Key: your-readonly-key"
```

**响应示例**:
```json
{
  "total": 5,
  "engineers": ["张三", "李四", "王五", "赵六", "钱七"]
}
```

**使用场景**:
- 其他系统构建工程师选择器
- 统计系统获取人员名单

---

## 错误处理

### HTTP状态码

| 状态码 | 含义 | 处理方式 |
|--------|------|---------|
| 200 | 成功 | 正常处理响应数据 |
| 403 | API Key无效 | 检查X-API-Key header |
| 429 | 请求过于频繁 | 减慢请求速度,当前限制100次/分钟 |
| 500 | 服务器内部错误 | 联系管理员 |
| 503 | 服务不可用 | 等待服务恢复或联系管理员 |

### 错误响应示例

```json
{
  "detail": "Invalid API Key"
}
```

---

## 代码示例

### Python

```python
import requests

BASE_URL = "http://your-server:8000"
API_KEY = "your-readonly-key"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# 查询张三本周的任务
response = requests.get(
    f"{BASE_URL}/api/tasks/by-engineer",
    headers=headers,
    params={"engineer": "张三"}
)

if response.status_code == 200:
    data = response.json()
    print(f"张三本周有 {data['total']} 个任务")
    for task in data['tasks']:
        print(f"- {task['date']}: {task['task_name']}")
else:
    print(f"请求失败: {response.status_code} - {response.text}")


# 获取统计数据
stats_response = requests.get(
    f"{BASE_URL}/api/tasks/stats",
    headers=headers,
    params={
        "start_date": "2025-10-13",
        "end_date": "2025-10-19"
    }
)

stats = stats_response.json()
print("本周工作量分布:")
for item in stats['by_engineer']:
    print(f"{item['engineer']}: {item['total_tasks']}个任务")
```

### JavaScript / Node.js

```javascript
const axios = require('axios');

const API_BASE = 'http://your-server:8000';
const API_KEY = 'your-readonly-key';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'X-API-Key': API_KEY
  }
});

// 查询工程师任务
async function getEngineerTasks(engineer) {
  try {
    const response = await api.get('/api/tasks/by-engineer', {
      params: { engineer }
    });
    console.log(`${engineer}本周有 ${response.data.total} 个任务`);
    return response.data;
  } catch (error) {
    console.error('请求失败:', error.response?.status, error.response?.data);
  }
}

// 获取统计数据
async function getStats(startDate, endDate) {
  const response = await api.get('/api/tasks/stats', {
    params: { start_date: startDate, end_date: endDate }
  });
  return response.data;
}

// 使用示例
(async () => {
  await getEngineerTasks('张三');

  const stats = await getStats('2025-10-13', '2025-10-19');
  console.log('工作量分布:', stats.by_engineer);
})();
```

---

## 限流规则

**限制**: 每个API Key每分钟最多100次请求

**超限响应**:
```json
HTTP 429 Too Many Requests
{
  "detail": "Rate limit exceeded. Max 100 requests per minute."
}
```

**建议**:
- 使用合理的请求频率
- 实现指数退避重试机制
- 缓存不常变化的数据(如工程师列表)

---

## 在线文档

访问 **Swagger UI** 查看交互式API文档:

**URL**: `http://your-server:8000/docs`

在Swagger UI中可以:
- ✅ 查看所有端点详细定义
- ✅ 在线测试API(需要先配置API Key)
- ✅ 查看请求/响应模型

---

## 技术支持

**遇到问题?**

1. 检查API Key是否正确
2. 查看Swagger文档: `http://your-server:8000/docs`
3. 联系派工系统管理员

**联系方式**:
- 📧 邮件: admin@company.com
- 💬 企业微信: 派工系统管理员
- 📞 电话: 内线123456

---

## 更新日志

**2025-10-20**:
- ✅ 新增6个查询API端点
- ✅ 实现API Key认证
- ✅ 实现限流保护(100次/分钟)
- ✅ 新增健康检查端点
- ✅ 新增请求日志审计

**未来计划**:
- ⏳ 支持Webhook推送(任务变更时主动通知)
- ⏳ 支持批量查询接口
- ⏳ 支持数据导出(Excel/CSV)
