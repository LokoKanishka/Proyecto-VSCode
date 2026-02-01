# Swarm distribuido (WS Bridge)

## Objetivo
Conectar múltiples nodos de Swarm vía WebSocket, compartiendo eventos y métricas.

## Prerrequisitos
- `LUCY_WS_GATEWAY=1` en el nodo principal.
- `LUCY_WS_BRIDGE_URLS=ws://host:8766` en nodos remotos.

## Ejemplo rápido
```bash
./scripts/bridge_multi_node_demo.sh
```

## Smoke remoto (multi-host)
Configura `LUCY_WS_REMOTE_URL` con el gateway remoto y ejecuta:
```bash
./scripts/bridge_remote_smoke.sh
```

## Variables clave
- `LUCY_WS_BRIDGE_URLS`: lista separada por coma.
- `LUCY_WS_BRIDGE_TOPICS`: tópicos a replicar (`broadcast,final_response`).
- `LUCY_WS_BRIDGE_MAX_HOPS`: límite de hops para evitar loops.
- `LUCY_WS_BRIDGE_BACKLOG_WARN`: umbral de backlog.
- `LUCY_WS_BRIDGE_TOKEN`: token simple de auth (gateway + bridge).
- `LUCY_WS_TLS_CERT` / `LUCY_WS_TLS_KEY`: cert/key TLS para gateway.
- `LUCY_WS_TLS_CA`: CA para clients bridge.

## Métricas
- `logs/bridge_metrics.jsonl` guarda latencia/backlog.
- `/api/bridge_metrics` expone métricas recientes en la UI.
