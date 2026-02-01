import pytest

from src.engine.vllm_client import VLLMClient


def test_vllm_client_url_override():
    client = VLLMClient(base_url="http://localhost:9999", model="dummy")
    assert client.base_url.endswith(":9999")
    assert client.model == "dummy"
