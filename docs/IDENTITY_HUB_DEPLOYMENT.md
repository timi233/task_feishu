# Identity Hub 部署指南（192.168.101.13）

## 1. 目录
`identity-hub/` 内包含后端、前端、Docker 配置以及数据文件夹。

## 2. 端口
- 9000：Identity Hub API/UI

## 3. 启动步骤
```bash
cd /opt/prod_192.168.101.13/identity-hub
docker compose build
docker compose up -d
```

默认配置：
- CORS 已包含 `http://192.168.101.13:8080`
- 派工系统客户端 `task_feishu_dispatch_system` 回调列表包含 `http://192.168.101.13:8080/auth/callback`

如需重新生成派工客户端凭证：
```bash
docker compose exec backend python backend/create_dispatch_client.py --redirect http://192.168.101.13:8080/auth/callback
```

## 4. 日常命令
```bash
# 查看日志
docker compose logs -f backend

# 重启
docker compose restart backend
```

## 5. 备份
```
cp identity-hub/data/identity-hub.db identity-hub.db.$(date +%F)
```

## 6. 验证
- `curl http://192.168.101.13:9000/health`
- 浏览器访问 `http://192.168.101.13:9000/login`

更多细节请参考 `identity-hub/README.md` 与 `docs/IDENTITY_HUB_MIGRATION_GUIDE.md`。
