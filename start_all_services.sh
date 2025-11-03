#!/bin/bash

# 启动Identity Hub和派工系统的所有服务

echo "=== 停止旧服务 ==="
pkill -f "uvicorn.*main:app.*8000" || true
pkill -f "uvicorn.*backend.main:app.*8000" || true
sleep 2

echo ""
echo "=== 启动Identity Hub (端口8000) ==="
cd /home/jian/code/identity-hub
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > /tmp/identity-hub.log 2>&1 &
IDENTITY_PID=$!
echo "Identity Hub PID: $IDENTITY_PID"
sleep 3

echo ""
echo "=== 启动派工系统后端 (端口8080) ==="
cd /home/jian/code/Task_feishu/backend
nohup uvicorn main:app --host 0.0.0.0 --port 8080 > /tmp/dispatch-backend.log 2>&1 &
DISPATCH_PID=$!
echo "派工系统后端 PID: $DISPATCH_PID"
sleep 3

echo ""
echo "=== 验证服务状态 ==="
echo "Identity Hub健康检查:"
curl -s http://10.242.94.9:8000/health | jq . || echo "❌ Identity Hub未响应"

echo ""
echo "派工系统健康检查:"
curl -s http://10.242.94.9:8080/health | head -5

echo ""
echo "派工系统认证状态:"
curl -s http://10.242.94.9:8080/auth/status | jq .

echo ""
echo "=== 服务启动完成 ==="
echo "Identity Hub: http://10.242.94.9:8000/docs"
echo "派工系统后端: http://10.242.94.9:8080/health"
echo "派工系统前端: npm start (在frontend目录)"
echo ""
echo "日志文件:"
echo "  Identity Hub: tail -f /tmp/identity-hub.log"
echo "  派工系统: tail -f /tmp/dispatch-backend.log"
