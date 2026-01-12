#!/bin/bash
# start.sh
echo "Starting application setup..."

# 同步间隔（从环境变量获取，默认30分钟）
SYNC_INTERVAL_MINUTES=${SYNC_INTERVAL_MINUTES:-30}
SYNC_INTERVAL_SECONDS=$((SYNC_INTERVAL_MINUTES * 60))

# Function to run data sync
run_sync(){
	echo "Running data sync at $(date)"
	python sync_once.py
	echo "Running dispatch sync at $(date)"
	python -c "from dispatch_sync import sync_all; sync_all()"
}

# Run initial sync
run_sync

# Start periodic sync in the background
echo "[SCHEDULER] Starting periodic sync every ${SYNC_INTERVAL_MINUTES} minutes..."
(
	while true;do
		echo "Sleeping for ${SYNC_INTERVAL_MINUTES} minutes..."
		sleep ${SYNC_INTERVAL_SECONDS}
		run_sync
	done
) &

# Start backend service
echo "Starting backend service..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
