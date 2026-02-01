#!/usr/bin/env python3
import os
import tempfile
from pathlib import Path

from src.core.types import MemoryEntry
from src.memory.memory_manager import MemoryManager


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "memory.db"
        manager = MemoryManager(db_path=str(db_path))
        manager.add_message(MemoryEntry(role="user", content="hola", session_id="smoke"))
        snapshot = manager.log_file_snapshot("notes/smoke.txt", b"smoke", metadata={"source": "smoke"})
        if not snapshot:
            print("❌ No pude crear snapshot")
            return 1
        os.environ["LUCY_BACKUP_REQUIRE_ENCRYPTION"] = "1"
        os.environ.pop("LUCY_BACKUP_PASSPHRASE", None)
        backup = manager.backup_db(backup_dir=str(Path(tmpdir) / "backups"))
        if backup is not None:
            print("❌ Backup debería fallar sin passphrase")
            return 1
    print("✅ Memory snapshot smoke OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
