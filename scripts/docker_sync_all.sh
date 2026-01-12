#!/bin/bash
#
# docker_sync_all.sh
# 一键在运行中的 docker 容器内执行「任务同步 + 派工同步」。

set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-docker-app-1}"
APP_DIR="${APP_DIR:-/app}"

# 检查容器是否运行
if ! docker ps --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
    echo "[ERROR] 容器 ${CONTAINER_NAME} 未运行，无法同步。" >&2
    exit 1
fi

run_in_container() {
    local cmd="$1"
    docker exec "${CONTAINER_NAME}" bash -c "cd ${APP_DIR} && ${cmd}"
}

echo "[1/3] 同步任务 (sync_once.py)..."
run_in_container "python sync_once.py"

echo "[2/3] 同步派工 (dispatch_sync.py)..."
run_in_container "python -c 'from dispatch_sync import sync_all; sync_all()'"

echo "[3/3] 同步完成于 $(date '+%F %T')"
