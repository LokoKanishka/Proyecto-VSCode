from src.core.bus import EventBus
from src.workers.browser_worker import BrowserWorker


def test_distill_html_basic():
    bus = EventBus()
    worker = BrowserWorker("browser_worker", bus)
    html = """
    <html>
      <head>
        <style>body{}</style>
        <script>console.log("x")</script>
      </head>
      <body>
        <h1>Titulo</h1>
        <p>hola mundo</p>
      </body>
    </html>
    """
    text = worker._distill_html(html)
    assert "Titulo" in text
    assert "hola mundo" in text
