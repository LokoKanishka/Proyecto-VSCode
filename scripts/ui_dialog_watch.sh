#!/usr/bin/env bash
set -e

# CLI: --one-shot | --for <seconds>
MODE="one-shot"
DURATION=0
if [[ "$1" == "--for" ]]; then
    MODE="loop"
    DURATION="$2"
fi

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$ROOT/config_ui_dialogs.yaml"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

# Inline Python Logic
python3 -c "
import sys
import time
import yaml
import re
import subprocess
import os

try:
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f)
except Exception as e:
    print(f'ERROR: loading config: {e}', file=sys.stderr)
    sys.exit(1)

host_exec = '$HOST_EXEC'
rules = config.get('rules', [])
cooldowns = {}

def get_active_window_info():
    try:
        # Get WID
        cmd_wid = [host_exec, 'xprop -root _NET_ACTIVE_WINDOW']
        res = subprocess.run(cmd_wid, capture_output=True, text=True, timeout=5)
        if res.returncode != 0: return None
        # Parse 0x...
        match = re.search(r'0x[0-9a-fA-F]+', res.stdout)
        if not match: return None
        wid_hex = match.group(0)
        
        # Get Title
        cmd_title = [host_exec, f'wmctrl -l | grep -i {wid_hex}'] # grep to filter locally? wmctrl output is multiple lines
        # Better: xprop -id WID _NET_WM_NAME
        cmd_title = [host_exec, f'xprop -id {wid_hex} _NET_WM_NAME']
        res_t = subprocess.run(cmd_title, capture_output=True, text=True, timeout=5)
        title = res_t.stdout
        # Clean title: _NET_WM_NAME(UTF8_STRING) = \"Title\"
        if '\"' in title:
             title = title.split('\"')[1]
        
        return wid_hex, title
    except Exception as e:
        return None

def execute_action(rule, wid):
    action = rule['action']
    cmd = ''
    if action == 'enter':
        cmd = f'xdotool key --window {wid} Return'
    elif action == 'escape':
         cmd = f'xdotool key --window {wid} Escape'
    elif action == 'tab_enter':
        count = rule.get('tab_count', 1)
        # Sequence of tabs then enter
        keys = 'Tab ' * count + 'Return'
        cmd = f'xdotool key --window {wid} {keys}'
    elif action == 'click_rel':
        # complex: get geometry, calc, click
        # Simplified: assume xdotool installed on host
        x_pct = rule.get('x_pct', 50)
        y_pct = rule.get('y_pct', 50)
        # Need geometry.
        # Use simpler approach: relative move if supported or just click
        # xdotool mousemove --window WID x y (but x y are coords, not pct)
        # Getting geometry via host_exec is expensive for this lightweight script? 
        # Plan says: 'click relative'. 
        pass 
        
    if cmd:
        subprocess.run([host_exec, cmd], capture_output=True)
        print(f'__LUCY_UI_DIALOG__ RULE={rule[\"name\"]} HIT=1', file=sys.stderr)
    else:
        # Handling click_rel or unknown
        pass

def run_once():
    info = get_active_window_info()
    if not info: return
    wid, title = info
    
    now = time.time()
    for rule in rules:
        regex = rule['window_title_regex']
        name = rule['name']
        
        # Cooldown check
        last = cooldowns.get(name, 0)
        cd_val = rule.get('cooldown_s', 5)
        if now - last < cd_val:
            continue
            
        if re.search(regex, title, re.IGNORECASE):
            # HIT
            execute_action(rule, wid)
            cooldowns[name] = now
            return

mode = '$MODE'
duration = float('$DURATION')
start = time.time()

while True:
    run_once()
    if mode == 'one-shot':
        break
    if time.time() - start > duration:
        break
    time.sleep(1.0)
"
