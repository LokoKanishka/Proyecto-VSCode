from src.planners.tree_of_thought_llm import _extract_json


def test_extract_json_from_text():
    text = "respuesta: {\"score\":0.7,\"rationale\":\"ok\"} fin"
    payload = _extract_json(text)
    assert payload == "{\"score\":0.7,\"rationale\":\"ok\"}"
