import logging
import time
from typing import Optional

from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.audio import AudioHandler
from lucy_voice.asr.fast_whisper_wrapper import WhisperASR
from lucy_voice.tts.mimic_tts import Mimic3TTS
from lucy_voice.llm.ollama_wrapper import OllamaLLM
from lucy_voice.tools.lucy_tools import ToolManager

class LucyOrchestrator:
    def __init__(self, config: Optional[LucyConfig] = None):
        self.config = config or LucyConfig()
        self.log = logging.getLogger("LucyOrchestrator")
        
        self.log.info("Inicializando componentes de Lucy...")
        self.audio = AudioHandler(self.config)
        self.asr = WhisperASR(self.config)
        self.tts = Mimic3TTS(self.config)
        self.llm = OllamaLLM(self.config)
        self.tools = ToolManager()
        self.log.info("Lucy lista.")

    def speak(self, text: str) -> bool:
        """
        Sintetiza y reproduce audio.
        Returns True si fue interrumpido.
        """
        audio_data, sr = self.tts.synthesize(text)
        if audio_data is None:
            return False
            
        return self.audio.play_audio(audio_data, sr)

    def run_turn(self, use_vad: bool = True) -> str:
        """
        Ejecuta un turno de conversación:
        Record -> Transcribe -> LLM -> Tool? -> TTS
        
        Returns:
            "continue"
            "stop"
            "no_speech"
        """
        # 1. Grabar
        if use_vad:
            audio = self.audio.record_until_silence(
                max_seconds=self.config.max_record_seconds,
                silence_duration=self.config.silence_duration_stop
            )
        else:
            audio = self.audio.record_fixed(self.config.record_seconds_fixed)
            
        if len(audio) == 0:
            return "no_speech"

        # 2. Transcribir
        text, _lang = self.asr.transcribe(audio)
        
        if not text.strip():
            self.speak("No escuché nada.")
            return "no_speech"

        # 3. Comandos de desactivación
        lowered = text.lower()
        deactivation_keywords = [
            "lucy desactiva", "desactiva lucy", "desactivate",
            "lucy apagate", "apagate lucy",
            "chau lucy", "lucy chau", "adiós lucy", "lucy adiós",
            "hasta luego", "nos vemos"
        ]
        
        for keyword in deactivation_keywords:
            if keyword in lowered:
                self.speak("Chau, me apago.")
                return "stop"

        # 4. LLM
        reply = self.llm.generate_response(text)
        
        # 5. Tools
        tool_data = self.llm.extract_tool_call(reply)
        
        if tool_data:
            tool_name = tool_data.get("tool")
            args = tool_data.get("args", [])
            
            self.log.info(f"Detectada herramienta: {tool_name} {args}")
            self.speak(f"Voy a {tool_name.replace('_', ' ')}.")
            
            result = self.tools.execute(tool_name, args)
            
            # 2do llamado al LLM
            final_reply = self.llm.generate_response(text, tool_result=result)
            self.log.info(f"Lucy (post-tool): {final_reply}")
            self.speak(final_reply)
            return "continue"

        # 6. Respuesta normal
        self.log.info(f"Lucy: {reply}")
        self.speak(reply)
        
        return "continue"
