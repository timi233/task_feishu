# 前端独立部署说明

本文档说明了如何在其他服务器上使用前端容器环境。

## 文件传输

1. 将 `task_feishu.tar.gz` 文件传输到目标服务器：
   ```bash
   scp task_feishu.tar.gz user@your-server-ip:/path/to/destination/
   ```

## 在目标服务器上的部署步骤

1. 解压文件：
   ```bash
   tar -xzf task_feishu.tar.gz
   cd Task_feishu
   ```

2. 配置环境变量：
   创建 `.env` 文件并设置必要的环境变量：
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入实际的飞书应用配置
   ```

3. 构建并启动容器：
   ```bash
   docker-compose up --build -d
   ```

4. 访问应用：
   - 前端: http://your-server-ip:8080
   - 后端API: http://your-server-ip:8000

## 端口配置

- 前端通过Nginx运行在端口8080
- 后端API直接暴露在端口8000

## 自定义配置

1. 如需修改端口映射，在 `docker-compose.yml` 中调整 ports 配置
2. 如需修改Nginx配置，编辑 `dd/nginx.conf` 文件然后重新构建镜像

## 停止服务

```bash
docker-compose down
```