import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('file:///app/static/index.html')

        # We inject mock values into localStorage to bypass the login screen
        await page.evaluate("""() => {
            localStorage.setItem('hr121_token', 'mock_token');
            localStorage.setItem('hr_u', 'mock_user');
            localStorage.setItem('USERS', 'mock_user:mock_password');
        }""")
        await page.reload()

        # Check for our aria-labels
        # Audio play button might only exist in a specific state, so we won't strictly wait for it
        # Topbar logout button should exist
        try:
            await page.wait_for_selector('button[aria-label="Выйти"]', timeout=5000)
            print("Successfully found 'Выйти' aria-label on logout button.")
        except Exception as e:
            print("Failed to find 'Выйти' aria-label:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())