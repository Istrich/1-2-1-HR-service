import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Page Error: {err}"))
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_timeout(2000)
        content = await page.content()
        # print(content[:500])
        await browser.close()

asyncio.run(main())
