# Identity Hub Docker配置文件模板

本文档提供Identity Hub Docker部署所需的配置文件模板，可以直接复制使用。

---

## 📁 文件清单

需要创建以下文件：
1. `Dockerfile` - Identity Hub后端镜像构建
2. `docker-compose.yml` - Docker编排配置
3. `.dockerignore` - Docker构建忽略文件
4. `start.sh` - 启动脚本（可选）
5. `.env.production` - 生产环境配置模板

---

## 1. Dockerfile

**文件路径**: `/home/jian/code/identity-hub/Dockerfile`

```dockerfile
# Identity Hub Dockerfile
# 基于Python 3.11官方镜像

FROM python:3.11-slim

# 设置标签
LABEL maintainer="Identity Hub Team"
LABEL version="1.0"
LABEL description="Identity Hub - 统一身份认证平台"

# 设置时区为北京时间
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 设置工作目录
WORKDIR /app

# 安装系统依赖（如果需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY backend/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 创建必要的目录
RUN mkdir -p /app/data

# 设置权限（如果需要）
# RUN useradd -m -u 1000 identityhub && chown -R identityhub:identityhub /app
# USER identityhub

# 暴露端口
EXPOSE 9000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/health').read()" || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
```

---

## 2. docker-compose.yml

**文件路径**: `/home/jian/code/identity-hub/docker-compose.yml`

```yaml
# Identity Hub Docker Compose配置
# 版本: v1.0

version: '3.8'

services:
  # Identity Hub主服务
  identity-hub:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: identity-hub
    hostname: identity-hub
    ports:
      - "9000:9000"  # Identity Hub主服务端口
    env_file:
      - .env  # 从.env文件加载所有环境变量
    environment:
      # Docker环境特定配置（覆盖.env中的配置）
      - HOST=0.0.0.0
      - PORT=9000
      # 生产环境可以设置更严格的日志级别
      # - LOG_LEVEL=WARNING
    volumes:
      # 持久化数据库文件
      - ./data:/app/data
      # 可选: 挂载日志目录
      # - ./logs:/app/logs
    networks:
      - identity-hub-network
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:9000/health').read()"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    # 资源限制（可选，生产环境推荐）
    # deploy:
    #   resources:
    #     limits:
    #       cpus: '1.0'
    #       memory: 512M
    #     reservations:
    #       cpus: '0.5'
    #       memory: 256M

  # 可选: PostgreSQL数据库（替代SQLite）
  # postgres:
  #   image: postgres:15-alpine
  #   container_name: identity-hub-postgres
  #   environment:
  #     - POSTGRES_DB=identity_hub
  #     - POSTGRES_USER=identity_hub
  #     - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   networks:
  #     - identity-hub-network
  #   restart: unless-stopped

  # 可选: Redis缓存
  # redis:
  #   image: redis:7-alpine
  #   container_name: identity-hub-redis
  #   networks:
  #     - identity-hub-network
  #   restart: unless-stopped

  # 可选: Nginx反向代理（用于HTTPS）
  # nginx:
  #   image: nginx:alpine
  #   container_name: identity-hub-nginx
  #   ports:
  #     - "443:443"
  #     - "80:80"
  #   volumes:
  #     - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
  #     - ./nginx/ssl:/etc/nginx/ssl:ro
  #   depends_on:
  #     - identity-hub
  #   networks:
  #     - identity-hub-network
  #   restart: unless-stopped

networks:
  identity-hub-network:
    driver: bridge

# volumes:
#   postgres_data:
```

---

## 3. .dockerignore

**文件路径**: `/home/jian/code/identity-hub/.dockerignore`

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Git
.git/
.gitignore
.gitattributes

# 文档
docs/
README.md
*.md

# 测试
tests/
*.test.py
.pytest_cache/
.coverage

# 日志
*.log
logs/

# 环境配置
.env.example
.env.local
.env.development

# 其他
.DS_Store
Thumbs.db
```

---

## 4. start.sh（可选）

**文件路径**: `/home/jian/code/identity-hub/start.sh`

如果需要在启动前执行一些初始化操作，可以使用启动脚本：

```bash
#!/bin/bash
# Identity Hub启动脚本

set -e

echo "🚀 Starting Identity Hub..."

# 1. 等待数据库就绪（如果使用PostgreSQL）
# if [ "$DATABASE_TYPE" = "postgresql" ]; then
#   echo "⏳ Waiting for PostgreSQL..."
#   while ! nc -z postgres 5432; do
#     sleep 1
#   done
#   echo "✅ PostgreSQL is ready"
# fi

# 2. 运行数据库迁移（如果有）
# echo "📊 Running database migrations..."
# alembic upgrade head

# 3. 创建初始数据（可选）
# python -c "from database import init_db; init_db()"

