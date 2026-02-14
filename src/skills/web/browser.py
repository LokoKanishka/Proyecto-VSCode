"""
src/skills/web/browser.py
Skill de Navegación Web (Headless y GUI).
"""
import asyncio
from typing import Optional, List, Dict, Any
from loguru import logger
from playwright.async_api import async_playwright, Browser, Page

class BrowserSkill:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def start(self):
        logger.info("🌐 Iniciando Navegador Neural...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        self.page = await self.browser.new_page()
        
    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Navegador detenido.")

    async def navigate(self, url: str) -> str:
        if not self.page:
            await self.start()
        logger.info(f"Navegando a: {url}")
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await self.page.title()
            return f"Navegación exitosa. Título: {title}"
        except Exception as e:
            logger.error(f"Error de navegación: {e}")
            return f"Error: {str(e)}"

    async def extract_text(self) -> str:
        if not self.page: return ""
        return await self.page.inner_text("body")

    async def screenshot(self, path: str = "screenshot.png"):
        if self.page:
            await self.page.screenshot(path=path)
            logger.info(f"Captura guardada en {path}")

# Singleton para uso compartido
_browser_instance = None

async def get_browser() -> BrowserSkill:
    global _browser_instance
    if not _browser_instance:
        _browser_instance = BrowserSkill(headless=True)
        await _browser_instance.start()
    return _browser_instance
