# 原生审批实例方法总结

## 核心概念
- **审批定义**：所有原生审批实例均基于既有的审批定义创建，必须预先在审批中心配置表单结构与审批流程。
- **实例唯一标识 Instance Code**：每个实例都有唯一的 `instance_code` 以便查询与幂等处理，可在创建实例成功返回值或批量查询接口中获取。
- **实例状态流转**：实例会在 `PENDING`（审批中）、`APPROVED`（通过）、`REJECTED`（拒绝）、`CANCELED`（撤回）、`DELETED`（删除）之间转换，用于判断审批进度与终态。

## 常用操作能力
- **创建**：调用“创建审批实例”接口提交表单数据与流程配置，从返回值中记录 `instance_code` 与 `uuid` 幂等信息。
- **撤回/撤销**：当发起人取消申请时调用“撤回审批实例”；系统修改场景可使用 `modified_instance_code` 或 `reverted_instance_code` 关联原单据。
- **抄送与查看流程**：使用“抄送审批实例”添加关注人；需提前调用“预览审批流程”确认节点与审批人信息。
- **查询**：
  - 通过“获取单个审批实例详情”拉取结构化信息（字段、任务、评论、时间线等）。
  - 结合“批量获取审批实例 ID”按时间段分页检索历史实例。

## 关键字段说明
- `instance_code`：审批实例唯一标识。
- `approval_code`：实例所属审批定义标识。
- `approval_name`：审批名称/标题。
- `start_time`、`end_time`：毫秒时间戳表示的创建与结束时间。
- `serial_number`：审批单编号，便于业务对账。
- `user_id` / `open_id`：发起人身份，需结合“用户身份概述”选择 ID 类型。
- `department_id`：发起人所属部门 ID。
- `status`：实例当前状态枚举。
- `uuid`：客户端自定义幂等键，防止重复创建。
- `form`：提交表单内容的 JSON 字符串（与审批定义控件一一对应）。
- `task_list`：审批节点任务数组，包含节点 ID、审批人、状态等。
- `comment_list`：审批过程中的评论列表。
- `timeline`：实例流转动态，记录动作类型、时间、操作者及抄送信息。

## 使用建议
- 在创建实例前缓存审批定义的表单与流程元数据，确保字段赋值顺序与类型匹配。
- 结合 `instance_code` 与 `uuid` 做防重校验，避免网络重试导致重复单据。
- 监控状态变化并同步至业务系统；对终态（通过/拒绝/撤回/删除）触发相应业务回调。
- 查询接口返回的 `task_list`、`comment_list`、`timeline` 可用于构建可视化审批详情或审计日志。

> 参考文档：飞书开放平台《原生审批实例概述》：https://open.feishu.cn/document/server-docs/approval-v4/instance/overview-approval-instance

## 常见接口示例

### 创建审批实例 (POST /open-apis/approval/v4/instances)
**请求示例**
```bash
curl -X POST 'https://open.feishu.cn/open-apis/approval/v4/instances' \
  -H 'Authorization: Bearer <tenant_access_token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "approval_code": "4202AD96-9EC1-4284-9C48-B923CDC4F30B",
    "user_id": "f7cb567e",
    "department_id": "od-8ec33ffec336c3a39a278bc25e931676",
    "form": "[{\"id\":\"widget1\",\"type\":\"input\",\"value\":\"预算申请\"},{\"id\":\"widget2\",\"type\":\"dateInterval\",\"value\":{\"start\":\"2019-10-01T08:12:01+08:00\",\"end\":\"2019-10-02T08:12:01+08:00\",\"interval\":2.0}}]",
    "uuid": "7C468A54-8745-2245-9675-08B7C63E7A87"
  }'
```
**响应示例**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "instance_code": "81D31358-93AF-92D6-7425-01A5D67C4E71"
  }
}
```

### 撤回审批实例 (POST /open-apis/approval/v4/instances/cancel)
**请求示例**
```bash
curl -X POST 'https://open.feishu.cn/open-apis/approval/v4/instances/cancel?user_id_type=open_id' \
  -H 'Authorization: Bearer <tenant_access_token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "approval_code": "7C468A54-8745-2245-9675-08B7C63E7A85",
    "instance_code": "81D31358-93AF-92D6-7425-01A5D67C4E71",
    "user_id": "f7cb567e"
  }'
