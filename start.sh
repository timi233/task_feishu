#!/bin/bash
# start.sh
echo "Starting application setup..."

# Function to run data sync
run_sync(){
	echo "Running data sync at $(date)"
	python sync_once.py
}

# Run initial sync
run_sync

# Start periodic sync in the ackground
# Run every 60 minutes
(
	while true;do
		echo "Sleeping for 60 minutes..."
		sleep 3600
		run_sync
	done
) &

# Start backend service
echo "Starting backend service..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
