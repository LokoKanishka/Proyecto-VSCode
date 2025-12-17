# Auditoría de trazabilidad (Lucy)

- Fecha: 2025-12-16 21:06:52
- Roots: scripts, lucy_agents, external/nodo-de-voz-modular-de-lucy
- Archivos escaneados: **31**
- Hallazgos: **ALTA=0**, **MEDIA=1**, **BAJA=10**

## Hallazgos críticos (ALTA)

_No se detectaron silenciamientos evidentes a nivel heurístico._

## Hallazgos a revisar (MEDIA)

- `external/nodo-de-voz-modular-de-lucy/tts.py:64` **python:subprocess.run** — Salida capturada (PIPE/capture_output): revisá que se imprima o se escriba a logs.
  - `proc = subprocess.run(`

## Hallazgos informativos (BAJA)

- `lucy_agents/desktop_bridge.py:53` **python:subprocess.run**
  - `completed = subprocess.run([sys.executable, str(DESKTOP_AGENT), "-c", command])`
- `scripts/audit_trazabilidad.sh:4` **shell:redirection**
  - `ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"`
- `scripts/audit_trazabilidad.sh:14` **shell:redirection**
  - `if command -v code >/dev/null 2>&1; then`
- `scripts/check_deps.sh:10` **shell:redirection**
  - `if command -v "$dep" >/dev/null 2>&1; then`
- `scripts/lucy_desktop_agent.py:71` **python:subprocess.run**
  - `result = subprocess.run(args)`
- `scripts/lucy_voice_wakeword_loop.sh:8` **shell:redirection**
  - `SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"`
- `scripts/lucy_voice_web_agent_voice.py:200` **python:subprocess.run**
  - `subprocess.run(cmd, shell=True, check=False)`
- `scripts/searxng_down.sh:8` **shell:redirection**
  - `if ! command -v docker >/dev/null 2>&1; then`
- `scripts/searxng_logs.sh:8` **shell:redirection**
  - `if ! command -v docker >/dev/null 2>&1; then`
- `scripts/searxng_up.sh:8` **shell:redirection**
  - `if ! command -v docker >/dev/null 2>&1; then`

## Recomendación mínima para el próximo paso

1) Elegir **1 solo** punto de ejecución de comandos (bridge) y estandarizar:
- log de inicio/fin
- comando exacto
- exit_code
- stdout/stderr (si se capturan)
2) Repetir en el resto.
