# Lucy Voice Architecture

## Overview
Lucy Voice is a local, voice-controlled assistant that uses a modular pipeline based on [Pipecat](https://github.com/pipecat-ai/pipecat). It processes audio input, detects wake words, transcribes speech, generates responses using an LLM, and synthesizes speech.

## Pipeline Structure
The core of the system is a linear pipeline of processors:

1.  **AudioInputNode**: Captures audio from the microphone (16kHz, Mono).
2.  **WakeWordNode**: Uses `openWakeWord` to detect activation phrases (e.g., "Hola Lucy"). It blocks audio until the wake word is detected.
3.  **VADNode**: Uses `webrtcvad` to detect voice activity. It emits `UserStartedSpeakingFrame` and `UserStoppedSpeakingFrame` to signal speech segments.
4.  **WhisperASRProcessor**: Buffers audio and transcribes it using `faster-whisper` when speech ends. Emits `TextFrame`.
5.  **OllamaLLMProcessor**: Receives text, sends it to a local LLM (Ollama), and handles tool execution (e.g., opening apps). Emits `TextFrame` with the response.
6.  **MimicTTSProcessor**: Converts the response text to audio using `mimic3-tts`. Emits `OutputAudioRawFrame`.
7.  **AudioOutputNode**: Plays the synthesized audio. Upon completion, it signals the `WakeWordNode` to reset (start listening for the wake word again).

## Data Flow
`Mic -> [Audio Frames] -> WakeWord (Gate) -> VAD -> ASR -> [Text] -> LLM -> [Text] -> TTS -> [Audio] -> Speaker`

## Key Components

### Wake Word
- **Model**: OpenWakeWord
- **Default**: "Hey Jarvis" / "Alexa" (included models)
- **Custom**: "Hola Lucy" (if trained model is present)
- **Behavior**: Blocks downstream audio until triggered. Resets after the assistant finishes speaking.

### Tool Calling
The LLM can invoke tools by generating a JSON object in its response.
- **Format**: `{"tool": "tool_name", "args": ["arg1"]}`
- **Execution**: The `OllamaLLMProcessor` intercepts this, executes the tool via `ToolManager`, and feeds the result back to the LLM for a final spoken response.

### Half-Duplex
The system currently operates in a half-duplex manner where the Wake Word detection is paused (or rather, the node is in "Pass Through" mode) during the conversation turn, and reset only after the assistant finishes speaking. This prevents Lucy from listening to herself.
