# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

飞书派工系统:从飞书多维表格同步任务数据,存储到本地数据库,通过FastAPI后端和React前端展示周任务视图,支持自定义筛选器。

**核心数据流**: 飞书API → 同步脚本 → 数据库(SQLite/MySQL) → FastAPI API → React SPA

**核心功能**:
- 🔄 自动数据同步: 页面打开时立即同步,之后每小时自动同步一次
- 📊 多视图展示: 周视图、月视图、按日期视图、按工程师视图
- ⚡ 手动同步: 用户可随时手动触发数据同步
- 🎛️ 用户控制: 支持开启/关闭自动同步,显示下次同步倒计时
- 🔍 任务筛选: 支持优先级、状态等多维度筛选
- 📈 统计面板: 实时统计不同优先级任务数量
- ✅ **派工管理**(NEW): 基于飞书原生审批的完整派工生命周期管理
  - 新建派工: 创建审批实例并自动流转
  - 修改派工: 撤回旧实例+创建新实例
  - 转交派工: 更改派工人员并通知相关人
  - 关闭派工: 撤回审批实例
  - 完成派工: 标记任务完成状态
  - 查询审批详情: 获取审批流程和时间线

## 常用命令

### 后端开发
```bash
cd backend
pip install -r requirements.txt

# 启动API服务(开发模式)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 手动同步飞书数据到数据库(需要先设置环境变量)
python sync_feishu_to_db.py

# 一次性同步(不启动定时任务)
python sync_once.py

# 数据库调试
python check_db.py              # 查看数据库内容
python check_filter_data.py     # 验证筛选器逻辑
python check_week_data.py       # 检查本周数据
python check_raw_db.py          # 检查feishu_records原始数据
python check_cross_day_tasks.py # 验证跨天任务展开

# 数据库迁移(添加审批字段)
python migrations/add_approval_fields.py
python migrations/add_approval_type_field.py  # 添加工单类型字段

# 测试
pytest test_feishu_approval.py -v  # 测试审批功能
python approval_config.py          # 验证审批配置
```

### 前端开发
```bash
cd frontend
npm install
npm start         # 开发服务器(热重载)
npm run build     # 生产构建
npm test          # 运行测试
```

### Docker部署
```bash
# 确保.env文件包含飞书凭证:
# FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN, FEISHU_TABLE_ID

# SQLite版本(默认)
docker-compose up --build

# MySQL版本
docker-compose -f docker-compose.mysql.yml up --build

# 访问:
# - 后端API: http://localhost:8000
# - 前端界面: http://localhost:8080
```

## 核心架构

### 数据层(`backend/`)
1. **飞书接口封装**
   - `feishu_reader.py`: `FeishuBitableReader`类,管理tenant_access_token,批量拉取记录
   - `feishu_approval.py`: `FeishuApprovalManager`类,封装飞书原生审批API(创建/撤回/查询/抄送)
   - `read_feishu_data.py`: 已弃用,逻辑已整合到`feishu_reader.py`

2. **数据处理管线**
   - `process_feishu_data.py`:
     - `process_feishu_records()`: 将飞书原始字段映射为任务对象
     - 跨天任务展开逻辑(一个飞书记录展开为多条数据库记录)
     - 字段映射常量在文件顶部定义(CUSTOMER_NAME_FIELD, TASK_CONTENT_FIELD, APPROVAL_INSTANCE_FIELD, APPROVAL_STATUS_FIELD等)

3. **数据库抽象**
   - `task_db.py`:
     - 两张主表: `feishu_records`(原始数据) + `tasks`(处理后数据,用于API查询)
     - `current_week_tasks_view`: SQLite视图,动态计算本周任务
     - `save_raw_feishu_records_to_db()`, `save_processed_tasks_to_db()`
     - 数据库路径: `/app/db/tasks.db`(容器内)或`./data/db/tasks.db`(主机)

4. **筛选系统**
   - `task_filter.py`: `TaskFilter`类,从`filter_config.json`加载规则
   - 支持操作符: equals, contains, in, not_empty等(详见`backend/filter_api_docs.md`)
   - `active_filter`决定默认筛选器

