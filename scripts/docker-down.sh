#!/bin/bash
# Docker Compose快捷停止脚本

cd "$(dirname "$0")/docker"

echo "正在停止Docker服务..."
docker-compose down

echo ""
echo "所有Docker服务已停止"
