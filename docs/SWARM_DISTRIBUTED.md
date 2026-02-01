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

## Variables clave
- `LUCY_WS_BRIDGE_URLS`: lista separada por coma.
- `LUCY_WS_BRIDGE_TOPICS`: tópicos a replicar (`broadcast,final_response`).
- `LUCY_WS_BRIDGE_MAX_HOPS`: límite de hops para evitar loops.
- `LUCY_WS_BRIDGE_BACKLOG_WARN`: umbral de backlog.

## Métricas
- `logs/bridge_metrics.jsonl` guarda latencia/backlog.
- `/api/bridge_metrics` expone métricas recientes en la UI.
