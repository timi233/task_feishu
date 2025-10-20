# 派工系统后端 README

## 项目结构

- `main.py`: 后端服务主入口，使用 FastAPI 构建。
- `requirements.txt`: Python 依赖包列表。

## 环境准备

1.  **安装 Python**: 确保已安装 Python 3.7+。
2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

## 配置说明

在 `main.py` 文件的顶部，有以下配置项需要根据你的飞书应用信息进行修改：

-   `FEISHU_APP_ID`: 你的飞书自建应用的 App ID。
-   `FEISHU_APP_SECRET`: 你的飞书自建应用的 App Secret。
-   `FEISHU_APP_TOKEN`: 你的多维表格的 App Token。
-   `FEISHU_TABLE_ID`: 你的多维表格中具体工作表（Table）的 ID。
-   `TASK_NAME_FIELD`, `ASSIGNEE_FIELD`, `STATUS_FIELD`, `DATE_FIELD`: 你的多维表格中对应列的内部字段名（Field Name）。

**注意**：此版本已移除用户授权流程，改为使用应用身份（Tenant Access Token）直接访问飞书API。请确保你的飞书应用有相应的权限（如 `bitable:app` 和 `bitable:record:read`），并且这些权限已在开发者后台发布。

## 运行服务

在 `backend` 目录下执行以下命令启动后端服务：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

或者直接运行 `main.py`:

```bash
python main.py
```

服务启动后，默认监听在 `http://localhost:8000`。

## API 接口

-   `GET /`: 服务根路径，返回欢迎信息。
-   `GET /api/tasks`: 获取处理后的任务数据，按星期一分组。此接口会自动使用应用身份获取数据。

## 注意事项

1.  **多维表格配置**:
    -   需要确保 `FEISHU_APP_TOKEN` 和 `FEISHU_TABLE_ID` 配置正确。
    -   必须根据你的多维表格字段的实际 `field_name` 修改 `main.py` 顶部的字段名配置。
2.  **应用权限**:
    -   确保飞书应用已申请并发布了访问多维表格所需的权限。
3.  **Tenant Access Token**:
    -   当前后端会自动获取和缓存 `tenant_access_token`。
4.  **前端交互**:
    -   前端可以直接请求 `/api/tasks` 接口获取数据，不再需要处理用户登录流程。