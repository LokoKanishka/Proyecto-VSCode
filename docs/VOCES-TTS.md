# Voces TTS Disponibles

## Voces en Español (es_ES)

Mimic3 tiene dos voces masculinas en español instaladas:

- `es_ES/m-ailabs_low` - Voz masculina (predeterminada anterior)
- `es_ES/carlfm_low` - Voz masculina alternativa (actual)

## Nota sobre Voces Femeninas

Actualmente Mimic3 no tiene voces femeninas en español disponibles en los repositorios oficiales.

### Opciones para voz femenina:

1. **Usar voz femenina en inglés** (no recomendado para español):
   - `en_US/ljspeech_low` - Voz femenina clara

2. **Instalar voz custom**:
   - Entrenar un modelo custom con Coqui TTS
   - Usar otro motor TTS (pyttsx3, gTTS, etc.)

3. **Esperar a que se publiquen más voces** en el repositorio de Mimic3

## Cambiar la Voz

Para cambiar la voz, editar `lucy_voice/pipeline_lucy_voice.py`:

```python
class LucyPipelineConfig:
    tts_voice: str = "es_ES/carlfm_low"  # Cambiar aquí
```
