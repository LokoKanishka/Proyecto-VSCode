# ADR 0002: H1 usa OpenClaw npm como upstream de Moltbot

## Estado
Aceptada

## Contexto
H1 requiere instalación vanilla de upstream y ejecución verificable (`--version` + comando mínimo).

## Decisión
Usar paquete npm `openclaw@latest` en prefijo local del repo (`runtime/openclaw`) y exponer wrapper estable en `runtime/wrapper/openclaw.sh`.

## Consecuencias
- Instalación en user-space, sin tocar el sistema global.
- Verificación reproducible con `scripts/verify_upstream.sh`.
- Requiere Node.js >= 22.12.0 según `engines` del paquete upstream.
