from playwright.sync_api import sync_playwright
import os

def test_frontend_renders_without_errors():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # We set localStorage to bypass login as mentioned in context memory
        page.goto(f"file://{os.path.abspath('static/index.html')}")

        # Run a script to set localStorage and reload
        page.evaluate("localStorage.setItem('hr121_token', 'fake-token'); localStorage.setItem('hr121_user', 'admin');")
        page.reload()

        # Check if basic elements are present to ensure the page parsed successfully
        assert page.locator("div.shell").is_visible(), "Shell should be visible"

        # Test specific aria-labels we added
        page.click("button:has-text('ИИ и API')")

        # Verify close button in ApiSettingsModal has aria-label="Закрыть"
        close_btn = page.locator("button[aria-label='Закрыть']")
        assert close_btn.count() > 0, "Close button with aria-label='Закрыть' should be present"

        browser.close()
        print("Frontend tests passed successfully.")

if __name__ == "__main__":
    test_frontend_renders_without_errors()
