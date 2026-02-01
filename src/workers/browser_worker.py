import asyncio
import base64
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
        self.default_headless = True
        self.default_timeout_ms = 12000
        self.default_user_data_dir: Optional[str] = None
        self.default_storage_state: Optional[str] = None

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

        if message.content == "capture_state":
            await self._capture_state(message)
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
        headless = message.data.get("headless", self.default_headless)
        user_data_dir = message.data.get("user_data_dir", self.default_user_data_dir)
        storage_state = message.data.get("storage_state", self.default_storage_state)
        fallback_vision = bool(message.data.get("fallback_vision", False))
        try:
            async with async_playwright() as pw:
                browser, context = await self._launch_context(
                    pw,
                    headless=headless,
                    user_data_dir=user_data_dir,
                    storage_state=storage_state,
                )
                page = await context.new_page()
                for step in steps:
                    action = (step.get("action") or "").lower()
                    selector = step.get("selector")
                    timeout = int(step.get("timeout", self.default_timeout_ms))
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
                if storage_state:
                    await context.storage_state(path=storage_state)
                await context.close()
                if browser:
                    await browser.close()
        except PlaywrightTimeoutError as exc:
            logger.exception("Timeout en pasos del navegador")
            if fallback_vision:
                payload = await self._capture_state_payload(message)
                await self.send_event(
                    "broadcast",
                    "browser_action_failed",
                    {"reason": "timeout", "detail": str(exc), "steps": steps, **payload},
                )
            await self.send_error(message, f"Timeout: {exc}")
            return
        except Exception as exc:
            logger.exception("Error ejecutando pasos del navegador")
            if fallback_vision:
                payload = await self._capture_state_payload(message)
                await self.send_event(
                    "broadcast",
                    "browser_action_failed",
                    {"reason": "error", "detail": str(exc), "steps": steps, **payload},
                )
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
        if not HAS_PLAYWRIGHT:
            await self.send_response(message, f"URL lista para abrir: {url}", {"url": url})
            return

        headless = message.data.get("headless", self.default_headless)
        user_data_dir = message.data.get("user_data_dir", self.default_user_data_dir)
        storage_state = message.data.get("storage_state", self.default_storage_state)
        try:
            async with async_playwright() as pw:
                browser, context = await self._launch_context(
                    pw,
                    headless=headless,
                    user_data_dir=user_data_dir,
                    storage_state=storage_state,
                )
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=self.default_timeout_ms)
                title = await page.title()
                if storage_state:
                    await context.storage_state(path=storage_state)
                await context.close()
                if browser:
                    await browser.close()
            await self.send_response(message, f"Abrí la URL: {title}", {"url": url, "title": title})
        except Exception as exc:
            await self.send_error(message, f"No pude abrir la URL: {exc}")

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

    async def _capture_state(self, message: LucyMessage):
        if not HAS_PLAYWRIGHT:
            await self.send_error(message, "Instalá playwright para capturar el estado.")
            return
        url = message.data.get("url")
        headless = message.data.get("headless", self.default_headless)
        user_data_dir = message.data.get("user_data_dir", self.default_user_data_dir)
        storage_state = message.data.get("storage_state", self.default_storage_state)
        try:
            async with async_playwright() as pw:
                browser, context = await self._launch_context(
                    pw,
                    headless=headless,
                    user_data_dir=user_data_dir,
                    storage_state=storage_state,
                )
                page = await context.new_page()
                if url:
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.default_timeout_ms)
                screenshot = await page.screenshot(full_page=True)
                html = await page.content()
                accessibility = None
                if message.data.get("accessibility"):
                    try:
                        accessibility = await page.accessibility.snapshot()
                    except Exception:
                        accessibility = None
                if storage_state:
                    await context.storage_state(path=storage_state)
                await context.close()
                if browser:
                    await browser.close()
            payload = {
                "url": url,
                "screenshot_b64": base64.b64encode(screenshot).decode("utf-8"),
                "html": html[:20000],
                "accessibility": accessibility,
            }
            await self.send_response(message, "Estado capturado.", payload)
        except Exception as exc:
            await self.send_error(message, f"No pude capturar el estado: {exc}")

    async def _launch_context(self, pw, headless: bool, user_data_dir: Optional[str], storage_state: Optional[str]):
        if user_data_dir:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
            )
            return None, context
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(storage_state=storage_state if storage_state else None)
        return browser, context

    async def _capture_state_payload(self, message: LucyMessage) -> Dict[str, Any]:
        """Captura estado en caso de error para fallback de visión."""
        if not HAS_PLAYWRIGHT:
            return {"capture_error": "playwright_no_disponible"}
        url = message.data.get("url")
        headless = message.data.get("headless", self.default_headless)
        user_data_dir = message.data.get("user_data_dir", self.default_user_data_dir)
        storage_state = message.data.get("storage_state", self.default_storage_state)
        try:
            async with async_playwright() as pw:
                browser, context = await self._launch_context(
                    pw,
                    headless=headless,
                    user_data_dir=user_data_dir,
                    storage_state=storage_state,
                )
                page = await context.new_page()
                if url:
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.default_timeout_ms)
                screenshot = await page.screenshot(full_page=True)
                html = await page.content()
                accessibility = None
                try:
                    accessibility = await page.accessibility.snapshot()
                except Exception:
                    accessibility = None
                if storage_state:
                    await context.storage_state(path=storage_state)
                await context.close()
                if browser:
                    await browser.close()
            return {
                "url": url,
                "screenshot_b64": base64.b64encode(screenshot).decode("utf-8"),
                "html": html[:20000],
                "accessibility": accessibility,
            }
        except Exception as exc:
            return {"capture_error": str(exc)}
