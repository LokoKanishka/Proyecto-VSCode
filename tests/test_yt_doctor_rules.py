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
        reason = _run_rule("https://peg%C3%A1_ac%C3%A1_la_url/", "")
        self.assertTrue(reason)

    def test_allowed_url(self) -> None:
        reason = _run_rule("https://www.youtube.com/", "")
        self.assertEqual(reason, "")

    def test_allowed_google_accounts(self) -> None:
        reason = _run_rule("https://accounts.google.com/signin", "")
        self.assertEqual(reason, "")

    def test_allowed_google_search(self) -> None:
        reason = _run_rule("https://www.google.com/search?q=youtube", "")
        self.assertEqual(reason, "")

    def test_allowed_consent(self) -> None:
        reason = _run_rule("https://consent.youtube.com/m?continue=1", "")
        self.assertEqual(reason, "")

    def test_dns_title(self) -> None:
        reason = _run_rule("https://www.youtube.com/", "DNS_PROBE_FINISHED_NXDOMAIN")
        self.assertTrue(reason)


if __name__ == "__main__":
    unittest.main()
