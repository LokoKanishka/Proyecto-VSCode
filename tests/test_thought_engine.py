import unittest

from src.engine.thought_engine import Planner, ThoughtEngine


class ThoughtEngineStaticTests(unittest.TestCase):
    def test_sanitize_steps_filters_ctrl_l_and_urls(self):
        steps = [
            {
                "tool": "perform_action",
                "args": {"action": "hotkey", "keys": ["ctrl", "l"]},
            },
            {
                "tool": "perform_action",
                "args": {"action": "type", "text": "https://example.com"},
            },
            {"tool": "launch_app", "args": {"app_name": "firefox", "url": "https://skyscanner.com"}},
        ]
        sanitized = Planner._sanitize_steps(steps)
        self.assertEqual(len(sanitized), 1)
        self.assertEqual(sanitized[0]["tool"], "launch_app")
        self.assertEqual(sanitized[0]["args"]["app_name"], "firefox")

    def test_validate_candidate_rejects_bad_grids_and_requires_focus(self):
        bad_grid = {"tool": "perform_action", "args": {"action": "click_grid", "grid": "Z9"}}
        self.assertFalse(ThoughtEngine._validate_candidate(bad_grid, state_snapshot=""))

        valid_grid = {"tool": "perform_action", "args": {"action": "click_grid", "grid": "A1"}}
        self.assertTrue(ThoughtEngine._validate_candidate(valid_grid, state_snapshot=""))

        typing_no_focus = {"tool": "perform_action", "args": {"action": "type", "text": "hola"}}
        self.assertFalse(ThoughtEngine._validate_candidate(typing_no_focus, state_snapshot=""))

        typing_with_focus = {"tool": "perform_action", "args": {"action": "type", "text": "hola"}}
        snapshot = "[focus ok]"
        self.assertTrue(ThoughtEngine._validate_candidate(typing_with_focus, state_snapshot=snapshot))


if __name__ == "__main__":
    unittest.main()
