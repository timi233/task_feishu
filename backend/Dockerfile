# task_feishu/backend/Dockerfile

# 使用Python官方镜像作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
# 使用--no-cache-dir减少镜像大小
# 使用--upgrade pip确保pip是最新版本
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端代码
# 使用.dockerignore来排除不必要的文件
COPY . .

# 创建目录用于存放静态文件（如果需要）
RUN mkdir -p static

# 确保数据库文件在容器重启后能持久化（通过挂载卷实现）
# RUN touch tasks.db

# 暴露端口 (后端API)
EXPOSE 8000

# 定义环境变量 (可以在运行时通过 -e 参数覆盖)
# 这些是示例值，实际部署时需要替换为真实的值
ENV FEISHU_APP_ID=your_app_id_here
ENV FEISHU_APP_SECRET=your_app_secret_here
ENV FEISHU_APP_TOKEN=your_app_token_here
ENV FEISHU_TABLE_ID=your_table_id_here
ENV BACKEND_PORT=8000

# 容器启动时执行的命令
# 1. 启动后端API服务 (使用Uvicorn)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]