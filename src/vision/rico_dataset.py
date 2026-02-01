from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_rico_annotations(root: str, limit: int = 500) -> List[Dict[str, Any]]:
    """
    Carga anotaciones RICO (si existen) desde un root dado.
    No asume estructura estricta; extrae bounds/text recursivamente.
    """
    base = Path(root)
    if not base.exists():
        return []
    json_files = list(base.rglob("*.json"))
    items: List[Dict[str, Any]] = []
    for path in json_files[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        elements: List[Dict[str, Any]] = []
        _collect_elements(data, elements)
        items.append(
            {
                "path": str(path),
                "elements": elements,
                "count": len(elements),
            }
        )
    return items


def _collect_elements(node: Any, out: List[Dict[str, Any]]) -> None:
    if isinstance(node, dict):
        bounds = node.get("bounds") or node.get("bounding_box") or node.get("bbox")
        text = node.get("text") or node.get("label")
        if bounds or text:
            out.append(
                {
                    "bounds": bounds,
                    "text": text,
                    "type": node.get("type") or node.get("class"),
                }
            )
        for child in node.get("children", []) or []:
            _collect_elements(child, out)
        for key in ("nodes", "elements"):
            for child in node.get(key, []) or []:
                _collect_elements(child, out)
    elif isinstance(node, list):
        for child in node:
            _collect_elements(child, out)
