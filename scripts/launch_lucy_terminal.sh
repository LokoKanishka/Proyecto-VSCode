#!/bin/bash

# Script to launch Lucy Voice in a terminal window
# This ensures the user can see logs and the window stays open

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_SCRIPT="$DIR/lucy_voice_wakeword.sh"

# Function to launch in terminal
launch_in_terminal() {
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "$TARGET_SCRIPT; echo 'Press Enter to close...'; read"
    elif command -v x-terminal-emulator &> /dev/null; then
        x-terminal-emulator -e bash -c "$TARGET_SCRIPT; echo 'Press Enter to close...'; read"
    elif command -v konsole &> /dev/null; then
        konsole -e bash -c "$TARGET_SCRIPT; echo 'Press Enter to close...'; read"
    elif command -v xterm &> /dev/null; then
        xterm -e bash -c "$TARGET_SCRIPT; echo 'Press Enter to close...'; read"
    else
        echo "No suitable terminal emulator found."
        # Fallback: just run it, hoping the desktop environment handles Terminal=true correctly
        bash -c "$TARGET_SCRIPT; echo 'Press Enter to close...'; read"
    fi
}

launch_in_terminal
