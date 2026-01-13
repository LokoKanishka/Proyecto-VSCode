#!/usr/bin/env bash
# Fast repository verification script for Lucy voice assistant
# Strict version: Fails on any error or missing dependency

set -e  # Exit on first error

# Define environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv-lucy-voz"
PYTHON_CMD="python3"

echo "🔍 Lucy Repository Verification (STRICT MODE)"
echo "==========================================="

# Check virtual environment
if [ -f "$VENV_DIR/bin/python" ]; then
    PYTHON_CMD="$VENV_DIR/bin/python"
    echo "✅ Using venv: $VENV_DIR"
else
    echo "❌ Virtual environment not found at $VENV_DIR"
    echo "   Run: python3 -m venv .venv-lucy-voz && source .venv-lucy-voz/bin/activate && pip install -r requirements.txt"
    exit 1
fi

cd "$PROJECT_ROOT"

# Track failure state
FAILURES=0

# 1. Python compilation check
echo ""
echo "📝 Step 1: Checking Python syntax..."
if $PYTHON_CMD -m compileall -q lucy_agents/ lucy_tools/ lucy_web_agent/ tests/ > /dev/null; then
    echo "✅ Python syntax OK"
else
    echo "❌ Python syntax errors found"
    FAILURES=$((FAILURES + 1))
fi

# 2. Run unit tests
echo ""
echo "🧪 Step 2: Running unit tests..."
if [ -d "tests/" ]; then
    # Capture output but respect exit code
    if $PYTHON_CMD -m unittest discover -s tests/ -p "test_*.py" -v; then
        echo "✅ Unit tests passed"
    else
        echo "❌ Unit tests FAILED"
        FAILURES=$((FAILURES + 1))
    fi
else
    echo "⚠️  No tests directory found"
fi

# 3. Black formatting check
echo ""
echo "🎨 Step 3: Checking code formatting (Black)..."
if $PYTHON_CMD -m black --version > /dev/null 2>&1; then
    if $PYTHON_CMD -m black --check --line-length 100 lucy_agents/ lucy_tools/ lucy_web_agent/ > /dev/null 2>&1; then
        echo "✅ Code formatting verified"
    else
        echo "❌ Code formatting issues found. Run: python -m black lucy_agents/ lucy_tools/ lucy_web_agent/"
        FAILURES=$((FAILURES + 1))
    fi
else
    echo "❌ Black not installed. Run: pip install -r requirements-dev.txt"
    FAILURES=$((FAILURES + 1))
fi

# 4. Config & Wake Word Validation
echo ""
echo "⚙️  Step 4: Validating usage & dependencies..."

# Check config validity
if $PYTHON_CMD -c "import yaml; yaml.safe_load(open('config.yaml'))" 2>/dev/null; then
    echo "✅ config.yaml is valid YAML"
    
    # Check strict wake word requirement
    WAKE_ENABLED=$($PYTHON_CMD -c "import yaml; print(str(yaml.safe_load(open('config.yaml')).get('wake_word', {}).get('enabled', True)).lower())")
    
    if [ "$WAKE_ENABLED" == "true" ]; then
        if $PYTHON_CMD -c "import openwakeword; import onnxruntime" 2>/dev/null; then
            echo "✅ Wake word enabled and dependencies found"
        else
            echo "❌ Wake word enabled in config but dependencies MISSING."
            echo "   Run: ./scripts/install_wakeword_deps.sh"
            FAILURES=$((FAILURES + 1))
        fi
    else
        echo "ℹ️  Wake word disabled in config (skipping dependency check)"
    fi
else
    echo "❌ config.yaml has errors"
    FAILURES=$((FAILURES + 1))
fi

# 5. Import test
echo ""
echo "📦 Step 5: Testing module imports..."
IMPORT_FAIL=0

for module in "lucy_agents.searxng_client" "lucy_agents.desktop_bridge" "lucy_web_agent.youtube_agent" "httpx"; do
    if $PYTHON_CMD -c "import $module" 2>/dev/null; then
        echo "✅ Import OK: $module"
    else
        echo "❌ Import FAILED: $module"
        IMPORT_FAIL=1
    fi
done

if [ $IMPORT_FAIL -eq 1 ]; then
    FAILURES=$((FAILURES + 1))
fi

# Summary
echo ""
echo "==========================================="
if [ $FAILURES -eq 0 ]; then
    echo "✅✅ VERIFICATION SUCCESSFUL"
    exit 0
else
    echo "❌❌ VERIFICATION FAILED ($FAILURES errors)"
    exit 1
fi
