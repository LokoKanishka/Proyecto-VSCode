# Handoff A14 - YouTube Doctor

## Objetivo
Capturar evidencia automatica cuando aparece el placeholder/NXDOMAIN o errores internos en Chrome, sin depender del foco ni de muestreo manual. El watcher NO corta por navegaciones normales (Google, cuentas, consent, etc.).

## Scripts clave

- `scripts/chrome_capture_active_tab.sh <WID_HEX> [OUTDIR]`
  - Captura URL, title y screenshot del tab activo.
  - Salida: `OUTDIR=...`, `WID_HEX=...`, `TITLE=...`, `URL=...`, `SCREENSHOT=...`.

- `scripts/yt_watch_until_bad_url.sh [SECONDS] [INTERVAL] [WID_HEX]`
  - Observa la pestaña y corta solo por senales de bug (placeholder, chrome-error, DNS).
  - Codigos:
    - `0`: no hubo bad url dentro del tiempo.
    - `10`: bad url detectada (se guarda evidencia).
    - `11`: no se pudo leer URL de forma confiable (clipboard vacio repetido).
    - `3`: no WID o multiples WID.
  - Salida estandar:
    - `OUTDIR=...` (vacio si no aplica)
    - `HIT_BAD_URL=...` (vacio si no aplica)
    - `SAVED=0|1`

- `scripts/verify_youtube_doctor.sh`
  - Verifica dependencias, corre tests y hace un smoke de captura.

## Como correr el watcher

1. Abrir YouTube en Chrome.
2. Obtener WID (hex) con `xdotool search --onlyvisible --class 'google-chrome' | tail -n 1` y convertir a hex:
   `printf '0x%08x' "$WID"`.
3. Ejecutar:
   `./scripts/yt_watch_until_bad_url.sh 60 1 0xXXXXXXXX`

## Interpretar OUTDIR

Cuando hay evidencia, el OUTDIR contiene:
- `url.txt` - URL copiada del omnibox.
- `title.txt` - titulo de la ventana.
- `screenshot.png` y `hit.png` - captura del estado.
- `trace.tsv` - linea con timestamp, WID, title y URL.
