# X11 file-IPC - Smoke tests (ChatGPT bridge)

## Requirements

- Host (GNOME Terminal / real X11 session) running the agent:
  ```bash
  cd ~/Lucy_Workspace/Proyecto-VSCode
  export X11_FILE_IPC_DIR="$PWD/diagnostics/x11_file_ipc"
  source scripts/x11_env.sh
  python3 scripts/x11_file_agent.py
  ```

- Sandbox / terminal where Lucy runs:
  ```bash
  cd ~/Lucy_Workspace/Proyecto-VSCode
  export X11_FILE_IPC_DIR="$PWD/diagnostics/x11_file_ipc"
  source scripts/x11_env.sh || true
  export CHATGPT_BRIDGE_PROFILE_DIR="$HOME/.cache/lucy_chatgpt_bridge_profile"
  ```

Note: from the sandbox there is no direct access to `/tmp/.X11-unix/*`. Everything goes through file-IPC.

## Panic button (kills loops that steal mouse/keyboard)

```bash
bash scripts/smoke/lucy_panic.sh
```

## Ask safe (non-blocking)

Returns a single line `LUCY_ANSWER_...: ...` or exits fast.

```bash
bash scripts/smoke/lucy_ask_safe.sh "Responde exactamente con: OK"
```

## Stability loop (N iterations)

```bash
bash scripts/smoke/smoke_ask_loop.sh 5
# or
bash scripts/smoke/smoke_ask_loop.sh 10
```

## Voice-like E2E (asks for SAFE command, runs on host, pastes output, confirms OK)

```bash
bash scripts/smoke/lucy_voice_like_e2e.sh
```

## Healthy signals

- `ASK_RC=0` and `ASK_OUT=LUCY_ANSWER_...: OK`
- Loop with `OK=N FAIL=0` (for a reasonable N)
- Voice-like with `RC=0` and lines:
  - `ASK1_ANS=... echo LUCY_CMD_OK_<id>`
  - `HOST_OUT_LINE=LUCY_CMD_OK_<id>`
  - `ASK2_ANS...: OK`