# 4. 启动应用
echo "✅ Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 9000
```

修改Dockerfile使用启动脚本：

```dockerfile
# 复制启动脚本
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 修改启动命令
CMD ["/app/start.sh"]
```

---

## 5. .env.production（生产环境模板）

**文件路径**: `/home/jian/code/identity-hub/.env.production`

```bash
# ========================================
# Identity Hub 生产环境配置模板
# ========================================
# 使用方法:
# 1. 复制此文件为 .env
# 2. 填写实际的配置值
# 3. 不要将 .env 提交到版本控制
# ========================================

# === 安全配置 ===
# JWT签名密钥（必须修改！使用: openssl rand -hex 32）
SECRET_KEY=your-secret-key-here-change-this

# === 飞书身份源配置 ===
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
# ⚠️ 迁移时必须修改为新服务器IP
FEISHU_REDIRECT_URI=http://NEW_SERVER_IP:9000/callback

# === 数据库配置 ===
# SQLite（默认）
DATABASE_URL=sqlite:///./data/identity-hub.db

# PostgreSQL（生产环境推荐）
# DATABASE_URL=postgresql://identity_hub:password@postgres:5432/identity_hub

# === 服务器配置 ===
HOST=0.0.0.0
PORT=9000

# === CORS配置 ===
# ⚠️ 迁移时必须修改，添加所有客户端系统的地址
ALLOWED_ORIGINS=http://NEW_IDENTITY_HUB_IP:9000,http://DISPATCH_SYSTEM_IP:8080,http://localhost:3000

# === 日志配置 ===
LOG_LEVEL=INFO
# 生产环境可设为 WARNING 或 ERROR

# === Redis配置（可选） ===
# REDIS_URL=redis://redis:6379/0

# === 其他配置 ===
# Session超时时间（秒）
# SESSION_TIMEOUT=3600

# OAuth token有效期（秒）
# ACCESS_TOKEN_EXPIRE=3600
# REFRESH_TOKEN_EXPIRE=2592000
```

---

## 6. Nginx配置（HTTPS支持，可选）

**文件路径**: `/home/jian/code/identity-hub/nginx/nginx.conf`

```nginx
events {
    worker_connections 1024;
}

http {
    upstream identity_hub {
        server identity-hub:9000;
    }

    # HTTP服务器（重定向到HTTPS）
    server {
        listen 80;
        server_name identity-hub.example.com;

        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS服务器
    server {
        listen 443 ssl http2;
        server_name identity-hub.example.com;

        # SSL证书
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # SSL配置
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # 安全头
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;

        # 反向代理到Identity Hub
        location / {
            proxy_pass http://identity_hub;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

---

## 使用说明

### 快速开始

```bash
# 1. 在旧服务器上创建Docker配置文件
cd /home/jian/code/identity-hub

# 创建Dockerfile（复制上面的内容）
nano Dockerfile

# 创建docker-compose.yml
nano docker-compose.yml

# 创建.dockerignore
nano .dockerignore

# 2. 修改.env配置
cp .env .env.backup
nano .env
# 确保所有配置正确

# 3. 测试构建
docker-compose build

# 4. 本地测试运行
docker-compose up

# 5. 确认无误后，停止容器
docker-compose down

# 6. 打包迁移
tar -czf ~/identity-hub-docker-migration.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  backend/ data/ .env Dockerfile docker-compose.yml .dockerignore
```

### 在新服务器上部署

```bash
# 1. 解压文件
mkdir ~/identity-hub
cd ~/identity-hub
tar -xzf /tmp/identity-hub-docker-migration.tar.gz

# 2. 修改配置（替换IP地址）
sed -i 's/10.242.94.9/NEW_SERVER_IP/g' .env

# 3. 构建并启动
docker-compose build
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 验证
curl http://localhost:9000/health
```

---

## 配置优化建议

### 1. 资源限制（生产环境）

在docker-compose.yml中添加资源限制：

```yaml
services:
  identity-hub:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### 2. 日志轮转

添加日志配置：

```yaml
services:
  identity-hub:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 3. 网络隔离

为不同环境创建独立网络：

```yaml
networks:
  identity-hub-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/16
```

### 4. 数据持久化

使用命名卷而不是绑定挂载：

```yaml
volumes:
  identity_hub_data:

services:
  identity-hub:
    volumes:
      - identity_hub_data:/app/data
```

---

## 常见问题

### Q1: 如何查看容器内的文件？

```bash
docker exec -it identity-hub ls -la /app/data/
```

### Q2: 如何进入容器调试？

```bash
docker exec -it identity-hub bash
```

### Q3: 如何重新构建镜像？

```bash
docker-compose build --no-cache
docker-compose up -d
```

### Q4: 如何导出镜像？

```bash
docker save identity-hub_identity-hub:latest -o identity-hub-image.tar
```

### Q5: 如何导入镜像？

```bash
docker load -i identity-hub-image.tar
```

---

## 相关文档

- [Identity Hub迁移手册](IDENTITY_HUB_MIGRATION_GUIDE.md)
- [派工系统迁移手册](DOCKER_MIGRATION_GUIDE.md)

---

**文档版本**: v1.0
**最后更新**: 2025-11-04
