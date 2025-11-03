# 审批表单字段映射

本文档记录两个飞书审批定义的详细字段,以及前端表单字段的映射关系。

生成时间: 2025-10-21

## 1. 公司日常工单 (daily_work)

**审批Code**: `F3E2FECF-0669-4EED-B764-5764DA494C9B`

**审批ID**: `7182219925686140929`

**字段列表** (共19个):

| # | 字段名 | 飞书ID | 类型 | 必填 | 选项/说明 |
|---|--------|--------|------|------|-----------|
| 1 | 产品分类 | widget1650009430450184848162296858 | radioV2 | 否 | IP-Guard/绿盟/爱数/深信服/其他产品/公司事务 |
| 2 | 产品型号 | widget17501252855820001 | input | 否 | - |
| 3 | 工作类型 | widget17501233300350001 | radioV2 | 否 | 售前沟通/部署测试/实施交付/客户培训/渠道培训/测试问题处理/售后问题处理/售后巡检/其他-请在工作内容里注明 |
| 4 | 优先级 | widget1650009430707233634337573427 | radioV2 | 否 | 一般/重要/紧急/非常紧急 |
| 5 | 工作方式 | widget17501273795460001 | radioV2 | 否 | 线上/线下 |
| 6 | 服务开始时间 | widget17553090513020001 | date | 否 | YYYY-MM-DD |
| 7 | 服务开始时间-时间段 | widget17553090644560001 | radioV2 | 否 | 上午/下午 |
| 8 | 服务结束时间 | widget17553090563410001 | date | 否 | YYYY-MM-DD |
| 9 | 服务结束时间-时间段 | widget17553090673240001 | radioV2 | 否 | 上午/下午 |
| 10 | 售后工程师 | widget17501254293910001 | contact | 否 | 联系人选择器 |
| 11 | 工作内容 | widget17553091304870001 | input | 否 | - |
| 12 | 客户公司名称 | widget1650009430661041708057438223 | input | 否 | - |
| 13 | 客户联系人 | widget17218043024090001 | input | 否 | - |
| 14 | 客户联系方式 | widget17555676755350001 | number | 否 | - |
| 15 | 是否有渠道 | widget17218044288600001 | radioV2 | 否 | 是/否 |
| 16 | 渠道名称 | widget17217912950250001 | input | 否 | - |
| 17 | 渠道联系人 | widget17218041850570001 | input | 否 | - |
| 18 | 渠道联系人联系方式 | widget17555677009440001 | number | 否 | - |
| 19 | 工程师身份 | widget17501326783360001 | radioV2 | 否 | 厂家/总代/公司 |

## 2. 爱数原厂派单 (eisoo_vendor)

**审批Code**: `1258F9D1-FFEB-4C1F-A0ED-200A7807261A`

**审批ID**: `7538630060082348033`

**字段列表** (共12个):

| # | 字段名 | 飞书ID | 类型 | 必填 | 选项/说明 |
|---|--------|--------|------|------|-----------|
| 1 | 厂家对接人 | widget17604215175840001 | input | **是** | - |
| 2 | 产品分类 | widget17552252938540001 | radioV2 | 否 | AnyBackup/AnyShare/其他产品 |
| 3 | 工作方式 | widget17552257002060001 | radioV2 | 否 | 线上/线下 |
| 4 | 服务开始时间 | widget17552257384470001 | date | 否 | YYYY-MM-DD |
| 5 | 服务开始时间-时间段 | widget17552257908810001 | radioV2 | 否 | 上午/下午 |
| 6 | 服务结束时间 | widget17552258803190001 | date | 否 | YYYY-MM-DD |
| 7 | 服务结束时间-时间段 | widget17552258908330001 | radioV2 | 否 | 上午/下午 |
| 8 | 售后工程师 | widget17552259047310001 | contact | 否 | 联系人选择器 |
| 9 | 工作内容 | widget17552259222440001 | input | 否 | - |
| 10 | 客户公司名称 | widget17552259414290001 | input | 否 | - |
| 11 | 客户联系人 | widget17552259944390001 | input | 否 | - |
| 12 | 客户联系方式 | widget17552260553850001 | telephone | 否 | - |

## 3. 前端表单字段映射

### 3.1 公司日常工单表单 (DailyWorkForm.js)

前端需要收集的字段(简化版,核心必填字段):

