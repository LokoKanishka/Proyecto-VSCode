#!/usr/bin/env python3
"""
Verifica el plan de Skyscanner usando los sanitizadores del ThoughtEngine.
"""

import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo))

from src.engine.thought_engine import Planner, ThoughtEngine


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    plan_path = repo / "docs" / "skyscanner_plan_sample.json"
    if not plan_path.exists():
        print("❌ No se encontró el plan de ejemplo.")
        return 1

    plan = json.loads(plan_path.read_text())
    sanitized = Planner._sanitize_steps(plan)
    print(f"Plan ejemplo: {len(plan)} pasos → sanitizados {len(sanitized)} pasos válidos.")

    focused_snapshot = "[focus ok] [screen update]"
    valid_steps = []
    for step in sanitized:
        if ThoughtEngine._validate_candidate(step, state_snapshot=focused_snapshot):
            valid_steps.append(step)
        else:
            print(f"⚠️ Paso rechazado: {step}")

    print(f"Valid steps tras validación adicional: {len(valid_steps)}")
    for step in valid_steps:
        print(f"  - {step['tool']} {step.get('args')}")

    return 0 if valid_steps else 2


if __name__ == "__main__":
    raise SystemExit(main())
