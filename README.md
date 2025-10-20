# 派工系统 Docker 部署指南

本项目采用 Docker 进行容器化部署，使用 Docker Compose 进行编排。

## 目录结构

```
task_feishu/
├── backend/          # 后端代码
├── frontend/         # 前端代码
├── data/             # (运行时创建) 用于持久化存储 SQLite 数据库文件
├── Dockerfile        # Docker 构建文件
├── docker-compose.yml # Docker Compose 编排文件
└── .dockerignore     # Docker 忽略文件
```

## 构建和运行

1.  **设置环境变量**：
    在运行 `docker-compose` 命令之前，需要设置飞书应用的环境变量。
    可以通过以下方式设置：
    *   **方式一：在终端中导出环境变量**
        ```bash
        export FEISHU_APP_ID=your_actual_app_id
        export FEISHU_APP_SECRET=your_actual_app_secret
        export FEISHU_APP_TOKEN=your_actual_app_token
        export FEISHU_TABLE_ID=your_actual_table_id
        ```
    *   **方式二：创建 `.env` 文件**
        在 `task_feishu` 目录下创建一个 `.env` 文件，并添加以下内容：
        ```
        FEISHU_APP_ID=your_actual_app_id
        FEISHU_APP_SECRET=your_actual_app_secret
        FEISHU_APP_TOKEN=your_actual_app_token
        FEISHU_TABLE_ID=your_actual_table_id
        ```

2.  **构建镜像**：
    ```bash
    cd task_feishu
    docker-compose build
    ```

3.  **启动服务**：
    ```bash
    docker-compose up
    ```
    或者在后台运行：
    ```bash
    docker-compose up -d
    ```

4.  **访问应用**：
    *   后端API: `http://localhost:8000/api/tasks`
    *   前端页面: `http://localhost:8000/static/index.html`

5.  **停止服务**：
    ```bash
    docker-compose down
    ```

## 数据持久化

SQLite 数据库文件 `tasks.db` 会保存在主机的 `task_feishu/data` 目录中，以确保容器重启或删除后数据不会丢失。

## 环境变量

| 变量名 | 描述 | 默认值 |
| :--- | :--- | :--- |
| `FEISHU_APP_ID` | 飞书应用的 App ID | `your_app_id_here` |
| `FEISHU_APP_SECRET` | 飞书应用的 App Secret | `your_app_secret_here` |
| `FEISHU_APP_TOKEN` | 飞书多维表格的 App Token | `your_app_token_here` |
| `FEISHU_TABLE_ID` | 飞书多维表格中具体表的 ID | `your_table_id_here` |
| `BACKEND_PORT` | 后端服务监听的端口 | `8000` |