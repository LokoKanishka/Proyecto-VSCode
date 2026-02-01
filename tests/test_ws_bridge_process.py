import os
import subprocess
import sys
import time

import pytest


@pytest.mark.skipif(os.getenv("LUCY_E2E_WS", "0") not in {"1", "true", "yes"}, reason="E2E WS disabled")
def test_ws_bridge_two_processes():
    env = os.environ.copy()
    env["LUCY_WS_PORT"] = "8779"
    env["LUCY_WS_GATEWAY"] = "1"
    env["LUCY_SWARM_CONSOLE"] = "0"

    gw = subprocess.Popen([sys.executable, "-m", "src.engine.swarm_runner"], env=env)
    try:
        time.sleep(2)
        env_b = env.copy()
        env_b["LUCY_WS_BRIDGE_URLS"] = "ws://127.0.0.1:8779"
        bridge = subprocess.Popen([sys.executable, "-m", "src.engine.swarm_runner"], env=env_b)
        try:
            time.sleep(2)
            assert bridge.poll() is None
        finally:
            bridge.terminate()
            bridge.wait(timeout=5)
    finally:
        gw.terminate()
        gw.wait(timeout=5)
