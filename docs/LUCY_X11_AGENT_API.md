# Lucy X11 Agent API

## Introduccion
Este documento define el contrato entre la capa de decision de Lucy y el
ejecutor grafico X11. Describe acciones, entradas, salidas y errores
esperados.
No es una implementacion, no describe herramientas internas ni detalles de
UI. Tampoco define logica de razonamiento o percepcion.
Este API define el cuerpo grafico de Lucy: el conjunto de acciones mediante
las cuales Lucy puede actuar y verificar efectos en un entorno X11.

## Principios de diseno
- Acciones explicitas, atomicas y auditables.
- Cada accion tiene entrada, salida y errores definidos.
- Lucy no asume exito: siempre verifica.
- Fallos y timeouts deben ser visibles y deterministas.
- No hay estado implicito: toda accion debe ser verificable mediante otra
  accion explicita.

## Acciones soportadas
- `list_windows`
- `find_window <pattern>`
- `focus_window <wid>`
- `send_keys <wid> <keys>`
- `type_text <wid> <text>`
- `screenshot <wid|root>`

### list_windows
Descripcion:
- Lista todas las ventanas visibles para el servidor X11.

Parametros:
- Ninguno.

Salida esperada (formato):
- Cero o mas lineas con el formato:
  `<WID>\t<DESKTOP>\t<CLASS>\t<TITLE>`
- `WID` en formato hexadecimal (por ejemplo `0x03a00007`).

Errores posibles:
- `ERR E_EXEC_FAIL <detalle>` si la herramienta falla.
- `ERR E_TIMEOUT` si el comando excede el timeout.

### find_window <pattern>
Descripcion:
- Busca una ventana cuyo `CLASS` o `TITLE` contenga el patron.
- Si hay multiples coincidencias, devuelve la primera en orden de aparicion
  y no garantiza estabilidad. Para control estricto, usar `list_windows`
  y filtrar en la capa de decision.

Parametros:
- `pattern`: texto plano, busqueda case-insensitive por substring.

Salida esperada (formato):
- Una linea con el formato:
  `<WID>\t<CLASS>\t<TITLE>`

Errores posibles:
- `ERR E_NOT_FOUND` si no hay coincidencias.
- `ERR E_INVALID_ARG` si `pattern` esta vacio.
- `ERR E_EXEC_FAIL <detalle>` o `ERR E_TIMEOUT`.

### focus_window <wid>
Descripcion:
- Lleva el foco a la ventana indicada.

Parametros:
- `wid`: ID de ventana en hexadecimal.

Salida esperada (formato):
- `OK`

Errores posibles:
- `ERR E_INVALID_ARG` si el WID es invalido.
- `ERR E_NOT_FOUND` si el WID no existe.
- `ERR E_EXEC_FAIL <detalle>` o `ERR E_TIMEOUT`.

### send_keys <wid> <keys>
Descripcion:
- Envia una secuencia de teclas a una ventana.

Parametros:
- `wid`: ID de ventana en hexadecimal.
- `keys`: secuencia en sintaxis tipo `xdotool` (ej: `ctrl+l`, `Return`).

Salida esperada (formato):
- `OK`

Errores posibles:
- `ERR E_INVALID_ARG` si faltan parametros.
- `ERR E_NOT_FOUND` si el WID no existe.
- `ERR E_EXEC_FAIL <detalle>` o `ERR E_TIMEOUT`.

### type_text <wid> <text>
Descripcion:
- Escribe texto literal en la ventana indicada.

Parametros:
- `wid`: ID de ventana en hexadecimal.
- `text`: texto literal (sin interpretar escapes).

Salida esperada (formato):
- `OK`

Errores posibles:
- `ERR E_INVALID_ARG` si faltan parametros.
- `ERR E_NOT_FOUND` si el WID no existe.
- `ERR E_EXEC_FAIL <detalle>` o `ERR E_TIMEOUT`.

### screenshot <wid|root>
Descripcion:
- Captura una imagen PNG de una ventana o de la pantalla completa.

Parametros:
- `wid`: ID de ventana en hexadecimal, o `root` para captura completa.

Salida esperada (formato):
- Una linea con el path del archivo creado:
  `PATH <ruta>`
- Puede incluir metadatos opcionales:
  `PATH <ruta> WIDTH <w> HEIGHT <h>`

Errores posibles:
- `ERR E_INVALID_ARG` si el parametro es invalido.
- `ERR E_NOT_FOUND` si el WID no existe.
- `ERR E_EXEC_FAIL <detalle>` o `ERR E_TIMEOUT`.

## Notas sobre timeouts
- Cada accion debe ejecutarse con un timeout corto (por defecto 2s).
- En timeout, la respuesta debe ser `ERR E_TIMEOUT` y el comando debe
  terminarse de forma segura.

## Codigos de error estandar
- `E_INVALID_ARG`
- `E_NOT_FOUND`
- `E_EXEC_FAIL`
- `E_TIMEOUT`

Regla:
- Ninguna accion debe inventar nuevos codigos sin documentarlos aqui.
