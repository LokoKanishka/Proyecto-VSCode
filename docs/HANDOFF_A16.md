# Handoff A16 - YouTube Doctor (PID-based verify)

## Objetivo
Hacer que `verify_youtube_doctor.sh` sea autonomo y deterministico:
- Lanza Chrome clean con perfil nuevo.
- Resuelve WID por PID (no por titulo).
- Hace smoke capture confiable.
- Ejecuta test deterministico de placeholder (rc=10 + evidencia).
- Ejecuta watcher normal (rc=0) y termina OK.

## Scripts clave

- `scripts/youtube_open_clean.sh [URL] [URL2]`
  - Abre Chrome clean y siempre imprime `PID=...`.
  - Usa `--user-data-dir` temporal.

- `scripts/chrome_wid_by_pid.sh <PID>`
  - Resuelve WID_HEX de una ventana Chrome perteneciente al PID.

- `scripts/chrome_capture_active_tab.sh <WID_HEX> [OUTDIR]`
  - Activa ventana, enfoca omnibox, limpia clipboard, reintenta.
  - Valida `^https?://` y devuelve rc=11 si no logra URL valida.

- `scripts/yt_force_placeholder_clean.sh [SECONDS] [INTERVAL]`
  - Abre Chrome clean con 2 tabs (YouTube + placeholder).
  - Fija tab 2 y corre watcher.
  - Exige rc=10 + evidencia (hit.png, url.txt, title.txt).

- `scripts/yt_watch_until_bad_url.sh [SECONDS] [INTERVAL] [WID_HEX]`
  - Contrato:
    - rc=0: no bug
    - rc=10: bug detectado (OUTDIR con evidencia)
    - rc=11: clipboard unreliable
    - rc=3: no WID
  - Siempre imprime `HIT_BAD_URL=`, `SAVED=`, `OUTDIR=`.

## Verify (boton rojo)

```
./scripts/verify_youtube_doctor.sh
```

Debe imprimir `YT_DOCTOR_OK` y exit code 0. Internamente:
- Corre tests `tests.test_yt_doctor_rules`.
- Ejecuta el placeholder test (rc=10 esperado).
- Abre Chrome clean y corre watcher normal (rc=0 esperado).

## Evidencia (OUTDIR)

Cuando hay hit, el OUTDIR contiene:
- `url.txt`
- `title.txt`
- `wid_hex.txt`
- `screenshot.png` y/o `hit.png`
- `trace.tsv`

