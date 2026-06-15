import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://127.0.0.1:8000")

        # Test 1: Global error button logic (if we can trigger an error)
        # Wait for the UI to load
        await page.wait_for_selector(".login-box")

        # Perform login to get to the main UI where SettingsModals are
        await page.fill("input[type='text']", "admin")
        await page.fill("input[type='password']", "changeme")
        await page.click("button.btn-am")

        # Wait for workspace/topbar to load
        await page.wait_for_selector(".topbar")

        # Open Settings modal
        await page.click("text=Промты")
        await page.wait_for_selector(".overlay-box")

        # Check that the close button in settings has aria-label and title
        settings_close_btn = page.locator(".overlay-head button[aria-label='Закрыть']").first
        assert await settings_close_btn.is_visible(), "Settings close button with ARIA label not found"
        title = await settings_close_btn.get_attribute("title")
        assert title == "Закрыть", f"Expected title 'Закрыть', got {title}"
        await settings_close_btn.click() # Close the modal

        # Open API Settings modal
        await page.click("text=ИИ и API")
        await page.wait_for_selector(".overlay-box")

        # Check that the close button in API settings has aria-label and title
        api_close_btn = page.locator(".overlay-head button[aria-label='Закрыть']").first
        assert await api_close_btn.is_visible(), "API settings close button with ARIA label not found"
        title = await api_close_btn.get_attribute("title")
        assert title == "Закрыть", f"Expected title 'Закрыть', got {title}"
        await api_close_btn.click() # Close the modal

        print("Tests passed successfully.")
        await browser.close()

asyncio.run(main())
