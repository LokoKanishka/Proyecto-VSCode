import unittest
from unittest.mock import patch, MagicMock
from lucy_voice.tools.lucy_tools import ToolManager

class TestToolManager(unittest.TestCase):
    def setUp(self):
        self.manager = ToolManager()

    @patch("lucy_voice.tools.lucy_tools.webbrowser.open")
    def test_abrir_url(self, mock_open):
        manager = ToolManager()
        result = manager.execute("abrir_url", ["https://example.com"])
        mock_open.assert_called_once_with("https://example.com")
        assert "Abrí la página" in result


class TestAbrirAplicacion(unittest.TestCase): # Added unittest.TestCase for consistency
    def setUp(self): # Added setUp for self.manager
        self.manager = ToolManager()

    @patch("lucy_voice.tools.lucy_tools.subprocess.Popen")
    @patch("lucy_voice.tools.lucy_tools.platform.system", return_value="Linux")
    def test_abrir_aplicacion_linux(self, mock_system, mock_popen):
        res = self.manager.execute("abrir_aplicacion", ["firefox"])
        self.assertIn("Abrí la aplicación firefox", res)
        mock_popen.assert_called()
