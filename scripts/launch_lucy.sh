#!/bin/bash

# Calculate script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Debug logging
LOG_FILE="/tmp/lucy_launch.log"
echo "$(date): Launching Lucy..." > "$LOG_FILE"

# Run the main script
"$SCRIPT_DIR/lucy_voice_wakeword.sh" 2>&1 | tee -a "$LOG_FILE"

# Capture exit code
EXIT_CODE=$?

# Always keep terminal open to see output/errors
echo ""
echo "=================================================="
echo "Lucy terminó (Código: $EXIT_CODE)."
echo "Presiona Enter para cerrar esta ventana..."
echo "=================================================="
read -p "Presiona Enter para continuar..."

