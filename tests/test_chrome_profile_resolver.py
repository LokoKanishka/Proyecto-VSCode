import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = "scripts/chrome_profile_dir_by_name.sh"


class TestChromeProfileResolver(unittest.TestCase):
    def _run(self, name: str, local_state: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["CHROME_LOCAL_STATE"] = str(local_state)
        return subprocess.run(
            ["bash", SCRIPT, name], capture_output=True, text=True, env=env, check=False
        )

    def test_resolve_profile_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            local_state = base / "Local State"
            payload = {
                "profile": {
                    "info_cache": {
                        "Default": {"name": "Chat"},
                        "Profile 1": {"name": "diego"},
                    }
                }
            }
            local_state.write_text(json.dumps(payload), encoding="utf-8")
            proc = self._run("diego", local_state)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("PROFILE_DIR=Profile 1", proc.stdout)
            self.assertIn(f"BASE={base}", proc.stdout)

    def test_missing_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            local_state = base / "Local State"
            payload = {"profile": {"info_cache": {"Default": {"name": "Chat"}}}}
            local_state.write_text(json.dumps(payload), encoding="utf-8")
            proc = self._run("nope", local_state)
            self.assertEqual(proc.returncode, 3)


if __name__ == "__main__":
    unittest.main()
