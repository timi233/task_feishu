# task_feishu/Dockerfile

# 使用Python官方镜像作为基础镜像
FROM python:3.11-slim

# 设置时区为 Asia/Shanghai (北京时间)
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 设置工作目录
WORKDIR /app

# 复制后端依赖文件
COPY backend/requirements.txt .

# 安装Python依赖
# 使用--no-cache-dir减少镜像大小
# 使用--upgrade pip确保pip是最新版本
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 创建目录用于存放前端静态文件
RUN mkdir -p static db

# 复制前端文件到后端的static目录
COPY frontend/index.html ./static/

# 复制启动脚本
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 确保数据库文件在容器重启后能持久化（通过挂载卷实现）
# RUN touch tasks.db

# 暴露端口 (后端API)
EXPOSE 8000

# 定义环境变量 (可以在运行时通过 -e 参数覆盖)
# 这些是示例值，实际部署时需要替换为真实的值
# ENV FEISHU_APP_ID=your_app_id_here
# ENV FEISHU_APP_SECRET=your_app_secret_here
# ENV FEISHU_APP_TOKEN=your_app_token_here
# ENV FEISHU_TABLE_ID=your_table_id_here
# ENV BACKEND_PORT=8000

# 容器启动时执行的命令
# 1. 启动后端API服务 (使用Uvicorn)
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["/app/start.sh"]
