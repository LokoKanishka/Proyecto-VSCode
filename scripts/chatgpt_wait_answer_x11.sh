#!/usr/bin/env bash
set -euo pipefail

# chatgpt_wait_answer_x11.sh
# Escucha activa del chat (polling de diffs) hasta detectar la respuesta completa (LUCY_ANSWER_<token>)
# o un timeout "inteligente" (si no hay cambios por mucho tiempo).

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COPY_SCRIPT="$ROOT/scripts/chatgpt_copy_messages_strict.sh"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

TOKEN="$1"
if [[ -z "${TOKEN:-}" ]]; then
  echo "ERROR: TOKEN required" >&2
  exit 2
fi

# Configuración (defaults ajustados para "thinking" models)
MAX_SEC="${CHATGPT_WAIT_MAX_SEC:-240}"       # Tiempo total máximo antes de rendirse
STABLE_SEC="${CHATGPT_WAIT_STABLE_SEC:-3}"   # Segundos sin cambios para considerar "estancado"
POLL_MIN="${CHATGPT_WAIT_POLL_MIN_SEC:-0.4}" # Poll intervalo min
POLL_MAX="${CHATGPT_WAIT_POLL_MAX_SEC:-2.0}" # Poll intervalo max

start_ts=$(date +%s)
last_change_ts=$start_ts
last_hash=""
found_answer=0
stable_count=0
nudged=0

  # Helper para extraer answer
extract_answer_line() {
  local content="$1"
  local token="$2"
  # Busca línea que empiece exactamente con "LUCY_ANSWER_<token>:" (ignorando espacios iniciales)
  # Esto evita matchear instrucciones en el prompt tipo "Debes contestar con LUCY_ANSWER..."
  grep -E "^[[:space:]]*LUCY_ANSWER_${token}:" <<< "$content" | head -n 1
}

# Helper timestamp ms
now_ms() {
  date +%s%3N
}

echo "__LUCY_WAIT_META__ START token=${TOKEN} max=${MAX_SEC}" >&2

while true; do
  now=$(date +%s)
  elapsed=$((now - start_ts))
  
  if [[ "$elapsed" -gt "$MAX_SEC" ]]; then
    echo "__LUCY_WAIT_META__ TIMEOUT elapsed=${elapsed}" >&2
    exit 1
  fi

  # 1. Copiar chat (strict mode ya limpia sidebar)
  # Usamos try-catch light porque el copy puede fallar temporalmente (focus)
  current_text="$("$COPY_SCRIPT" 2>/dev/null || echo "")"
  
  # Si falló copy (vacío), no es "cambio" ni "estable", es error transitorio (o loading)
  if [[ -z "$current_text" ]]; then
    sleep "$POLL_MIN"
    continue
  fi

  # 2. Hash check
  current_hash="$(echo "$current_text" | sha1sum | awk '{print $1}')"
  
  changed=0
  if [[ "$current_hash" != "$last_hash" ]]; then
    changed=1
    last_hash="$current_hash"
    last_change_ts="$now"
    stable_count=0
    # Si hubo cambios, el nudge ya no es necesario (reseteamos flag si queremos re-nudgear en futuro estancamiento? 
    # Mejor no, un nudge por sesión suele bastar si se trabó el scroll)
  else
    stable_wait=$((now - last_change_ts))
    if [[ "$stable_wait" -ge "$STABLE_SEC" ]]; then
      stable_count=1
    fi
  fi

  # 3. Detectar respuesta
  answer_line="$(extract_answer_line "$current_text" "$TOKEN")"
  
  if [[ -n "$answer_line" ]]; then
    found_answer=1
    echo "__LUCY_WAIT_META__ FOUND bytes=${#current_text}" >&2
    echo "$answer_line"
    exit 0
  fi

  echo "__LUCY_WAIT_META__ t=${elapsed} changed=${changed} bytes=${#current_text} stable=${stable_wait:-0}" >&2

  # 4. Manejo de estancamiento (Stable pero sin respuesta)
  if [[ "$stable_count" -eq 1 ]]; then
    # Si llevamos mucho tiempo estables y no hay respuesta...
    # Caso A: Apenas se estabilizó (pasaron STABLE_SEC). Intentamos UN nudge si no lo hicimos.
    if [[ "$nudged" -eq 0 ]]; then
      echo "__LUCY_WAIT_META__ NUDGE (refreshing interactions)" >&2
      # Acción suave: Escape + End + Recopy forzado
      # Esto ayuda si el "strict copy" estaba fallando por scroll o foco perdido
      # O si ChatGPT dejó de streamear pero no scrolleó.
      "$HOST_EXEC" "xdotool key --window "$WID_DEC" --clearmodifiers Escape End 2>/dev/null"
      nudged=1
      # Reseteamos last_change_ts para dar tiempo post-nudge
      last_change_ts="$now"
      sleep 0.5
      continue
    fi
    
    # Caso B: Ya nugeamos y sigue estable (y sin answer).
    # Podría ser que el modelo terminó pero NO generó el formato correcto (error de modelo).
    # O que sigue pensando (poco probable si es stable 3s, aunque o1 a veces pausa).
    # Si el tiempo stable es MUY largo (ej 20s), asumimos que terminó mal.
    stable_total=$((now - last_change_ts))
    if [[ "$stable_total" -gt 20 ]]; then # Hardcoded safety for dead generation
       echo "ERROR: STUCK (stable > 20s without valid answer format)" >&2
       exit 2
    fi
  fi

  # Backoff sleep
  sleep "$POLL_MIN"
done
