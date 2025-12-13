#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[SmokeAll] Proyecto: $PROJECT_DIR"

echo
echo "[SmokeAll] 1) Smoke SearXNG (curl + web_answer)"
timeout 120s "$PROJECT_DIR/scripts/lucy_web_search_smoke_test.sh"
echo "[SmokeAll] OK: smoke search"

echo
echo "[SmokeAll] 2) Smoke Web Agent (NO_LLM=1, sin Ollama)"
export LUCY_WEB_NO_LLM=1
timeout 120s "$PROJECT_DIR/scripts/lucy_web_research_smoke_no_llm.sh"
echo "[SmokeAll] OK: smoke NO_LLM"

echo
echo "[SmokeAll] TODO OK"
