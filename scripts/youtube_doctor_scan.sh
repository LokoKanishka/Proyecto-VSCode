#!/bin/bash
set -euo pipefail

# youtube_doctor_scan.sh
# Uso: Lee la URL de la ventana pineada por el Guard A34 y extrae los resultados usando yt-dlp.
# Salida: JSON simplificado para consumo del LLM.

PIN_FILE="$HOME/Lucy_Workspace/Proyecto-VSCode/diagnostics/pins/chrome_diego.wid"
CAP="$HOME/Lucy_Workspace/Proyecto-VSCode/scripts/chrome_capture_url_omnibox.sh"
TEMP_DIR="/tmp/lucy_yt_doctor"
mkdir -p "$TEMP_DIR"

# 1. Verificar Pin
if [ ! -f "$PIN_FILE" ]; then
    echo "ERROR_NO_PIN: Guard no ha establecido un pin."
    exit 1
fi

# Leer WID del pin (formato seguro A34)
WID_HEX=$(grep "WID_HEX=" "$PIN_FILE" | cut -d= -f2)
if [ -z "$WID_HEX" ]; then
    echo "ERROR_BAD_PIN: No se encontro WID_HEX en el archivo."
    exit 1
fi

# 2. Capturar URL actual de la ventana segura
# Usamos el capturador existente que ya sabemos que respeta el WID
"$CAP" "$WID_HEX" "$TEMP_DIR" >/dev/null 2>&1

if [ ! -f "$TEMP_DIR/url.txt" ]; then
    echo "ERROR_CAPTURE_FAIL: No se pudo leer la URL de la ventana $WID_HEX"
    exit 1
fi

CURRENT_URL=$(cat "$TEMP_DIR/url.txt" | sed 's/^<<<//;s/>>>$//')

# 3. Validar que sea YouTube
if [[ "$CURRENT_URL" != *"youtube.com"* && "$CURRENT_URL" != *"youtu.be"* ]]; then
    echo "ERROR_NOT_YOUTUBE: La ventana esta en $CURRENT_URL"
    exit 1
fi

echo "Scanning URL: $CURRENT_URL" >&2

# 4. Extraer Datos con yt-dlp (Modo Rapido)
# --flat-playlist: No descarga videos, solo lista.
# --dump-json: Salida estructurada.
# Limitamos a 5 resultados para no saturar el contexto del LLM.

if ! command -v yt-dlp >/dev/null 2>&1; then
    echo "ERROR_MISSING_TOOL: yt-dlp no esta instalado."
    exit 1
fi

results=$(yt-dlp --flat-playlist --dump-json --playlist-end 5 "$CURRENT_URL" 2>/dev/null)

if [ -z "$results" ]; then
    echo "ERROR_NO_RESULTS: yt-dlp no devolvio datos (URL invalida o sin resultados)"
    exit 1
fi

# 5. Formatear Salida (JSON Array simple)
# Procesamos linea por linea el JSON de yt-dlp (que es un objeto JSON por linea)
echo "["
first=1
while IFS= read -r line; do
    if [ $first -eq 1 ]; then first=0; else echo ","; fi

    # Extraemos solo lo vital para el LLM usando python3.
    echo "$line" | python3 -c "import sys, json
try:
    d = json.load(sys.stdin)
    print(json.dumps({
        'id': d.get('id'),
        'title': d.get('title'),
        'duration': d.get('duration_string', 'N/A'),
        'channel': d.get('uploader', 'Unknown')
    }))
except Exception:
    pass
"
done <<< "$results"
echo "]"
