# 生产运维手册

## 一、服务列表
- `docker_app_1`: FastAPI + 同步任务
- `docker-frontend-1`: React 静态资源 (Nginx)
- `identity-hub_backend`：OAuth/单点登录服务

## 二、日常操作
```bash
cd /opt/task_feishu/prod_192.168.101.13/docker
# 查看状态
docker compose ps
# 查看日志
docker compose logs -f app
# 重启
docker compose restart app frontend
# 重新构建并部署
docker compose build app frontend && docker compose up -d
```

手动同步派工：
```bash
curl -X POST http://192.168.101.13:8080/api/sync/dispatch
```

定时同步（Cron）：
- 配置: `0 * * * *` (每小时整点)
- 脚本: `/opt/task_feishu/prod_192.168.101.13/scripts/cron_sync.sh`
- 日志: `/opt/task_feishu/prod_192.168.101.13/logs/sync.log`

## 三、健康检查
- 派工系统：`http://192.168.101.13:8080/health`
- Identity Hub：`http://192.168.101.13:9000/health`

建议通过监控系统定期探测 8080/9000 端口。

## 四、备份
- SQLite：`cp /opt/task_feishu/prod_192.168.101.13/data/db/tasks.db tasks.db.$(date +%F)`
- Identity Hub DB：`cp /opt/task_feishu/prod_192.168.101.13/identity-hub/data/identity-hub.db identity-hub.db.$(date +%F)`
- 版本升级前务必备份代码与数据目录。

## 五、常见问题
| 问题 | 处理 |
| --- | --- |
| 登录失败 | 检查 `.env` 的 `IDENTITY_HUB_URL/REDIRECT_URI`，确认 Identity Hub 客户端的回调列表包含 `http://192.168.101.13:8080/auth/callback` |
| 派工不同步 | 调用 `/api/sync/dispatch` 并查看 `docker compose logs -f app` |
| 数据不可见 | 确认账号权限是否为系统管理员或相关责任人 |
| SQLite 被锁 | 停止服务或使用 `sqlite3 .dump` 方式备份 |

## 六、回滚
1. `docker compose down`
2. 恢复备份数据库/代码
3. `docker compose up -d --build`

## 七、联系方式
- 运维负责人：________
- Identity Hub 管理员：________

更多部署细节见《PROD_DEPLOYMENT_GUIDE.md》。
