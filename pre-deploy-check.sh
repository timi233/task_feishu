#!/bin/bash
# 部署前预检脚本
# 用于在外部设备部署前验证所有必要条件

set -e

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS="${GREEN}✓${NC}"
FAIL="${RED}✗${NC}"
WARN="${YELLOW}⚠${NC}"

echo ""
echo "========================================"
echo "  派工系统部署前环境检查"
echo "========================================"
echo ""

# 检查项计数
total_checks=0
passed_checks=0
failed_checks=0

check_item() {
    total_checks=$((total_checks + 1))
    printf "%-50s" "$1"
}

pass() {
    echo -e "$PASS $2"
    passed_checks=$((passed_checks + 1))
}

fail() {
    echo -e "$FAIL $2"
    failed_checks=$((failed_checks + 1))
}

warn() {
    echo -e "$WARN $2"
}

# 1. 检查操作系统
check_item "操作系统"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_VERSION=$(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)
    pass "$OS_VERSION"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    pass "macOS"
else
    warn "未知系统: $OSTYPE"
fi

# 2. 检查Docker
check_item "Docker"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    pass "已安装 (v$DOCKER_VERSION)"
else
    fail "未安装"
    echo "   安装: https://docs.docker.com/get-docker/"
fi

# 3. 检查Docker Compose
check_item "Docker Compose"
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
    pass "已安装 (v$COMPOSE_VERSION)"
else
    fail "未安装"
    echo "   安装: https://docs.docker.com/compose/install/"
fi

# 4. 检查Docker服务状态
check_item "Docker服务"
if docker info &> /dev/null; then
    pass "运行中"
else
    fail "未运行"
    echo "   启动: sudo systemctl start docker"
fi

# 5. 检查磁盘空间
check_item "可用磁盘空间"
AVAILABLE_SPACE=$(df -h . | awk 'NR==2 {print $4}')
AVAILABLE_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAILABLE_GB" -gt 2 ]; then
    pass "$AVAILABLE_SPACE 可用"
else
    warn "$AVAILABLE_SPACE (建议至少2GB)"
fi

# 6. 检查内存
check_item "可用内存"
if command -v free &> /dev/null; then
    TOTAL_MEM=$(free -h | awk 'NR==2 {print $2}')
    AVAILABLE_MEM=$(free -h | awk 'NR==2 {print $7}')
    pass "$AVAILABLE_MEM / $TOTAL_MEM"
elif command -v vm_stat &> /dev/null; then
    # macOS
    pass "$(vm_stat | grep 'Pages free' | awk '{print $3}')"
fi

# 7. 检查网络连接
check_item "互联网连接"
if ping -c 1 8.8.8.8 &> /dev/null; then
    pass "正常"
else
    fail "无法连接"
fi

# 8. 检查飞书API可达性
check_item "飞书API连接"
if curl -s --connect-timeout 5 https://open.feishu.cn &> /dev/null; then
    pass "可访问"
else
    warn "无法访问 (可能是防火墙限制)"
fi

# 9. 检查端口占用
check_item "端口8000"
if lsof -Pi :8000 -sTCP:LISTEN -t &> /dev/null; then
    warn "已被占用"
else
    pass "可用"
fi

check_item "端口8080"
if lsof -Pi :8080 -sTCP:LISTEN -t &> /dev/null; then
    warn "已被占用"
else
    pass "可用"
fi

# 10. 检查必要文件
echo ""
echo "文件检查:"
echo "----------------------------------------"

check_item "  docker-compose.yml"
if [ -f "docker-compose.yml" ]; then
    pass "存在"
else
    fail "缺失"
fi

check_item "  Dockerfile"
if [ -f "Dockerfile" ]; then
    pass "存在"
else
    fail "缺失"
fi

check_item "  .env配置文件"
if [ -f ".env" ]; then
    pass "存在"

    # 检查关键变量
    if grep -q "请替换为" .env 2>/dev/null; then
        warn "  → 包含未替换的示例值"
    fi
else
    warn "不存在 (将从.env.example创建)"
fi

check_item "  backend/"
if [ -d "backend" ]; then
    pass "存在"
else
    fail "缺失"
fi

check_item "  frontend/"
if [ -d "frontend" ]; then
    pass "存在"
else
    fail "缺失"
fi

# 11. 检查data目录
check_item "  data/db/"
if [ -d "data/db" ]; then
    PERMS=$(stat -c %a data/db 2>/dev/null || stat -f %Lp data/db)
    if [ "$PERMS" = "755" ] || [ "$PERMS" = "775" ]; then
        pass "存在 (权限: $PERMS)"
    else
        warn "存在但权限可能不当 ($PERMS)"
    fi
else
    warn "不存在 (将自动创建)"
fi

# 12. 环境变量验证
if [ -f ".env" ]; then
    echo ""
    echo "环境变量检查:"
    echo "----------------------------------------"

    check_env_var() {
        VAR_NAME=$1
        if grep -q "^${VAR_NAME}=" .env && ! grep "^${VAR_NAME}=.*请替换" .env &> /dev/null; then
            VALUE=$(grep "^${VAR_NAME}=" .env | cut -d'=' -f2)
            if [ -n "$VALUE" ]; then
                check_item "  $VAR_NAME"
                pass "已配置"
            else
                check_item "  $VAR_NAME"
                fail "值为空"
            fi
        else
            check_item "  $VAR_NAME"
            fail "未配置或为示例值"
        fi
    }

    check_env_var "FEISHU_APP_ID"
    check_env_var "FEISHU_APP_SECRET"
    check_env_var "FEISHU_APP_TOKEN"
    check_env_var "FEISHU_TABLE_ID"
    check_env_var "API_KEYS"
    check_env_var "READONLY_API_KEYS"
    check_env_var "ALLOWED_ORIGINS"
fi

# 汇总
echo ""
echo "========================================"
echo "  检查汇总"
echo "========================================"
echo "总检查项: $total_checks"
echo -e "${GREEN}通过: $passed_checks${NC}"
echo -e "${RED}失败: $failed_checks${NC}"
echo ""

if [ $failed_checks -eq 0 ]; then
    echo -e "${GREEN}✓ 环境检查通过,可以开始部署!${NC}"
    echo ""
    echo "下一步:"
    echo "  1. 确认 .env 文件配置正确"
    echo "  2. 运行: ./deploy.sh"
    echo ""
    exit 0
else
    echo -e "${RED}✗ 环境检查失败,请解决上述问题后重试${NC}"
    echo ""
    echo "常见问题解决:"
    echo "  - Docker未安装: https://docs.docker.com/get-docker/"
    echo "  - 端口被占用: 修改 docker-compose.yml 中的端口"
    echo "  - .env未配置: cp .env.example .env && nano .env"
    echo ""
    exit 1
fi