```
**响应示例**
```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

### 抄送审批实例 (POST /open-apis/approval/v4/instances/cc)
**请求示例**
```bash
curl -X POST 'https://open.feishu.cn/open-apis/approval/v4/instances/cc?user_id_type=open_id' \
  -H 'Authorization: Bearer <tenant_access_token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "approval_code": "7C468A54-8745-2245-9675-08B7C63E7A85",
    "instance_code": "81D31358-93AF-92D6-7425-01A5D67C4E71",
    "user_id": "f7cb567e",
    "cc_user_ids": ["ou_123456"],
    "comment": "审批已提交，请关注进度"
  }'
```
**响应示例**
```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

### 预览审批流程 (POST /open-apis/approval/v4/instances/preview)
**创建前预览请求示例**
```json
{
  "approval_code": "C2CAAA90-70D9-3214-906B-B6FFF947F00D",
  "user_id": "f7cb567e",
  "department_id": "od-8ec33ffec336c3a39a278bc25e931676",
  "form": "[{\"id\":\"widget16256287451710001\",\"type\":\"number\",\"value\":\"43\"}]"
}
```
**实例中节点预览请求示例**
```json
{
  "instance_code": "12345CA6-97AC-32BB-8231-47C33FFFCCFD",
  "user_id": "f7cb567e",
  "task_id": "6982332863116876308"
}
```
**响应片段示例**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "preview_nodes": [
      {
        "node_id": "b078ffd28db767c502ac367053f6e0ac",
        "node_name": "发起",
        "user_id_list": ["ffffffff"],
        "node_type": "START"
      },
      {
        "node_id": "e6ce10282a3cc3bf4a408feffd678dcf",
        "node_name": "审批",
        "node_type": "AND",
        "user_id_list": ["ffffffff"],
        "is_empty_logic": false,
        "has_cc_type_free": false
      }
    ]
  }
}
```

### 获取单个审批实例详情 (GET /open-apis/approval/v4/instances/{instance_code})
**请求示例**
```bash
curl -X GET 'https://open.feishu.cn/open-apis/approval/v4/instances/81D31358-93AF-92D6-7425-01A5D67C4E71?locale=zh-CN&user_id=f7cb567e&user_id_type=user_id' \
  -H 'Authorization: Bearer <tenant_access_token>'
```
**响应片段示例**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "approval_name": "Payment",
    "status": "PENDING",
    "user_id": "f3ta757q",
    "form": "[{\"id\":\"widget1\",\"type\":\"textarea\",\"value\":\"aaaa\"}]",
    "task_list": [
      {
        "id": "1234",
        "user_id": "f7cb567e",
        "status": "PENDING",
        "node_id": "46e6d96cfa756980907209209ec03b64"
      }
    ],
    "timeline": [
      {
        "type": "PASS",
        "create_time": "1564590532967",
        "task_id": "1234"
      }
    ]
  }
}
```

### 批量获取审批实例 ID (GET /open-apis/approval/v4/instances)
**请求示例**
```bash
curl -X GET 'https://open.feishu.cn/open-apis/approval/v4/instances?approval_code=7C468A54-8745-2245-9675-08B7C63E7A85&start_time=1567690398020&end_time=1567693998020&page_size=100&page_token=nF1ZXJ5VGhlbkZldGNoCgAAAAAA6PZwFmUzSldvTC1yU' \
  -H 'Authorization: Bearer <tenant_access_token>'
```
**响应示例**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "instance_code_list": [
      "357C21A0-2069-4F6B-955F-1DFBE6710C51"
    ],
    "page_token": "nF1ZXJ5VGhlbkZldGNoCgAAAAAA6PZwFmUzSldvTC1yU",
    "has_more": false
  }
}
```
