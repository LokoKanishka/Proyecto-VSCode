import asyncio
from playwright.async_api import async_playwright
import os
import time

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Navigate to local server
        print("Navigating to http://localhost:5000...")
        try:
            await page.goto("http://localhost:5000", timeout=10000)
        except Exception as e:
            print(f"Error connecting to server: {e}")
            await browser.close()
            return

        # Wait for potential rendering
        time.sleep(2)

        # Desktop Screenshot
        print("Taking desktop screenshot...")
        await page.set_viewport_size({"width": 1920, "height": 1080})
        os.makedirs("artifacts", exist_ok=True)
        await page.screenshot(path="artifacts/lucy_studio_ui_real.png", full_page=True)
        
        # Mobile Screenshot
        print("Taking mobile screenshot...")
        await page.set_viewport_size({"width": 375, "height": 812})
        await page.screenshot(path="artifacts/lucy_studio_ui_mobile.png", full_page=True)

        await browser.close()
        print("Screenshots captured in artifacts/")

if __name__ == "__main__":
    asyncio.run(run())
