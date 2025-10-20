#!/bin/bash
# 派工系统快速部署脚本
# 使用方法: ./deploy.sh [选项]

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查必要的工具
check_prerequisites() {
    print_info "检查部署环境..."

    if ! command_exists docker; then
        print_error "Docker未安装,请先安装Docker"
        echo "安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! command_exists docker-compose; then
        print_error "Docker Compose未安装,请先安装Docker Compose"
        echo "安装指南: https://docs.docker.com/compose/install/"
        exit 1
    fi

    print_success "环境检查通过"
}

# 检查并创建.env文件
check_env_file() {
    print_info "检查环境变量配置..."

    if [ ! -f .env ]; then
        print_warning ".env 文件不存在"
        if [ -f .env.example ]; then
            print_info "从 .env.example 创建 .env 文件"
            cp .env.example .env
            print_warning "请编辑 .env 文件并填写真实的飞书凭证和API密钥"
            echo ""
            echo "需要配置的变量:"
            echo "  - FEISHU_APP_ID"
            echo "  - FEISHU_APP_SECRET"
            echo "  - FEISHU_APP_TOKEN"
            echo "  - FEISHU_TABLE_ID"
            echo "  - API_KEYS (请替换为强密码)"
            echo "  - READONLY_API_KEYS (请替换为强密码)"
            echo "  - ALLOWED_ORIGINS (根据访问地址配置)"
            echo ""
            read -p "按Enter继续编辑 .env 文件..."
            ${EDITOR:-nano} .env
        else
            print_error ".env.example 文件也不存在,无法创建配置"
            exit 1
        fi
    else
        print_success "找到 .env 配置文件"
    fi

    # 检查关键变量是否配置
    if grep -q "请替换为您的" .env; then
        print_warning ".env 中存在未替换的示例值,请确认已填写真实配置"
        read -p "确认继续? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            print_info "部署已取消"
            exit 0
        fi
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建数据目录..."

    mkdir -p data/db
    mkdir -p logs

    # 设置权限
    chmod 755 data/db

    print_success "目录创建完成"
}

# 构建并启动服务
deploy_services() {
    print_info "开始部署服务..."

    # 停止旧服务
    if docker-compose ps | grep -q "Up"; then
        print_info "停止现有服务..."
        docker-compose down
    fi

    # 构建并启动
    print_info "构建Docker镜像..."
    docker-compose build --no-cache

    print_info "启动服务..."
    docker-compose up -d

    print_success "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    print_info "等待服务就绪..."

    max_attempts=30
    attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "后端服务已就绪"
            break
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    echo ""

    if [ $attempt -eq $max_attempts ]; then
        print_error "等待服务超时,请检查日志"
        docker-compose logs --tail=50
        exit 1
    fi
}

# 验证部署
verify_deployment() {
    print_info "验证部署状态..."

    # 检查容器状态
    if ! docker-compose ps | grep -q "Up"; then
        print_error "容器未正常运行"
        docker-compose ps
        exit 1
    fi

    # 检查后端健康
    health_response=$(curl -s http://localhost:8000/health)
    if echo "$health_response" | grep -q "healthy"; then
        print_success "后端健康检查通过"
    else
        print_error "后端健康检查失败: $health_response"
        exit 1
    fi

    print_success "部署验证完成"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    print_success "========================================="
    print_success "  派工系统部署完成!"
    print_success "========================================="
    echo ""
    echo "访问地址:"
    echo "  - 前端界面: http://$(hostname -I | awk '{print $1}'):8080"
    echo "  - 后端API:  http://$(hostname -I | awk '{print $1}'):8000"
    echo "  - API文档:  http://$(hostname -I | awk '{print $1}'):8000/docs"
    echo ""
    echo "常用命令:"
    echo "  - 查看日志:   docker-compose logs -f"
    echo "  - 停止服务:   docker-compose down"
    echo "  - 重启服务:   docker-compose restart"
    echo "  - 查看状态:   docker-compose ps"
    echo ""
    echo "数据同步:"
    echo "  - 点击前端页面右上角\"同步数据\"按钮"
    echo "  - 或执行: curl -X POST -H \"X-API-Key: <your-key>\" http://localhost:8000/api/sync"
    echo ""
    print_info "详细文档: docs/DEPLOYMENT_GUIDE.md"
    echo ""
}

# 主流程
main() {
    echo ""
    print_info "========================================="
    print_info "  派工系统部署脚本"
    print_info "========================================="
    echo ""

    # 检查参数
    case "${1:-}" in
        -h|--help)
            echo "使用方法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  -h, --help     显示帮助信息"
            echo "  -c, --check    仅检查环境"
            echo "  -s, --stop     停止服务"
            echo "  -r, --restart  重启服务"
            echo "  -l, --logs     查看日志"
            echo ""
            exit 0
            ;;
        -c|--check)
            check_prerequisites
            check_env_file
            print_success "环境检查完成,可以开始部署"
            exit 0
            ;;
        -s|--stop)
            print_info "停止服务..."
            docker-compose down
            print_success "服务已停止"
            exit 0
            ;;
        -r|--restart)
            print_info "重启服务..."
            docker-compose restart
            print_success "服务已重启"
            exit 0
            ;;
        -l|--logs)
            docker-compose logs -f
            exit 0
            ;;
    esac

    # 执行部署流程
    check_prerequisites
    check_env_file
    create_directories
    deploy_services
    wait_for_services
    verify_deployment
    show_deployment_info
}

# 运行主流程
main "$@"
