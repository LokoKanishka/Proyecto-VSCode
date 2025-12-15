import unittest

from lucy_agents.web_agent.web_search import build_queries

class TestBuildQueries(unittest.TestCase):
    def test_definitional_numero_aureo_disambiguation(self):
        qs = build_queries("qué es el número áureo")
        self.assertGreaterEqual(len(qs), 2)
        self.assertEqual(qs[0].lower(), "qué es el número áureo")
        self.assertIn("proporcion aurea", [x.lower() for x in qs])

    def test_definitional_does_not_add_argentina(self):
        qs = build_queries("qué es la fotosíntesis")
        lowered = [x.lower() for x in qs]
        self.assertFalse(any(" argentina" in x for x in lowered))

    def test_non_definitional_adds_argentina(self):
        qs = build_queries("precio del asado")
        lowered = [x.lower() for x in qs]
        self.assertTrue(any(x.endswith(" argentina") for x in lowered))

    def test_max_three_variants(self):
        qs = build_queries("cómo se calcula el número áureo en una recta con dos segmentos")
        self.assertLessEqual(len(qs), 3)

if __name__ == "__main__":
    unittest.main()
