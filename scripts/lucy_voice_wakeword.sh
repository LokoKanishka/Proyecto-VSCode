#!/usr/bin/env bash
# Lanzar Lucy voz en modo wake word (hey_jarvis)

cd ~/Lucy_Workspace/Proyecto-VSCode || exit 1
source .venv-lucy-voz/bin/activate
python -m lucy_voice.wakeword_iddkd
