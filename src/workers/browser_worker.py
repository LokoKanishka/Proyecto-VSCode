import asyncio
import logging
from typing import Any, Dict, List, Optional

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    HAS_PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    HAS_PLAYWRIGHT = False

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class BrowserWorker(BaseWorker):
    """Worker encargado de navegar siguiendo pasos y acciones."""

    def __init__(self, worker_id: str, bus):
        super().__init__(worker_id, bus)

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        if message.content == "search_youtube":
            await self._search_youtube(message)
            return

        if message.content == "run_actions":
            await self._run_actions(message)
            return

        if message.content == "open_url":
            await self._open_url(message)
            return

        await self.send_error(message, f"Comando desconocido: {message.content}")

    async def _run_actions(
        self,
        message: LucyMessage,
        extra_log: Optional[Dict[str, Any]] = None,
        forced_steps: Optional[List[Dict[str, Any]]] = None,
    ):
        if not HAS_PLAYWRIGHT:
            await self.send_error(message, "Instalá playwright para ejecutar acciones.")
            return

        steps = forced_steps if forced_steps is not None else message.data.get("steps")
        if not isinstance(steps, list) or not steps:
            await self.send_error(message, "Necesito una lista de pasos para ejecutar.")
            return

        logger.info("🌐 BrowserWorker ejecutando %d pasos", len(steps))
        actions_log = []
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page = await browser.new_page()
                for step in steps:
                    action = (step.get("action") or "").lower()
                    selector = step.get("selector")
                    timeout = int(step.get("timeout", 12000))
                    if action == "goto":
                        await page.goto(step.get("url"), wait_until="domcontentloaded", timeout=timeout)
                        actions_log.append(f"goto {step.get('url')}")
                        await asyncio.sleep(step.get("post_wait", 0.0))
                    elif action == "fill" and selector:
                        await page.fill(selector, step.get("text", ""), timeout=timeout)
                        actions_log.append(f"fill {selector}")
                    elif action == "click" and selector:
                        await page.click(selector, timeout=timeout)
                        actions_log.append(f"click {selector}")
                    elif action == "wait" and selector:
                        await page.wait_for_selector(selector, timeout=timeout)
                        actions_log.append(f"wait {selector}")
                    elif action == "press":
                        await page.press(selector or "body", step.get("key", "Enter"), timeout=timeout)
                        actions_log.append(f"press {step.get('key', 'Enter')}")
                    elif action == "evaluate":
                        result = await page.evaluate(step.get("script", "''"))
                        actions_log.append(f"eval({result})")
                    else:
                        actions_log.append(f"skip({action})")
                await browser.close()
        except PlaywrightTimeoutError as exc:
            logger.exception("Timeout en pasos del navegador")
            await self.send_error(message, f"Timeout: {exc}")
            return
        except Exception as exc:
            logger.exception("Error ejecutando pasos del navegador")
            await self.send_error(message, f"Error: {exc}")
            return

        payload = {"log": actions_log}
        if extra_log:
            payload.update(extra_log)
        await self.send_response(
            message,
            "Acciones ejecutadas correctamente.",
            payload
        )

    async def _open_url(self, message: LucyMessage):
        url = message.data.get("url")
        if not url:
            await self.send_error(message, "Necesito una URL para abrir.")
            return
        await self.send_response(message, f"URL lista para abrir: {url}", {"url": url})

    async def _search_youtube(self, message: LucyMessage):
        if not HAS_PLAYWRIGHT:
            await self.send_error(message, "Instalá playwright para que pueda navegar.")
            return

        query = message.data.get("query", "").strip()
        if not query:
            await self.send_error(message, "Necesito un término de búsqueda.")
            return

        steps = [
            {"action": "goto", "url": "https://www.youtube.com", "post_wait": 0.5},
            {"action": "fill", "selector": "input#search", "text": query},
            {"action": "press", "selector": "input#search", "key": "Enter"},
            {"action": "wait", "selector": "ytd-video-renderer", "timeout": 12000},
            {"action": "click", "selector": "ytd-video-renderer a#thumbnail", "timeout": 0},
        ]
        await self._run_actions(
            message,
            extra_log={
                "query": query,
                "grid_hint": "E5",
                "purpose": "youtube_search",
            },
            forced_steps=steps
        )
