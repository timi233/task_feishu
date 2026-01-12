#!/bin/bash
# Docker Compose快捷启动脚本
# 使用方法: ./docker-up.sh [mysql|frontend|default]

cd "$(dirname "$0")"

case "${1:-default}" in
    mysql)
        echo "使用MySQL配置启动..."
        cd docker && docker-compose -f docker-compose.mysql.yml up -d
        ;;
    frontend)
        echo "仅启动前端服务..."
        cd docker && docker-compose -f docker-compose.frontend.yml up -d
        ;;
    *)
        echo "使用默认配置(SQLite)启动..."
        cd docker && docker-compose up -d
        ;;
esac

echo ""
echo "服务已启动! 访问:"
echo "  - 前端: http://10.242.94.9:8080"
echo "  - 后端API: http://10.242.94.9:8000"
echo "  - API文档: http://10.242.94.9:8000/docs"
echo ""
echo "查看日志: cd docker && docker-compose logs -f"
echo "停止服务: ./docker-down.sh"
