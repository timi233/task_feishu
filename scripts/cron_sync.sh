#!/bin/bash
cd /opt/task_feishu/prod_192.168.101.13/docker
docker compose exec -T app python3 -c "
from sync_feishu_to_db import sync_feishu_data_to_db
sync_feishu_data_to_db()
" >> /opt/task_feishu/prod_192.168.101.13/logs/sync.log 2>&1
