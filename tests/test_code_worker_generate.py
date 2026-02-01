from src.workers.code_worker import CodeWorker
from src.core.bus import EventBus


def test_code_worker_generate_code_prompt():
    worker = CodeWorker("code_worker", EventBus())
    # No llama al modelo; valida que no rompe al invocar el método interno con error controlado.
    reply, data = worker._generate_code_with_llm("print('hola')")
    assert "model" in data