| 前端字段名 | 飞书字段名 | 组件类型 | 必填 | 备注 |
|-----------|-----------|---------|------|------|
| product_category | 产品分类 | select | 否 | |
| product_model | 产品型号 | input | 否 | |
| work_type | 工作类型 | select | 否 | |
| priority | 优先级 | select | **是** | 系统必填 |
| work_mode | 工作方式 | select | 否 | |
| start_date | 服务开始时间 | date | **是** | 系统必填 |
| start_period | 服务开始时间-时间段 | select | 否 | |
| end_date | 服务结束时间 | date | **是** | 系统必填 |
| end_period | 服务结束时间-时间段 | select | 否 | |
| assignee | 售后工程师 | input | **是** | 系统必填 |
| work_content | 工作内容 | textarea | **是** | 系统必填 |
| customer_name | 客户公司名称 | input | **是** | 系统必填 |
| contact_person | 客户联系人 | input | 否 | |
| contact_phone | 客户联系方式 | tel | 否 | |
| has_channel | 是否有渠道 | select | 否 | |
| channel_name | 渠道名称 | input | 否 | 当has_channel=是时显示 |
| channel_contact | 渠道联系人 | input | 否 | 当has_channel=是时显示 |
| channel_phone | 渠道联系人联系方式 | tel | 否 | 当has_channel=是时显示 |
| engineer_role | 工程师身份 | select | 否 | |

### 3.2 爱数原厂派单表单 (EisooVendorForm.js)

前端需要收集的字段:

| 前端字段名 | 飞书字段名 | 组件类型 | 必填 | 备注 |
|-----------|-----------|---------|------|------|
| vendor_contact | 厂家对接人 | input | **是** | 飞书必填 |
| product_category | 产品分类 | select | 否 | |
| work_mode | 工作方式 | select | 否 | |
| start_date | 服务开始时间 | date | **是** | 系统必填 |
| start_period | 服务开始时间-时间段 | select | 否 | |
| end_date | 服务结束时间 | date | **是** | 系统必填 |
| end_period | 服务结束时间-时间段 | select | 否 | |
| assignee | 售后工程师 | input | **是** | 系统必填 |
| work_content | 工作内容 | textarea | **是** | 系统必填 |
| customer_name | 客户公司名称 | input | **是** | 系统必填 |
| contact_person | 客户联系人 | input | 否 | |
| contact_phone | 客户联系方式 | tel | 否 | |

## 4. 后端API提交格式

### 4.1 公司日常工单提交

```json
{
  "approval_type": "daily_work",
  "start_date": "2025-10-21",
  "end_date": "2025-10-22",
  "assignee": "张三",
  "priority": "紧急",
  "customer_name": "阿里巴巴",
  "work_content": "处理服务器故障",
  "extra_fields": {
    "product_category": "爱数",
    "product_model": "AnyBackup F8600",
    "work_type": "售后问题处理",
    "work_mode": "线下",
    "start_period": "上午",
    "end_period": "下午",
    "contact_person": "李四",
    "contact_phone": "13800138000",
    "has_channel": "是",
    "channel_name": "XX渠道",
    "channel_contact": "王五",
    "channel_phone": "13900139000",
    "engineer_role": "公司"
  }
}
```

### 4.2 爱数原厂派单提交

```json
{
  "approval_type": "eisoo_vendor",
  "start_date": "2025-10-21",
  "end_date": "2025-10-22",
  "assignee": "张三",
  "customer_name": "阿里巴巴",
  "work_content": "处理备份故障",
  "extra_fields": {
    "vendor_contact": "爱数技术支持",
    "product_category": "AnyBackup",
    "work_mode": "线上",
    "start_period": "上午",
    "end_period": "下午",
    "contact_person": "李四",
    "contact_phone": "13800138000"
  }
}
```

## 5. 注意事项

1. **时间段字段**: 飞书审批有"服务开始时间-时间段"和"服务结束时间-时间段"两个独立字段,需要在前端表单中体现

2. **联系人字段类型**:
   - 公司日常工单的"售后工程师"是`contact`类型(联系人选择器)
   - 前端简化为文本输入,后端提交时需要转换为飞书user_id

3. **电话字段**:
   - 公司日常工单使用`number`类型
   - 爱数原厂派单使用`telephone`类型
   - 前端统一使用`tel` input类型

4. **必填字段**:
   - 爱数原厂派单只有"厂家对接人"在飞书中是必填
   - 其他必填字段是系统层面的业务要求(如工程师、客户、时间等)

5. **优先级字段映射**:
   - 公司日常工单: 一般/重要/紧急/非常紧急
   - 爱数原厂派单: 没有优先级字段,如需要应从工作类型或其他字段推导

## 6. 环境变量配置

需要在`.env`文件中添加:

```bash
FEISHU_APPROVAL_CODE=F3E2FECF-0669-4EED-B764-5764DA494C9B
FEISHU_APPROVAL_CODE_EISOO=1258F9D1-FFEB-4C1F-A0ED-200A7807261A
```
