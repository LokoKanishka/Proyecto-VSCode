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
- `scripts/bridge_multi_node_demo.sh`
- `/api/bridge_metrics` responde

## Smokes
- `scripts/run_all_smokes.sh`
- `scripts/ci_smoke.sh`
