#!/bin/bash
set -e

# Configuration
WORKSPACE_DIR="/home/lucy-ubuntu/Lucy_Workspace/Proyecto-VSCode"
SCREENSHOTS_DIR="$WORKSPACE_DIR/screenshots"
LOGS_DIR="$WORKSPACE_DIR/logs"
RETENTION_DAYS=1

echo "Starting maintenance for $WORKSPACE_DIR..."

# 1. Cleanup old screenshots
if [ -d "$SCREENSHOTS_DIR" ]; then
    echo "Cleaning screenshots older than $RETENTION_DAYS days in $SCREENSHOTS_DIR..."
    find "$SCREENSHOTS_DIR" -name "*.png" -type f -mtime +$RETENTION_DAYS -delete
fi

# 2. Rotate/Clean logs (Simple approach: delete old logs, or use logrotate if configured externally)
# Here we just clean old log files if they are just flat files
if [ -d "$LOGS_DIR" ]; then
    echo "Cleaning logs older than 7 days in $LOGS_DIR..."
    find "$LOGS_DIR" -name "*.log" -type f -mtime +7 -delete
fi

echo "Maintenance complete."
