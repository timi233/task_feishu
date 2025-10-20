# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

飞书派工系统:从飞书多维表格同步任务数据,存储到本地数据库,通过FastAPI后端和React前端展示周任务视图,支持自定义筛选器。

**核心数据流**: 飞书API → 同步脚本 → 数据库(SQLite/MySQL) → FastAPI API → React SPA

## 常用命令

### 后端开发
```bash
cd backend
pip install -r requirements.txt

# 启动API服务(开发模式)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 手动同步飞书数据到数据库(需要先设置环境变量)
python sync_feishu_to_db.py

# 数据库调试
python check_db.py              # 查看数据库内容
python check_filter_data.py     # 验证筛选器逻辑
python check_week_data.py       # 检查本周数据
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
   - `read_feishu_data.py`: 已弃用,逻辑已整合到`feishu_reader.py`

2. **数据处理管线**
   - `process_feishu_data.py`:
     - `process_feishu_records()`: 将飞书原始字段映射为任务对象
     - 跨天任务展开逻辑(一个飞书记录展开为多条数据库记录)
     - 字段映射常量在文件顶部定义(CUSTOMER_NAME_FIELD, TASK_CONTENT_FIELD等)

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
   - 核心端点: `GET /api/tasks?start_date=&end_date=&filter_name=`
   - 响应模型: `TaskGroup`(按星期一到周日分组)

6. **同步脚本**
   - `sync_feishu_to_db.py`: 定时任务入口(默认60分钟),调用reader→processor→db保存

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
FEISHU_APP_ID=cli_xxx          # 飞书应用ID
FEISHU_APP_SECRET=xxx          # 飞书应用密钥
FEISHU_APP_TOKEN=xxx           # 多维表格App Token
FEISHU_TABLE_ID=tblxxx         # 表格中的具体表ID
```

### 字段映射配置
在`process_feishu_data.py`顶部定义飞书字段名映射:
```python
CUSTOMER_NAME_FIELD = "客户公司名称"
TASK_CONTENT_FIELD = "工作内容"
ASSIGNEE_FIELD = "售后工程师"
PRIORITY_FIELD = "优先级"
APPLICATION_STATUS_FIELD = "申请状态"
START_DATE_FIELD = "服务开始时间"  # 毫秒时间戳
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
