import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('file:///app/static/index.html')

        # We need to test the logout button as it's on the main screen (after login)
        # In memory, we bypass login by setting localStorage:
        await page.evaluate("""() => {
            localStorage.setItem('hr121_token', 'test_token');
            localStorage.setItem('hr121_user', 'admin');
            localStorage.setItem('hr_u', 'admin');
        }""")
        await page.reload()

        # Check if logout button has proper aria-label
        logout_btn = page.locator('button[aria-label="Выйти"]')
        count = await logout_btn.count()
        print(f"Logout button count: {count}")
        if count > 0:
            print(f"Logout button title: {await logout_btn.get_attribute('title')}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
