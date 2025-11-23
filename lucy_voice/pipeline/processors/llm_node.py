from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, TextFrame
from lucy_voice.llm.ollama_wrapper import OllamaLLM
from lucy_voice.config import LucyConfig
from lucy_voice.tools.lucy_tools import ToolManager
import logging

import asyncio

class OllamaLLMProcessor(FrameProcessor):
    def __init__(self, config: LucyConfig):
        super().__init__()
        self.llm = OllamaLLM(config)
        self.tools = ToolManager()
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
                # Run blocking LLM call in thread
                response = await asyncio.to_thread(self.llm.generate_response, text)
                
                # Check for tools
                tool_call = self.llm.extract_tool_call(response)
                if tool_call:
                    self.log.info(f"Tool call detected: {tool_call}")
                    
                    tool_name = tool_call.get("tool")
                    tool_args = tool_call.get("args", [])
                    
                    # Notify user we are executing?
                    # Maybe yield a TextFrame("Voy a abrir...")?
                    # For now, just execute.
                    
                    # Execute
                    # ToolManager.execute expects list of args
                    result = self.tools.execute(tool_name, tool_args)
                    self.log.info(f"Tool result: {result}")
                    
                    # Feed result back to LLM
                    final_response = await asyncio.to_thread(self.llm.generate_response, text, tool_result=result)
                    self.log.info(f"LLM Final Response: {final_response}")
                    
                    await self.push_frame(TextFrame(final_response), direction)
                else:
                    await self.push_frame(TextFrame(response), direction)
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

