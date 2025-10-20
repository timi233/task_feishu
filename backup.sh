#!/bin/bash
# 数据库备份脚本
# 用于定期备份SQLite数据库

set -e

# 配置
BACKUP_DIR="./backups"
DB_PATH="./data/db/tasks.db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/tasks_${DATE}.db"

# 保留天数
RETENTION_DAYS=7

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "  派工系统数据库备份"
echo "========================================"
echo ""

# 检查数据库文件是否存在
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}错误:${NC} 数据库文件不存在: $DB_PATH"
    exit 1
fi

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 执行备份
echo -e "${YELLOW}正在备份数据库...${NC}"
cp "$DB_PATH" "$BACKUP_FILE"

# 验证备份文件
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ 备份成功${NC}"
    echo "  文件: $BACKUP_FILE"
    echo "  大小: $SIZE"
else
    echo -e "${RED}✗ 备份失败${NC}"
    exit 1
fi

# 清理旧备份
echo ""
echo -e "${YELLOW}清理 $RETENTION_DAYS 天前的旧备份...${NC}"
OLD_COUNT=$(find "$BACKUP_DIR" -name "tasks_*.db" -mtime +$RETENTION_DAYS | wc -l)

if [ "$OLD_COUNT" -gt 0 ]; then
    find "$BACKUP_DIR" -name "tasks_*.db" -mtime +$RETENTION_DAYS -delete
    echo -e "${GREEN}✓ 删除了 $OLD_COUNT 个旧备份${NC}"
else
    echo "  无需清理"
fi

# 列出当前所有备份
echo ""
echo "当前备份列表:"
echo "----------------------------------------"
ls -lh "$BACKUP_DIR"/tasks_*.db 2>/dev/null | awk '{print "  "$9" ("$5")"}'

echo ""
echo -e "${GREEN}备份完成!${NC}"
