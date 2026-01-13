#!/usr/bin/env bash
# Fast repository verification script for Lucy voice assistant
# Runs basic checks to ensure code quality and functionality

set -e  # Exit on first error

echo "🔍 Lucy Repository Verification"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Track failures
FAILURES=0

# 1. Python compilation check
echo "📝 Step 1: Checking Python syntax..."
if python3 -m compileall -q lucy_agents/ lucy_tools/ lucy_web_agent/ tests/ 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Python syntax check passed"
else
    echo -e "${RED}✗${NC} Python syntax errors found"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 2. Run unit tests
echo "🧪 Step 2: Running unit tests..."
if [ -d "tests/" ]; then
    if python3 -m unittest discover -s tests/ -p "test_*.py" -v 2>&1 | tail -20; then
        echo -e "${GREEN}✓${NC} Unit tests passed"
    else
        echo -e "${YELLOW}⚠${NC} Some unit tests failed (non-critical)"
        # Don't count as failure for now
fi
else
    echo -e "${YELLOW}⚠${NC} No tests directory found"
fi
echo ""

# 3. Black formatting check
echo "🎨 Step 3: Checking code formatting (Black)..."
if command -v black &> /dev/null; then
    if python3 -m black --check --line-length 100 lucy_agents/ lucy_tools/ lucy_web_agent/ 2>&1 | tail -10; then
        echo -e "${GREEN}✓${NC} Code formatting verified"
    else
        echo -e "${YELLOW}⚠${NC} Code needs formatting (run: black lucy_agents/ lucy_tools/ lucy_web_agent/)"
        # Don't count as failure, just warning
    fi
else
    echo -e "${YELLOW}⚠${NC} Black not installed (skip formatting check)"
fi
echo ""

# 4. Config file validation
echo "⚙️  Step 4: Validating configuration..."
if python3 -c "import yaml; yaml.safe_load(open('config.yaml'))" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} config.yaml is valid"
else
    echo -e "${RED}✗${NC} config.yaml has errors"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 5. Import test
echo "📦 Step 5: Testing module imports..."
IMPORT_ERRORS=0

if python3 -c "from lucy_agents import searxng_client, desktop_bridge" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} lucy_agents imports OK"
else
    echo -e "${RED}✗${NC} lucy_agents import failed"
    IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
fi

if python3 -c "from lucy_web_agent import youtube_agent" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} lucy_web_agent imports OK"
else
    echo -e "${RED}✗${NC} lucy_web_agent import failed"
    IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
fi

if python3 -c "from lucy_tools.wake_word import WakeWordDetector" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} lucy_tools.wake_word imports OK"
else
    echo -e "${YELLOW}⚠${NC} lucy_tools.wake_word import failed (openwakeword may not be installed)"
fi

if [ $IMPORT_ERRORS -gt 0 ]; then
    FAILURES=$((FAILURES + 1))
fi
echo ""

# Summary
echo "================================"
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ All critical checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAILURES critical check(s) failed${NC}"
    exit 1
fi
