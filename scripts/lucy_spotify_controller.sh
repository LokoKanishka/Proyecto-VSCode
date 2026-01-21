#!/bin/bash
# lucy_spotify_controller.sh
# Control Spotify via MPRIS (playerctl) con fallback "best-effort".

COMMAND="${1:-}"
QUERY="${2:-}"
PLAYER_NAME=""

if [ -z "$COMMAND" ]; then
    echo "Usage: $0 {open|play|pause|toggle|next|prev|search|play_uri|status} [query_or_uri]" >&2
    exit 1
fi

if ! command -v playerctl >/dev/null 2>&1; then
    echo "ERROR_MISSING_TOOL: playerctl" >&2
    exit 3
fi

# Detectar nombre real del player (a veces es spotify, a veces instance...)
detect_player() {
    playerctl -l 2>/dev/null | grep -i "spotify" | head -n1
}

spotify_running() {
    pgrep -af "[s]potify" >/dev/null 2>&1
}

wait_for_mpris() {
    # Esperamos hasta 20s a que aparezca en el bus
    for _ in $(seq 1 40); do
        PLAYER_NAME="$(detect_player)"
        if [ -n "$PLAYER_NAME" ]; then
            return 0
        fi
        sleep 0.5
    done
    return 1
}

ensure_spotify_launched() {
    if ! spotify_running; then
        echo "[SpotifyCtrl] Iniciando aplicación..." >&2
        if command -v spotify >/dev/null 2>&1; then
            spotify >/dev/null 2>&1 &
        elif command -v snap >/dev/null 2>&1; then
            snap run spotify >/dev/null 2>&1 &
        else
            echo "ERROR_NO_SPOTIFY_BINARY" >&2
            exit 2
        fi
        # Damos tiempo extra para arranque en frío
        sleep 5
    fi
}

# Intenta obtener el control, pero NO mata el script si falla (Best Effort)
ensure_mpris_best_effort() {
    if [ -n "$(detect_player)" ]; then
        PLAYER_NAME="$(detect_player)"
        return 0
    fi
    
    # Si no está, esperamos un poco
    if wait_for_mpris; then
        return 0
    fi
    
    echo "WARN_SPOTIFY_MPRIS_TIMEOUT: Intentando comando a ciegas..." >&2
    PLAYER_NAME="spotify" # Fallback por defecto
    return 1
}

encode_query() {
    python3 - <<'PY' "$1"
import sys, urllib.parse
print(urllib.parse.quote(sys.argv[1]))
PY
}

open_uri() {
    local uri="$1"
    # Intentamos abrir con xdg-open o spotify directo
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$uri" >/dev/null 2>&1 &
        return 0
    fi
    echo "ERROR_NO_OPEN_HANDLER" >&2
    return 2
}

case "$COMMAND" in
    open|start)
        ensure_spotify_launched
        ensure_mpris_best_effort
        ;;

    play)
        ensure_mpris_best_effort
        playerctl -p "${PLAYER_NAME}" play >/dev/null 2>&1 || true
        ;;

    pause)
        ensure_mpris_best_effort
        playerctl -p "${PLAYER_NAME}" pause >/dev/null 2>&1 || true
        ;;

    toggle)
        ensure_mpris_best_effort
        playerctl -p "${PLAYER_NAME}" play-pause >/dev/null 2>&1 || true
        ;;

    next)
        ensure_mpris_best_effort
        playerctl -p "${PLAYER_NAME}" next >/dev/null 2>&1 || true
        ;;

    prev|previous)
        ensure_mpris_best_effort
        playerctl -p "${PLAYER_NAME}" previous >/dev/null 2>&1 || true
        ;;

    search)
        if [ -z "$QUERY" ]; then
            echo "ERROR_MISSING_QUERY" >&2
            exit 1
        fi
        ensure_spotify_launched
        encoded="$(encode_query "$QUERY")"
        
        # AQUI EL CAMBIO CLAVE: Abrimos la URI pase lo que pase
        echo "[SpotifyCtrl] Abriendo búsqueda: $QUERY" >&2
        open_uri "spotify:search:${encoded}"
        
        # Esperamos un toque y tratamos de dar play si el control apareció
        sleep 2
        if ensure_mpris_best_effort; then
             playerctl -p "${PLAYER_NAME}" play >/dev/null 2>&1 || true
        fi
        ;;

    play_uri)
        if [ -z "$QUERY" ]; then
            echo "ERROR_MISSING_URI" >&2
            exit 1
        fi
        ensure_spotify_launched
        open_uri "$QUERY"
        ;;

    status)
        if ensure_mpris_best_effort; then
            playerctl -p "${PLAYER_NAME}" metadata --format "{{ artist }} - {{ title }}" 2>/dev/null || echo "Paused/Unknown"
        else
            echo "NoControl"
        fi
        ;;

    *)
        echo "Usage: $0 {open|play...} [args]" >&2
        exit 1
        ;;
esac