5. **API服务**
   - `main.py`: FastAPI应用,CORS已开启
   - 核心端点分为三类:
     - **前端专用**(无需认证): `GET /api/tasks`, `GET /api/filters`, `POST /api/sync`
     - **系统集成**(需要API Key): `GET /api/tasks/by-engineer`, `GET /api/tasks/by-date`, `GET /api/tasks/stats`, `GET /api/tasks/search`, `GET /api/engineers`
     - **派工管理**(需要API Key): `POST /api/approvals`, `PUT /api/approvals/{id}`, `DELETE /api/approvals/{id}`, `POST /api/approvals/{id}/transfer`, `POST /api/approvals/{id}/complete`, `GET /api/approvals/{id}`
   - 响应模型: `TaskGroup`(按星期一到周日分组) + `TaskListResponse`(扁平结构) + `ApprovalDetailResponse`(审批详情)
   - 认证: `auth.py`提供API Key验证,`rate_limit.py`提供限流保护

6. **同步脚本**
   - `sync_feishu_to_db.py`: 定时任务入口(默认60分钟),调用reader→processor→db保存

7. **日志系统**
   - `utils/logging_config.py`: 统一日志配置模块
   - 特性:
     - 环境变量控制: `LOG_LEVEL`(DEBUG/INFO/WARNING/ERROR, 默认INFO)
     - 可选JSON格式: `LOG_FORMAT=json`(用于ELK/Splunk等日志系统)
     - 文件输出: `LOG_FILE=true` + `LOG_DIR=./logs`
     - 自动日志轮转: 每天一个文件,保留30天
     - 集中配置: 避免多个文件重复配置logging.basicConfig
   - 使用:
     ```python
     # main.py中统一配置(仅一次)
     from utils.logging_config import setup_logging
     setup_logging(app_name="feishu_task")

     # 其他模块中直接使用
     logger = logging.getLogger(__name__)
     ```

8. **配置管理**
   - `config.py`: 统一配置管理模块
   - 特性:
     - 集中管理29个环境变量
     - 配置分组: FeishuConfig/DatabaseConfig/AuthConfig/LoggingConfig/ServerConfig
     - 类型注解和验证
     - 配置摘要输出（启动时）
     - 处理空字符串环境变量
   - 使用:
     ```python
     from config import settings

     # 访问配置
     app_id = settings.feishu.app_id
     db_file = settings.database.file_path
     api_keys = settings.auth.api_keys
     log_level = settings.logging.level
     origins = settings.server.allowed_origins
     ```

### 前端层(`frontend/`)
- React 18 + Create React App
- `src/App.js`: 主组件,任务卡片视图,周视图切换
- `index.html`: 静态回退页面(风格1)
- 环境变量: 使用`REACT_APP_*`前缀

### 部署配置
- `docker-compose.yml`: SQLite版本,挂载`./data/db`持久化
- `docker-compose.mysql.yml`: MySQL版本
- `Dockerfile`: Python 3.9镜像,安装依赖+同步脚本+API服务
- `dd/Dockerfile.frontend`: Nginx托管React构建产物

## 关键设计决策

1. **两阶段存储**:
   - `feishu_records`保留原始飞书数据(fields序列化为JSON)
   - `tasks`表存储展平后的任务记录,跨天任务会产生多条记录(同一`record_id`但不同`date`)

2. **跨天任务处理**:
   - 飞书的一条记录如果`服务开始时间`到`服务结束时间`跨多天,会在`tasks`表中展开为每天一条记录
   - `UNIQUE(record_id, date)`约束防止重复

3. **周视图逻辑**:
   - 前端默认显示本周(周一到周日,含周末)
   - 后端`get_current_week_dates()`计算日期范围
   - SQLite视图用`DATE('now', 'weekday 1', '-7 days')`计算本周一

4. **筛选器架构**:
   - 后端从数据库拉取所有任务,在内存中应用筛选规则
   - 筛选后的任务按日期范围重新分组返回给前端
   - 修改筛选器: 编辑`backend/filter_config.json` → 重启服务或挂载卷热更新

## 环境变量与配置

