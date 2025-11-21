import unittest
from unittest.mock import patch, MagicMock
from lucy_voice.tools.lucy_tools import ToolManager

class TestToolManager(unittest.TestCase):
    def setUp(self):
        self.manager = ToolManager()

    @patch("lucy_voice.core.tools.webbrowser.open")
    def test_abrir_url(self, mock_open):
        res = self.manager.execute("abrir_url", ["google.com"])
        self.assertIn("Abrí la página", res)
        mock_open.assert_called_with("https://google.com")

    def test_unknown_tool(self):
        res = self.manager.execute("fake_tool", [])
        self.assertIn("No conozco la herramienta", res)

    @patch("lucy_voice.core.tools.subprocess.Popen")
    @patch("lucy_voice.core.tools.platform.system", return_value="Linux")
    def test_abrir_aplicacion_linux(self, mock_system, mock_popen):
        res = self.manager.execute("abrir_aplicacion", ["firefox"])
        self.assertIn("Abrí la aplicación firefox", res)
        mock_popen.assert_called()
