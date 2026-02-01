from src.engine.lora_manager import LoraManager


def test_lora_manager_activate():
    lm = LoraManager()
    lm.register("test", "/tmp/test.safetensors")
    assert lm.activate("test") is True
    assert lm.active() == "test"
    lm.deactivate()
    assert lm.active() is None
