#!/bin/bash
# verify_network.sh - 验证网络访问配置

echo "=========================================="
echo " 飞书派工系统 - 网络访问验证"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 通过${NC}"
        return 0
    else
        echo -e "${RED}✗ 失败${NC}"
        return 1
    fi
}

# 1. 检查IP地址
echo "1. 检查IP地址配置..."
if ip addr show | grep -q "10.242.94.9"; then
    echo -e "   ${GREEN}✓ 发现IP: 10.242.94.9${NC}"
else
    echo -e "   ${YELLOW}⚠ 未发现IP 10.242.94.9,系统可能绑定到其他IP${NC}"
    echo "   当前IP地址:"
    ip addr show | grep "inet " | grep -v "127.0.0.1" | awk '{print "   - " $2}'
fi
echo ""

# 2. 检查Docker服务状态
echo "2. 检查Docker服务状态..."
docker-compose ps | grep -E "Up|健康"
check_status
echo ""

# 3. 检查端口监听
echo "3. 检查端口监听..."
echo "   后端 (8000):"
if ss -tuln | grep -q ":8000"; then
    echo -e "   ${GREEN}✓ 端口8000正在监听${NC}"
    ss -tuln | grep ":8000" | head -1
else
    echo -e "   ${RED}✗ 端口8000未监听${NC}"
fi

echo "   前端 (8080):"
if ss -tuln | grep -q ":8080"; then
    echo -e "   ${GREEN}✓ 端口8080正在监听${NC}"
    ss -tuln | grep ":8080" | head -1
else
    echo -e "   ${RED}✗ 端口8080未监听${NC}"
fi
echo ""

# 4. 检查CORS配置
echo "4. 检查CORS配置..."
if grep -q "10.242.94.9" .env; then
    echo -e "   ${GREEN}✓ CORS已包含10.242.94.9${NC}"
    grep "ALLOWED_ORIGINS" .env
else
    echo -e "   ${RED}✗ CORS未配置10.242.94.9${NC}"
fi
echo ""

# 5. 测试后端API
echo "5. 测试后端API (health检查)..."
if curl -s -f http://10.242.94.9:8000/health > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ 后端API响应正常${NC}"
    curl -s http://10.242.94.9:8000/health
elif curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "   ${YELLOW}⚠ 后端仅localhost可访问,10.242.94.9不可访问${NC}"
    echo "   请检查防火墙或网络配置"
else
    echo -e "   ${RED}✗ 后端API无响应${NC}"
fi
echo ""

# 6. 测试前端访问
echo "6. 测试前端Nginx..."
if curl -s -f http://10.242.94.9:8080 > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ 前端Nginx响应正常${NC}"
elif curl -s -f http://localhost:8080 > /dev/null 2>&1; then
    echo -e "   ${YELLOW}⚠ 前端仅localhost可访问,10.242.94.9不可访问${NC}"
else
    echo -e "   ${RED}✗ 前端Nginx无响应${NC}"
fi
echo ""

# 7. 检查数据库文件
echo "7. 检查数据库文件..."
if [ -f "data/db/tasks.db" ]; then
    echo -e "   ${GREEN}✓ 数据库文件存在${NC}"
    ls -lh data/db/tasks.db
else
    echo -e "   ${RED}✗ 数据库文件不存在${NC}"
fi
echo ""

# 8. 检查engineers表
echo "8. 检查engineers表..."
ENGINEER_CHECK=$(docker-compose exec -T app python << 'EOFPYTHON'
import sqlite3
try:
    conn = sqlite3.connect("./data/db/tasks.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM engineers")
    count = cursor.fetchone()[0]
    print(f"SUCCESS:{count}")
    conn.close()
except Exception as e:
    print(f"ERROR:{e}")
EOFPYTHON
)

if echo "$ENGINEER_CHECK" | grep -q "SUCCESS"; then
    ENGINEER_COUNT=$(echo "$ENGINEER_CHECK" | cut -d: -f2)
    echo -e "   ${GREEN}✓ engineers表已创建${NC}"
    echo "   工程师数量: $ENGINEER_COUNT"
else
    echo -e "   ${YELLOW}⚠ engineers表检查失败${NC}"
    echo "   $ENGINEER_CHECK"
fi
echo ""

# 总结
echo "=========================================="
echo " 验证完成!"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  前端界面: http://10.242.94.9:8080"
echo "  后端API:  http://10.242.94.9:8000"
echo "  API文档:  http://10.242.94.9:8000/docs"
echo ""
echo "如有问题,请查看详细文档:"
echo "  docs/NETWORK_ACCESS_CONFIG.md"
echo ""