### 必须的飞书凭证(`.env`或环境变量)
```
# 多维表格配置
FEISHU_APP_ID=cli_xxx          # 飞书应用ID
FEISHU_APP_SECRET=xxx          # 飞书应用密钥
FEISHU_APP_TOKEN=xxx           # 多维表格App Token
FEISHU_TABLE_ID=tblxxx         # 表格中的具体表ID

# 审批配置(可选,用于派工管理功能)
FEISHU_APPROVAL_CODE=4202AD96-9EC1-4284-9C48-B923CDC4F30B       # 公司日常工单审批Code
FEISHU_APPROVAL_CODE_EISOO=1258F9D1-FFEB-4C1F-A0ED-200A7807261A  # 爱数原厂派单审批Code
FEISHU_APPROVAL_ADMIN_USER_ID=f7cb567e                          # 默认发起人ID
```

### API认证配置(可选,生产环境推荐)
```
API_KEYS=admin-key-1,admin-key-2              # 管理员密钥(读写权限)
READONLY_API_KEYS=readonly-key-1,readonly-key-2  # 只读密钥(供其他系统调用)
API_RATE_LIMIT=100                            # 每分钟请求限制(默认100)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080  # CORS允许的来源
LOG_LEVEL=INFO                                # 日志级别(DEBUG/INFO/WARNING/ERROR)
```

**注意**:
- 如果不配置`API_KEYS`和`READONLY_API_KEYS`,系统会使用默认开发密钥(不适合生产环境)
- `/api/tasks`等前端调用的端点不需要认证,`/api/tasks/by-engineer`等供其他系统调用的端点需要`X-API-Key`头

### 字段映射配置
在`process_feishu_data.py`顶部定义飞书字段名映射:
```python
CUSTOMER_NAME_FIELD = "客户公司名称"
TASK_CONTENT_FIELD = "工作内容"
ASSIGNEE_FIELD = "售后工程师"
PRIORITY_FIELD = "优先级"
APPLICATION_STATUS_FIELD = "申请状态"
APPROVAL_INSTANCE_FIELD = "审批实例ID"  # 关联审批实例的字段
APPROVAL_STATUS_FIELD = "审批状态"      # 审批状态字段
START_DATE_FIELD = "服务开始时间"        # 毫秒时间戳
END_DATE_FIELD = "服务结束时间"
```

**修改规则**: 如果飞书表格字段名改变,只需更新这些常量,无需修改处理逻辑。

## 调试工作流

1. **数据同步问题**:
   ```bash
   python check_raw_db.py         # 检查feishu_records表是否有数据
   python check_db.py             # 检查tasks表是否有数据
   python check_date_fields.py    # 验证日期字段解析
   ```

2. **筛选器问题**:
   ```bash
   python check_filter_data.py    # 打印筛选前后的任务数量
   python test_filter.py          # 单元测试筛选器逻辑
   ```

3. **API问题**:
   - 直接访问`http://localhost:8000/docs`查看Swagger文档
   - 测试端点: `curl http://localhost:8000/api/tasks`

4. **跨天任务问题**:
   ```bash
   python check_cross_day_tasks.py  # 列出展开后的跨天任务记录
   ```

## 测试策略

- **后端测试**: `backend/test_*.py`文件,使用`pytest backend`批量运行(需先同步数据)
- **前端测试**: `npm test`启动Jest,测试文件命名为`*.test.js`
- **集成测试**: 启动Docker容器后,通过前端UI验证数据流

## 安全注意事项

- **永远不要**将飞书凭证硬编码到代码中,仅通过环境变量传递
- `data/tasks.db`包含生产数据,不要提交到版本控制
- Docker部署时使用`.env.local`覆盖本地配置,该文件已在`.gitignore`中排除
- CORS配置当前为`allow_origins=["*"]`,生产环境应限制为前端域名

## 代码风格约定

- **Python**: PEP 8,4空格缩进,snake_case命名
- **JavaScript**: ESLint + Prettier(react-scripts默认),camelCase文件名
- **提交信息**: 使用Conventional Commits格式(`feat:`, `fix:`, `refactor:`等)

## 系统集成指南

### 使用API访问任务数据

其他系统可通过以下端点访问任务数据(需要在请求头中提供`X-API-Key`):

