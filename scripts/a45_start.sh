#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$REPO_ROOT/scripts/a45_runner.sh"
SESSION="lucy_a45"

if ! command -v tmux >/dev/null; then
  echo "tmux no está disponible; ejecuta $RUNNER manualmente."
  exit 1
fi

if tmux has-session -t "$SESSION" >/dev/null 2>&1; then
  echo "La sesión $SESSION ya está activa. Usa 'tmux attach -t $SESSION' para verla."
  exit 0
fi

tmux new-session -d -s "$SESSION" "$RUNNER"
echo "Runner lanzado en sesión tmux '$SESSION'."
echo "Para seguir el progreso: tmux attach -t $SESSION"
echo "También podes vigilar el log principal con:"
echo "  tail -f /tmp/lucy_a45_runner_*/runner.log"
