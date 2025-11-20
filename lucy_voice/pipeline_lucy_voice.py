from __future__ import annotations

import logging
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"


@dataclass
class LucyPipelineConfig:
    whisper_model_name: str = "Systran/faster-whisper-small"  # Volvemos a small para mejor precisión
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    ollama_model: str = "gpt-oss:20b"
    ollama_host: str = "http://localhost:11434"
    tts_voice: str = "en_US/ljspeech_low"  # Voz femenina neural
    # segundos de audio que se graban después de la activación
    record_seconds: float = 4.0


class LucyVoicePipeline:
    def __init__(self, config: Optional[LucyPipelineConfig] = None) -> None:
        self.log = logging.getLogger("LucyVoicePipeline")
        self.config = config or LucyPipelineConfig()
        self.interrupt_flag = threading.Event()  # Flag para interrupción
        self.is_speaking = False  # Estado de TTS

        self.log.info(
            "Cargando modelo Whisper %r (device=%s, compute_type=%s)...",
            self.config.whisper_model_name,
            self.config.whisper_device,
            self.config.whisper_compute_type,
        )
        self.whisper_model = WhisperModel(
            self.config.whisper_model_name,
            device=self.config.whisper_device,
            compute_type=self.config.whisper_compute_type,
        )

    # ----------------- Audio -----------------

    def _record_fixed(self, seconds: float) -> np.ndarray:
        frames = int(seconds * SAMPLE_RATE)
        self.log.info(
            "[LucyVoicePipeline] Grabando audio fijo: %.1fs a %d Hz...",
            seconds,
            SAMPLE_RATE,
        )
        audio = sd.rec(
            frames,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
        )
        sd.wait()
        self.log.info(
            "[LucyVoicePipeline] Audio grabado: %.2fs",
            len(audio) / SAMPLE_RATE,
        )
        # (frames, 1) -> (frames,)
        return audio.reshape(-1)

    def _record_until_silence(self, max_seconds: float = 10.0, silence_duration: float = 1.0) -> np.ndarray:
        """
        Graba audio hasta detectar silencio prolongado usando VAD.
        
        Args:
            max_seconds: Tiempo máximo de grabación
            silence_duration: Segundos de silencio para detener
        """
        vad = webrtcvad.Vad(2)  # Aggressiveness 0-3, 2 es moderado
        frame_duration_ms = 30  # webrtcvad soporta 10, 20, 30 ms
        frame_size = int(SAMPLE_RATE * frame_duration_ms / 1000)
        
        self.log.info("[LucyVoicePipeline] Grabando con VAD (max %.1fs)...", max_seconds)
        
        frames = []
        silence_frames = 0
        silence_threshold = int(silence_duration * 1000 / frame_duration_ms)
        max_frames = int(max_seconds * 1000 / frame_duration_ms)
        
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE) as stream:
            for _ in range(max_frames):
                audio_chunk, _ = stream.read(frame_size)
                audio_f32 = audio_chunk[:, 0]
                frames.append(audio_f32)
                
                # Convertir a int16 para VAD
                audio_int16 = (audio_f32 * 32767).astype(np.int16).tobytes()
                
                is_speech = vad.is_speech(audio_int16, SAMPLE_RATE)
                
                if is_speech:
                    silence_frames = 0
                else:
                    silence_frames += 1
                    
                if silence_frames >= silence_threshold:
                    self.log.info("[LucyVoicePipeline] Silencio detectado, finalizando grabación.")
                    break
        
        audio = np.concatenate(frames)
        self.log.info("[LucyVoicePipeline] Audio grabado: %.2fs", len(audio) / SAMPLE_RATE)
        return audio

    # ----------------- ASR -----------------

    def _transcribe(self, audio: np.ndarray) -> Tuple[str, str]:
        """
        Transcribe audio en memoria usando Whisper.
        Devuelve (texto, idioma_detectado).
        """
        audio_f32 = audio.astype("float32")

        segments, info = self.whisper_model.transcribe(
            audio_f32,
            beam_size=1,
            vad_filter=False,
        )

        text_chunks = []
        for seg in segments:
            text_chunks.append(seg.text.strip())
        text = " ".join(t for t in text_chunks if t)

        lang = info.language or "unknown"
        self.log.info(
            "[LucyVoicePipeline] Texto reconocido: %r (lang=%s, p=%.2f)",
            text,
            lang,
            info.language_probability or 0.0,
        )
        return text, lang

    # ----------------- LLM (Ollama) -----------------

    def _extract_visible_answer(self, raw: str) -> str:
        """
        Extrae solo la parte 'visible' cuando el modelo devuelve
        trazas tipo 'Thinking...' y '...done thinking.'.
        """
        marker = "...done thinking."
        if marker in raw:
            visible = raw.split(marker, 1)[1].strip()
            if visible:
                return visible

        # Fallbacks por si el modelo usa otros prefijos
        for token in ["Respuesta:", "Answer:", "Final answer:", "Assistant:"]:
            if token in raw:
                tail = raw.split(token, 1)[1].strip()
                if tail:
                    return tail

        return raw

    def _call_ollama(self, prompt: str, tool_result: Optional[str] = None) -> str:
        """
        Llama al modelo local de Ollama via CLI (`ollama run`).
        """
        self.log.info(
            "[LucyVoicePipeline] Llamando a Ollama (modelo=%s)...",
            self.config.ollama_model,
        )

        system_prompt = (
            "Sos Lucy, una asistente de voz local. "
            "Podés usar herramientas respondiendo SOLO con un JSON válido. "
            "Herramientas disponibles: "
            "abrir_aplicacion(nombre), abrir_url(url), tomar_captura(), escribir_texto(texto). "
            "Ejemplo: {\"tool\": \"abrir_aplicacion\", \"args\": [\"firefox\"]} "
            "Si no usás herramientas, respondé brevemente en español rioplatense."
        )

        if tool_result:
            full_prompt = (
                f"{system_prompt}\n"
                f"Resultado de la herramienta: {tool_result}\n"
                "Explicáselo al usuario brevemente."
            )
        else:
            full_prompt = (
                f"{system_prompt}\n"
                f"Usuario: {prompt}"
            )

        try:
            proc = subprocess.run(
                ["ollama", "run", self.config.ollama_model],
                input=full_prompt.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.log.error("Error Ollama: %s", e)
            return "Tuve un problema con el modelo."

        raw = proc.stdout.decode("utf-8", errors="ignore").strip()
        self.log.debug("[Ollama raw] %r", raw)
        
        return self._extract_visible_answer(raw)

    # ----------------- TTS (Mimic3) -----------------

    def _speak(self, text: str) -> bool:
        """
        Usa mimic3 por CLI con soporte para interrupción.
        Returns True si fue interrumpido, False si completó.
        """
        self.log.info(
            "[LucyVoicePipeline] Sintetizando audio con Mimic3 (voz=%s)...",
            self.config.tts_voice,
        )

        tmp_wav = Path("lucy_tts_output.wav")

        try:
            proc = subprocess.run(
                ["mimic3", "--voice", self.config.tts_voice],
                input=text.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.log.error("Error mimic3: %s", e)
            return False

        tmp_wav.write_bytes(proc.stdout)

        try:
            import soundfile as sf
            data, sr = sf.read(str(tmp_wav), dtype="float32")
            
            # IMPORTANTE: Setear is_speaking ANTES de iniciar monitor y reproducción
            self.is_speaking = True
            self.interrupt_flag.clear()
            
            # Iniciar monitor DESPUÉS de setear is_speaking
            monitor_thread = self._start_interruption_monitor()
            
            # Usar OutputStream explícito para poder detenerlo
            stream = sd.OutputStream(samplerate=sr, channels=1, dtype='float32')
            stream.start()
            
            # Reproducir en chunks pequeños para poder interrumpir rápido
            chunk_size = int(sr * 0.1)  # 100ms chunks
            interrupted = False
            
            for i in range(0, len(data), chunk_size):
                if self.interrupt_flag.is_set():
                    self.log.info("[LucyVoicePipeline] ¡Interrumpido! Deteniendo audio...")
                    stream.stop()
                    stream.close()
                    interrupted = True
                    break
                
                chunk = data[i:i+chunk_size]
                stream.write(chunk)
            
            if not interrupted:
                stream.stop()
                stream.close()
            
            self.is_speaking = False
            return interrupted
            
        except Exception as e:
            self.log.error("Error reproduciendo audio TTS: %s", e)
            self.is_speaking = False
            return False
        finally:
            try:
                tmp_wav.unlink(missing_ok=True)
            except Exception:
                pass

    def _start_interruption_monitor(self) -> threading.Thread:
        """
        Inicia un thread que monitorea audio para detectar voz fuerte (posible interrupción).
        Usa detección de energía en lugar de transcripción para evitar conflictos.
        """
        def monitor():
            try:
                self.log.info("[Monitor] Iniciando monitor de interrupción...")
                # Monitorear energía de audio mientras Lucy habla
                energy_threshold = 0.01  # Umbral más bajo para mayor sensibilidad
                consecutive_speech_chunks = 0
                required_chunks = 2  # Solo 2 chunks para ser más rápido
                
                while self.is_speaking:
                    # Grabar chunk pequeño
                    audio = sd.rec(
                        int(SAMPLE_RATE * 0.2),  # 200ms más rápido
                        samplerate=SAMPLE_RATE,
                        channels=CHANNELS,
                        dtype=DTYPE
                    )
                    sd.wait()
                    
                    # Calcular energía RMS
                    audio_f32 = audio.reshape(-1).astype("float32")
                    energy = np.sqrt(np.mean(audio_f32**2))
                    
                    # Log periódico para debug
                    if int(energy * 1000) % 5 == 0:  # Log cada ~5 iteraciones
                        self.log.debug(f"[Monitor] Energía: {energy:.4f}, Chunks: {consecutive_speech_chunks}")
                    
                    # Detectar si hay voz (energía alta)
                    if energy > energy_threshold:
                        consecutive_speech_chunks += 1
                        self.log.info(f"[Monitor] Voz detectada! Energía: {energy:.4f}, Chunks: {consecutive_speech_chunks}/{required_chunks}")
                        if consecutive_speech_chunks >= required_chunks:
                            self.log.info(f"[Monitor] ¡INTERRUMPIENDO! (energía: {energy:.4f})")
                            self.interrupt_flag.set()
                            return
                    else:
                        if consecutive_speech_chunks > 0:
                            self.log.debug(f"[Monitor] Reset chunks (energía baja: {energy:.4f})")
                        consecutive_speech_chunks = 0
                
                self.log.info("[Monitor] Monitor finalizado (Lucy dejó de hablar)")
                            
            except Exception as e:
                self.log.error(f"Error en monitor de interrupción: {e}")
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        return thread

    # ----------------- Roundtrip completo -----------------

    def run_mic_llm_roundtrip_once(self, use_vad: bool = True) -> str:
        """
        1. Graba audio (con VAD o tiempo fijo).
        2. Transcribe.
        3. Llama a Ollama (detecta tools).
        4. Responde.
        
        Returns:
            "continue" - seguir en modo conversación
            "stop" - salir del modo conversación (comando de desactivación)
            "no_speech" - no se detectó voz
        """
        # Grabar con VAD o tiempo fijo
        if use_vad:
            audio = self._record_until_silence(max_seconds=10.0, silence_duration=1.5)
        else:
            seconds = self.config.record_seconds
            audio = self._record_fixed(seconds)
            
        text, _lang = self._transcribe(audio)

        if not text.strip():
            self._speak("No escuché nada.")
            return "no_speech"

        # Detectar comandos de desactivación
        lowered = text.lower()
        deactivation_keywords = [
            "lucy desactiva", "desactiva lucy", "desactivate",
            "lucy apagate", "apagate lucy",
            "chau lucy", "lucy chau", "adiós lucy", "lucy adiós",
            "hasta luego", "nos vemos"
        ]
        
        for keyword in deactivation_keywords:
            if keyword in lowered:
                self._speak("Chau, me apago.")
                return "stop"

        # 1er llamado al LLM
        reply = self._call_ollama(text)
        
        # Detectar JSON tool
        import json
        from lucy_voice import lucy_tools

        try:
            # Intentar parsear JSON. A veces el modelo pone texto antes o después.
            # Buscamos el primer '{' y el último '}'
            start = reply.find("{")
            end = reply.rfind("}")
            
            if start != -1 and end != -1:
                json_str = reply[start:end+1]
                data = json.loads(json_str)
                
                if "tool" in data:
                    tool_name = data["tool"]
                    args = data.get("args", [])
                    
                    self.log.info(f"Detectada herramienta: {tool_name} {args}")
                    self._speak(f"Voy a {tool_name.replace('_', ' ')}.")
                    
                    # Ejecutar
                    result = lucy_tools.execute_tool(tool_name, args)
                    
                    # 2do llamado al LLM con el resultado
                    final_reply = self._call_ollama(text, tool_result=result)
                    self.log.info(f"Lucy (post-tool): {final_reply}")
                    self._speak(final_reply)
                    return "continue"
                    
        except Exception as e:
            self.log.warning(f"Error procesando posible tool: {e}")

        # Si no hubo tool o falló, hablar normal
        self.log.info("Lucy: %s", reply)
        self._speak(reply)

        return "continue"


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s",
    )


def main() -> None:
    _setup_logging()
    main_log = logging.getLogger("LucyVoicePipelineMain")

    main_log.info(
        "Iniciando LucyVoicePipeline en modo texto+voz "
        "(push-to-talk simple, grabación fija)."
    )

    pipeline = LucyVoicePipeline()

    try:
        while True:
            input("Enter para grabar (Ctrl+C para salir)...")
            should_stop = pipeline.run_mic_llm_roundtrip_once()
            if should_stop:
                main_log.info("Lucy pidió apagarse por voz. Terminando.")
                break
    except KeyboardInterrupt:
        main_log.info("Interrupción por teclado. Chau.")


if __name__ == "__main__":
    main()
