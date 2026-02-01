from src.workers.browser_worker import BrowserWorker
from src.core.bus import EventBus


def test_dom_summary_tables():
    html = """
    <html><body>
    <table>
      <tr><th>Col1</th><th>Col2</th></tr>
      <tr><td>A</td><td>B</td></tr>
    </table>
    </body></html>
    """
    worker = BrowserWorker("browser_worker", EventBus())
    summary = worker._distill_dom(html)
    assert summary["counts"]["tables"] == 1
    assert summary["tables"][0]["headers"] == ["Col1", "Col2"]
