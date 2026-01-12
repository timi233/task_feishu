# 生产部署手册（目标 IP: 192.168.101.13）

## 1. 准备工作
- 操作系统：Ubuntu 20.04+/Debian 11+
- 需要 sudo 权限
- 安装 Docker 24+ 与 docker compose v2
- 确保 8080 端口对外开放（前端），9000 端口用于 Identity Hub

## 2. 包内容
```
prod_192.168.101.13/
├── backend/
├── frontend/
├── docker/
├── scripts/
├── docs/
├── identity-hub/
├── .env
└── README*.md
```

## 3. 部署步骤
1. 上传并解压：
   ```bash
   scp prod_192.168.101.13_full.tar.gz user@192.168.101.13:/opt
   cd /opt && tar -xzf prod_192.168.101.13_full.tar.gz
   ```
2. 准备数据目录：
   ```bash
   mkdir -p /opt/task_feishu/prod_192.168.101.13/data/db
   mkdir -p /opt/task_feishu/prod_192.168.101.13/logs
   ```
3. 安装依赖、构建前端（可选）：
   ```bash
   cd /opt/task_feishu/prod_192.168.101.13/frontend
   npm install && npm run build
   ```
   （包中已含 build 结果，如无修改可跳过）
4. 启动派工系统：
   ```bash
   cd /opt/task_feishu/prod_192.168.101.13/docker
   docker compose build
   docker compose up -d
   ```
5. 启动 Identity Hub（如需）：
   ```bash
   cd /opt/task_feishu/prod_192.168.101.13/identity-hub
   docker compose build
   docker compose up -d
   ```
6. 配置定时同步（Cron）：
   ```bash
   crontab -e
   # 添加以下行（每小时同步一次）
   0 * * * * /opt/task_feishu/prod_192.168.101.13/scripts/cron_sync.sh
   ```
7. 验证：
   ```bash
   curl http://192.168.101.13:8080/health
   curl http://192.168.101.13:9000/health
   ```

## 4. 关键环境变量
| 变量 | 说明 | 值 |
| --- | --- | --- |
| `ALLOWED_ORIGINS` | CORS 白名单 | 含 `http://192.168.101.13:8080` |
| `IDENTITY_HUB_URL` | OAuth 服务 | `http://192.168.101.13:9000` |
| `IDENTITY_HUB_REDIRECT_URI` | OAuth 回调 | `http://192.168.101.13:8080/auth/callback` |
| `FRONTEND_URL` | 登录后跳转 | `http://192.168.101.13:8080` |

## 5. 常见命令
```bash
# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f app

# 重新构建
docker compose up -d --build
```

## 6. 验证清单
- [ ] 前端可访问 http://192.168.101.13:8080
- [ ] 登录能跳转至 Identity Hub 并返回
- [ ] `/api/dispatch/orders` 能返回数据
- [ ] `/health` 返回 `status=healthy`

更多细节见同目录的《PROD_OPERATIONS_GUIDE.md》和《IDENTITY_HUB_DEPLOYMENT.md》。
