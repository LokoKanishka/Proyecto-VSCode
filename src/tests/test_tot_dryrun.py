import logging
import os
import sys
from typing import Optional

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.engine.thought_engine import ThoughtEngine, ThoughtNode


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ToT_Tester")


class DummySwarm:
    def __init__(self, host: str):
        self.host = host

    def set_profile(self, profile_name: str) -> None:
        return


def print_tree(node: ThoughtNode, indent: int = 0) -> None:
    prefix = "  " * indent
    symbol = "TREE" if indent == 0 else "-"
    if node.score >= 0.7:
        status_icon = "OK"
    elif node.score >= 0.4:
        status_icon = "WARN"
    else:
        status_icon = "BAD"

    plan_str = "ROOT" if not node.plan_step else str(node.plan_step)[:50] + "..."
    print(f"{prefix}{symbol} {status_icon} [{node.score:.2f}] {plan_str} ({node.status})")

    for child in node.children:
        print_tree(child, indent + 1)


def main() -> int:
    print("Starting Tree of Thoughts dry run...")

    host = os.getenv("LUCY_OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("LUCY_MAIN_MODEL", "qwen2.5:14b")
    swarm = DummySwarm(host)

    brain = ThoughtEngine(swarm=swarm, model=model, host=host)

    goal = "Averiguar el clima actual en Tokio y guardarlo en un archivo."
    print(f"Goal: {goal}")

    root = ThoughtNode(
        id="root",
        parent=None,
        plan_step={},
        state_snapshot=f"Goal: {goal}. History: None.",
        score=1.0,
        depth=0,
    )

    print("Running search_dfs()...")
    best_node: Optional[ThoughtNode] = brain.search_dfs(root)

    print("\nThought tree:")
    print_tree(root)

    if best_node:
        print(f"\nBest node: {best_node.plan_step}")
        print(f"Score: {best_node.score}")
        return 0

    print("No viable solution found.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
