# Protocolo de Herramientas de Lucy (Lucy Tools)

Este documento define cómo el LLM debe solicitar la ejecución de acciones en el sistema.

## Formato de Respuesta

Cuando Lucy decide usar una herramienta, su respuesta debe ser **exclusivamente** un objeto JSON con la siguiente estructura:

```json
{
  "tool": "nombre_de_la_herramienta",
  "args": ["argumento1", "argumento2"]
}
```

Si la respuesta no es un JSON válido, se interpretará como texto para ser hablado por el TTS.

## Herramientas Disponibles

### `abrir_aplicacion`
Abre una aplicación instalada en el sistema.
- **Argumentos**: `[nombre_app]` (string)
- **Ejemplo**: `{"tool": "abrir_aplicacion", "args": ["firefox"]}`

### `abrir_url`
Abre una URL en el navegador predeterminado.
- **Argumentos**: `[url]` (string)
- **Ejemplo**: `{"tool": "abrir_url", "args": ["https://www.google.com"]}`

### `tomar_captura`
Toma una captura de pantalla y la guarda en la carpeta de imágenes.
- **Argumentos**: Ninguno (o opcionalmente un nombre de archivo)
- **Ejemplo**: `{"tool": "tomar_captura", "args": []}`

### `escribir_texto`
Escribe texto simulando el teclado.
- **Argumentos**: `[texto]` (string)
- **Ejemplo**: `{"tool": "escribir_texto", "args": ["Hola mundo"]}`

## Flujo de Ejecución

1. **Usuario**: "Abrí el navegador".
2. **LLM**: Genera `{"tool": "abrir_aplicacion", "args": ["firefox"]}`.
3. **Sistema**:
    - Detecta JSON.
    - Ejecuta la función `abrir_aplicacion("firefox")`.
    - Captura el resultado (ej: "Se abrió firefox").
4. **Sistema -> LLM**: Envía el resultado como contexto ("Tool output: Se abrió firefox").
5. **LLM**: Genera respuesta final hablada ("Listo, abrí Firefox").
6. **TTS**: Dice "Listo, abrí Firefox".
