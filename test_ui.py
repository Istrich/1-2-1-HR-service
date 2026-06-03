import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        # Mock localStorage bypass for login
        await page.goto("file:///app/static/index.html")
        await page.evaluate("""
            localStorage.setItem('hr121_token', 'mock_token');
            localStorage.setItem('hr_u', 'mock_user');
            localStorage.setItem('USERS', 'admin:changeme');
        """)
        await page.reload()
        # Verify elements are present
        print("Page title:", await page.title())
        await browser.close()

asyncio.run(main())
