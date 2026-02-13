#!/bin/bash
# LUCY ALEPH UI - Master Ignition Script
# Starts: Ray Cluster (Nucleus, Thought, Vision, Memory, Action) + Host Agent + React UI

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}🔥 LUCY ALEPH UI - MANUAL IGNITION INITIATED...${NC}"

# 1. Start Host Agent (Background)
echo -e "${GREEN}[1/3] Starting Host Agent (X11 Bridge)...${NC}"
python3 scripts/x11_file_agent.py > logs/host_agent.log 2>&1 &
HOST_AGENT_PID=$!
echo "Host Agent PID: $HOST_AGENT_PID"

# 2. Ignite Ray Cluster (Foreground/Attached)
echo -e "${GREEN}[2/3] Starting Neural Swarm (Ray Actors)...${NC}"
./.venv_web/bin/python lucy_ignition.py &
CEREBRO_PID=$!
echo "Neural Swarm PID: $CEREBRO_PID"

# 3. Start Aleph UI (Vite)
echo -e "${GREEN}[3/3] Starting Aleph UI (React)...${NC}"
cd src/ui/aleph_ui
npm run dev -- --port 5050
