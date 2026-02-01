# Checklist de despliegue local

## Audio
- `ffmpeg` instalado
- `soundfile` instalado
- `scripts/check_voice_pipeline.sh`

## Swarm/WS
- `LUCY_SWARM_CONSOLE=1`
- `LUCY_WS_GATEWAY=1`
- `scripts/bridge_smoke.sh`

## Bridge distribuido
- `LUCY_WS_BRIDGE_URLS` configurado
- `LUCY_WS_BRIDGE_TOKEN` configurado si hay auth
- `LUCY_WS_TLS_CERT`/`LUCY_WS_TLS_KEY` si se usa TLS
- `scripts/bridge_multi_node_demo.sh`
- `scripts/bridge_tls_token_demo.sh`
- `/api/bridge_metrics` responde

## Smokes
- `scripts/run_all_smokes.sh`
- `scripts/ci_smoke.sh`