```bash
# 获取某工程师本周任务
curl -H "X-API-Key: your-readonly-key" \
  "http://localhost:8000/api/tasks/by-engineer?engineer=张三&start_date=2025-10-13&end_date=2025-10-19"

# 获取某天所有任务
curl -H "X-API-Key: your-readonly-key" \
  "http://localhost:8000/api/tasks/by-date?date=2025-10-15"

# 获取统计数据
curl -H "X-API-Key: your-readonly-key" \
  "http://localhost:8000/api/tasks/stats?start_date=2025-10-13&end_date=2025-10-19"

# 搜索任务
curl -H "X-API-Key: your-readonly-key" \
  "http://localhost:8000/api/tasks/search?keyword=阿里巴巴&limit=50"

# 获取工程师列表
curl -H "X-API-Key: your-readonly-key" \
  "http://localhost:8000/api/engineers"
```

### 派工管理API(基于飞书原生审批)

**支持两种工单类型**:
1. `daily_work`: 公司日常工单(默认)
2. `eisoo_vendor`: 爱数原厂派单

```bash
# 获取可用工单类型
curl -H "X-API-Key: admin-key-1" \
  http://localhost:8000/api/approvals/types

# 新建日常工单(默认类型)
curl -X POST http://localhost:8000/api/approvals \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_type": "daily_work",
    "task_name": "网络故障排查",
    "assignee": "张三",
    "priority": "紧急",
    "start_date": "2025-10-22",
    "end_date": "2025-10-23",
    "user_id": "f7cb567e"
  }'

# 新建爱数原厂派单
curl -X POST http://localhost:8000/api/approvals \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_type": "eisoo_vendor",
    "customer_name": "XX科技公司",
    "issue_type": "硬件故障",
    "urgency": "紧急",
    "contact_person": "李四",
    "contact_phone": "13800138000",
    "assignee": "王五",
    "start_date": "2025-10-22",
    "end_date": "2025-10-23",
    "user_id": "f7cb567e"
  }'

# 修改派工
curl -X PUT http://localhost:8000/api/approvals/{instance_code} \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "assignee": "李四",
    "user_id": "f7cb567e"
  }'

# 转交派工
curl -X POST http://localhost:8000/api/approvals/{instance_code}/transfer \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "new_assignee": "王五",
    "user_id": "f7cb567e",
    "reason": "临时调整"
  }'

# 完成派工
curl -X POST http://localhost:8000/api/approvals/{instance_code}/complete \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "f7cb567e",
    "completion_note": "任务已完成"
  }'

# 关闭派工
curl -X DELETE http://localhost:8000/api/approvals/{instance_code} \
  -H "X-API-Key: admin-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "f7cb567e",
    "reason": "客户取消"
  }'

# 查询审批详情
curl -H "X-API-Key: admin-key-1" \
  http://localhost:8000/api/approvals/{instance_code}
```

详细API文档可访问: `http://localhost:8000/docs`(Swagger UI)

### 触发手动同步

```bash
# 前端用户点击"同步"按钮或其他系统触发
curl -X POST -H "X-API-Key: your-readonly-key" \
  "http://localhost:8000/api/sync"
```

## 性能考虑

1. **数据库查询**: SQLite适合中小规模(<10万条任务),大规模建议切换到MySQL
2. **筛选性能**: 当前在内存中筛选,任务量大时考虑改为SQL WHERE子句
3. **定时同步**: 默认60分钟,可通过修改`sync_feishu_to_db.py`调整间隔
4. **API限流**: 默认100次/分钟,生产环境可通过`API_RATE_LIMIT`环境变量调整

## 故障排查清单

1. **前端显示空白**: 检查后端是否启动(`curl http://localhost:8000/health`)
2. **数据不更新**: 检查同步日志,验证飞书凭证是否过期
3. **筛选器不生效**: 检查`filter_config.json`语法,验证`active_filter`设置
4. **跨天任务显示异常**: 运行`python check_cross_day_tasks.py`验证展开逻辑
5. **API认证失败**: 检查环境变量`API_KEYS`/`READONLY_API_KEYS`是否配置正确
