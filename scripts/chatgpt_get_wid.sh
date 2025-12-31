#!/usr/bin/env bash
set -euo pipefail

# Selector estable del WID de la ventana "puente" de ChatGPT.
# - NO usa wmctrl local: usa host_exec (IPC), sirve desde sandbox.
# - Si no existe ventana ChatGPT, la crea (abre chat.openai.com) y espera.
# - Protege de tipear en ventanas "V.S.Code ..."

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

# Si ya está forzado por env, respetarlo.
if [[ -n "${CHATGPT_WID_HEX:-}" ]]; then
  printf '%s\n' "$CHATGPT_WID_HEX"
  exit 0
fi

get_wmctrl() {
  "$HOST_EXEC" 'wmctrl -lx' 2>/dev/null || true
}

pick_chatgpt_wid() {
  awk '
    BEGIN { best=""; bestScore=-1 }
    {
      wid=$1; cls=$3;
      title="";
      for(i=4;i<=NF;i++){ title = title (i==4 ? "" : " ") $i }

      # Chrome
      if(cls!="google-chrome.Google-chrome") next;

      # Debe ser ChatGPT (criterio actual)
      if(index(title,"ChatGPT")==0) next;

      # Evitar este chat (o cualquier ventana que arrastre el contexto VS Code)
      if(index(title,"V.S.Code")>0) next;

      score=10;
      if(index(title,"ChatGPT - Google Chrome")>0) score=90;
      else if(index(title,"ChatGPT")>0) score=60;

      if(score>bestScore){ bestScore=score; best=wid }
    }
    END { if(best!="") print best }
  '
}

# 1) Intento directo
WINS="$(get_wmctrl)"
WID="$(printf '%s\n' "$WINS" | pick_chatgpt_wid | head -n 1)"

# 2) Si no hay ventana ChatGPT, abrirla y esperar
if [[ -z "${WID:-}" ]]; then
  "$HOST_EXEC" "bash -lc 'google-chrome --new-window \"https://chat.openai.com/\" >/dev/null 2>&1 & disown'" >/dev/null 2>&1 || true

  # Esperar hasta ~12s a que aparezca un título con ChatGPT
  for _ in $(seq 1 24); do
    sleep 0.5
    WINS="$(get_wmctrl)"
    WID="$(printf '%s\n' "$WINS" | pick_chatgpt_wid | head -n 1)"
    [[ -n "${WID:-}" ]] && break
  done
fi

# 3) Resultado
if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no encuentro ventana ChatGPT (título no contiene 'ChatGPT'). Abrí ChatGPT en Chrome y reintentá." >&2
  exit 3
fi

printf '%s\n' "$WID"
