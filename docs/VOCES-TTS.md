# Voces TTS Disponibles

## Voces en Español (es_ES)

Mimic3 incluye modelos multispeaker; el speaker se elige con el formato `idioma/modelo#speaker`.

- `es_ES/m-ailabs_low#karen_savage` - Voz femenina (predeterminada actual en Lucy Voz v2).
- `es_ES/m-ailabs_low` - Voz masculina neutra del mismo paquete.
- `es_ES/carlfm_low` - Voz masculina alternativa.

## Cambiar la Voz

1. Ajustar `tts_voice` en `config.yaml` (raíz del repo) o en `external/nodo-de-voz-modular-de-lucy/config.yaml`.
2. Ejecutar el nodo de voz modular normalmente (`scripts/lucy_voice_modular_node.sh`); el valor se pasa directo a Mimic3.
