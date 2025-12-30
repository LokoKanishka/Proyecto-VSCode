#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
IPC_DIR="${X11_FILE_IPC_DIR:-$ROOT/diagnostics/x11_file_ipc}"
FIFO="/tmp/lucy_agent_stdin.fifo"

mkdir -p "$IPC_DIR/inbox" "$IPC_DIR/outbox" "$IPC_DIR/payloads"

# Stop existing agent
pkill -f 'scripts/x11_file_agent\.py' >/dev/null 2>&1 || true

# Prepare "infinite stdin" FIFO to avoid pipe_read/EOF issues
rm -f "$FIFO"
mkfifo "$FIFO"
(nohup bash -lc "while :; do echo .; sleep 60; done >'$FIFO'" >/dev/null 2>&1 &)

# Start detached agent
setsid -f python3 "$ROOT/scripts/x11_file_agent.py" <"$FIFO" >>"$IPC_DIR/agent.log" 2>&1

# Quick check
"$ROOT/scripts/x11_file_call.sh" 'echo PING_OK'
