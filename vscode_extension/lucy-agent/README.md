# Lucy Agent VS Code Extension

Extensión mínima para exponer un WebSocket local y permitir comandos remotos desde Lucy.

## Build

```bash
cd vscode_extension/lucy-agent
npm install
npm run build
```

## Uso

1. Instalar la extensión generada en VS Code.
2. Al activarse, abre un WebSocket en `ws://127.0.0.1:8765`.
3. Enviar mensajes JSON con formato:

```json
{"type":"command","action":"openFile","args":{"path":"/ruta/al/archivo.py"}}
```

Acciones soportadas:
- `openFile`
- `insertText`
- `saveFile`
- `runCommand`
