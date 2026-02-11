import unittest
from lucy_voice.llm.ollama_wrapper import OllamaLLM
from lucy_voice.config import LucyConfig

class TestOllamaLLM(unittest.TestCase):
    def setUp(self):
        self.config = LucyConfig()
        self.llm = OllamaLLM(self.config)

    def test_extract_visible_answer(self):
        raw = "Thinking...\n...done thinking.\nHola, ¿cómo estás?"
        extracted = self.llm._extract_visible_answer(raw)
        self.assertEqual(extracted, "Hola, ¿cómo estás?")

        raw2 = "Respuesta: Bien, gracias."
        extracted2 = self.llm._extract_visible_answer(raw2)
        self.assertEqual(extracted2, "Bien, gracias.")

        raw3 = "Just raw text"
        extracted3 = self.llm._extract_visible_answer(raw3)
        self.assertEqual(extracted3, "Just raw text")

    def test_extract_tool_call(self):
        text = 'Claro, voy a abrir eso. {"tool": "abrir_aplicacion", "args": ["firefox"]}'
        tool = self.llm.extract_tool_call(text)
        self.assertIsNotNone(tool)
        self.assertEqual(tool["tool"], "abrir_aplicacion")
        self.assertEqual(tool["args"], ["firefox"])

        text_no_tool = "Solo texto normal."
        tool_none = self.llm.extract_tool_call(text_no_tool)
        self.assertIsNone(tool_none)

        text_malformed = '{"tool": "broken"'
        tool_broken = self.llm.extract_tool_call(text_malformed)
        self.assertIsNone(tool_broken)
