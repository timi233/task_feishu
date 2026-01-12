# 前端独立部署说明

本文档说明了如何在其他服务器上独立部署前端服务（不包含后端）。

## 文件传输

1. 将 `task_feishu_frontend.tar.gz` 文件传输到目标服务器：
   ```bash
   scp task_feishu_frontend.tar.gz user@your-server-ip:/path/to/destination/
   ```

## 在目标服务器上的部署步骤

1. 解压文件：
   ```bash
   tar -xzf task_feishu_frontend.tar.gz
   cd Task_feishu
   ```

2. 配置环境变量：
   编辑 `docker-compose.frontend.yml` 文件，设置 `REACT_APP_BACKEND_URL` 为您的后端API地址：
   ```yaml
   environment:
     - REACT_APP_BACKEND_URL=http://your-backend-server.com:8000
   ```

3. 构建并启动前端容器：
   ```bash
   # 如果当前用户不在docker组中，需要使用sudo
   sudo docker-compose -f docker-compose.frontend.yml up --build -d
   ```

4. 访问前端应用：
   - 默认端口80: http://your-server-ip
   - 如果修改了端口映射，如7080:80，则访问: http://your-server-ip:7080

## 端口配置

- 前端通过Nginx运行在端口80
- 如果需要更改端口，在 `docker-compose.frontend.yml` 中调整 ports 配置

## 自定义配置

1. 如需修改Nginx配置，编辑 `dd/nginx.frontend.conf` 文件然后重新构建镜像

## 停止服务

```bash
sudo docker-compose -f docker-compose.frontend.yml down
```

## 注意事项

1. 确保您的后端API服务器允许来自前端服务器的跨域请求（CORS）
2. 确保防火墙设置允许目标服务器访问后端API服务器的端口
3. 如果当前用户不在docker组中，需要使用sudo运行docker-compose命令
4. 如果服务器上没有package-lock.json文件，构建过程会自动使用npm install安装依赖