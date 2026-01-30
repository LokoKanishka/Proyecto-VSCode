import unittest

from src.engine.thought_engine import Planner, ThoughtEngine, ThoughtNode


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

    def test_remember_skyscanner_fields_limits_memory(self):
        engine = ThoughtEngine.__new__(ThoughtEngine)
        engine.skyscanner_memory = []
        engine.remember_skyscanner_fields({"origen": "A1", "destino": "B2"})
        engine.remember_skyscanner_fields({"origen": "C3"})
        self.assertEqual(len(engine.skyscanner_memory), 2)
        for entry in engine.skyscanner_memory:
            self.assertIn("origen", entry)
        for idx in range(12):
            engine.remember_skyscanner_fields({"buscar": f"field{idx}"})
        self.assertEqual(len(engine.skyscanner_memory), 10)

    def test_prioritize_skyscanner_children(self):
        engine = ThoughtEngine.__new__(ThoughtEngine)
        children = []
        def make(tool, args):
            node = ThoughtNode(id="x", parent=None, plan_step={"tool": tool, "args": args}, state_snapshot="", score=0.0, depth=0)
            node.children = []
            return node
        children.append(make("perform_action", {"action": "hotkey", "keys": ["ctrl", "l"]}))
        children.append(make("capture_screen", {"grid": True}))
        children.append(make("launch_app", {"app_name": "firefox", "url": "https://www.skyscanner.com"}))
        priority = engine._prioritize_skyscanner_children(children, "el navegador skyscanner está abierto")
        self.assertEqual(priority[0].plan_step["tool"], "launch_app")
        self.assertEqual(priority[1].plan_step["tool"], "capture_screen")


if __name__ == "__main__":
    unittest.main()
