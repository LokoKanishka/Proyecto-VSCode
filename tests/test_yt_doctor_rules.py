import subprocess
import unittest


def _run_rule(url: str, title: str) -> str:
    cmd = (
        "source scripts/yt_doctor_rules.sh; "
        f"r=$(_yt_bad_url_reason '{url}' '{title}'); "
        "printf '%s' \"$r\""
    )
    proc = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
    return (proc.stdout or "").strip()


class TestYouTubeDoctorRules(unittest.TestCase):
    def test_chrome_error(self) -> None:
        reason = _run_rule("chrome-error://foo", "")
        self.assertTrue(reason)

    def test_placeholder_pattern(self) -> None:
        reason = _run_rule("https://pega_aca_la_url/", "")
        self.assertTrue(reason)

    def test_allowed_url(self) -> None:
        reason = _run_rule("https://www.youtube.com/", "")
        self.assertEqual(reason, "")


if __name__ == "__main__":
    unittest.main()
