#!/bin/bash
set -euo pipefail

# Check if the process is running
if ! pgrep -f "src/main.py" > /dev/null; then
    echo "Lucy Core is not running!"
    exit 1
fi

# Here we could add a curl check to a local health endpoint if implemented
# curl -f http://localhost:8000/health || exit 1

echo "Lucy Core is healthy."
exit 0
