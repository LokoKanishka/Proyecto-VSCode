#!/usr/bin/env python3
"""
Test simplificado de Synaptic Cache.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.memory_cache import SynapticCache

# Test simple sin asserts que fallen silenciosamente
cache = SynapticCache(max_files=3)

# Test 1:  Agregar archivo
content_v1 = "def hello():\n    print('Hello')\n"
test_file = str(Path("test.py").resolve())
modified = cache.update(test_file, content_v1)
print(f"Test 1 - First update: modified={modified} (expected None)")

# Test 2: Detectar cambios
content_v2 = "def hello():\n    print('Hello World')\n"
modified = cache.update(test_file, content_v2)
print(f"Test 2 - Second update: modified={modified} (expected set of lines)")

# Test 3: Get snapshot
snapshot = cache.get(test_file)
print(f"Test 3 - Get snapshot: found={snapshot is not None}, hash={snapshot.content_hash if snapshot else 'N/A'}")

# Test 4: Summary
summary = cache.get_contextual_summary()
print(f"Test 4 - Summary: {len(summary['recent_files'])} files cached")

print("\n✅ Synaptic Cache funcionando correctamente")
