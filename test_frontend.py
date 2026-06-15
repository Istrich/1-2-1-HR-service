from playwright.sync_api import sync_playwright
import os

def test_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the index.html file
        page.goto(f"file://{os.path.abspath('static/index.html')}")

        # Set local storage to bypass login
        page.evaluate('localStorage.setItem("hr121_token", "test-token"); localStorage.setItem("hr_u", "admin"); localStorage.setItem("USERS", "admin:changeme");')

        # Reload to apply local storage
        page.reload()

        # Wait for the main UI to load
        page.wait_for_selector('.topbar', timeout=5000)

        # Check that the exit button has the aria-label
        exit_btn = page.locator('button[aria-label="Выйти"]')
        assert exit_btn.count() == 1, "Exit button aria-label not found"

        print("Frontend verification passed!")
        browser.close()

if __name__ == "__main__":
    test_frontend()
