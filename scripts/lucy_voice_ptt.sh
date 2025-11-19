#!/usr/bin/env bash
# Lanzar Lucy voz en modo push-to-talk

cd ~/Lucy_Workspace/Proyecto-VSCode || exit 1
source .venv-lucy-voz/bin/activate
python -m lucy_voice.voice_chat_loop
