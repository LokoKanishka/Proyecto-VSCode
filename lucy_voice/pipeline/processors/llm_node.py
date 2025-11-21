from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, TextFrame
from lucy_voice.llm.ollama_wrapper import OllamaLLM
from lucy_voice.config import LucyConfig
import logging

class OllamaLLMProcessor(FrameProcessor):
    def __init__(self, config: LucyConfig):
        super().__init__()
        self.llm = OllamaLLM(config)
        self.log = logging.getLogger("OllamaLLMProcessor")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, TextFrame):
            text = frame.text.strip()
            if text:
                self.log.info(f"Processing text: {text}")
                response = self.llm.generate_response(text)
                
                # Check for tools (basic implementation)
                tool_call = self.llm.extract_tool_call(response)
                if tool_call:
                    # If tool detected, we might want to emit a ToolCallFrame?
                    # Or handle it here?
                    # For now, just emit the text response (which might include tool JSON)
                    # Ideally, we'd have a ToolProcessor next.
                    pass
                
                await self.push_frame(TextFrame(response), direction)
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)
