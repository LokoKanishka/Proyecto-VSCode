import unittest

from lucy_voice.tools.lucy_tools import ToolManager


class ToolManagerTests(unittest.TestCase):
    def test_execute_returns_placeholder(self):
        manager = ToolManager()
        result = manager.execute("open_url", {"url": "https://example.com"})
        self.assertIn("Herramienta 'open_url' no está disponible", result)

    def test_execute_accepts_args(self):
        manager = ToolManager()
        result = manager.execute("fake_tool", ["arg"])
        self.assertTrue("fake_tool" in result)


if __name__ == "__main__":
    unittest.main()
