from playwright.sync_api import sync_playwright

def run_cuj(page):
    page.goto("file:///app/static/index.html")
    page.evaluate("""
        localStorage.setItem('hr121_token', 'mock_token');
        localStorage.setItem('hr_u', 'mock_user');
        localStorage.setItem('USERS', 'admin:changeme');
    """)
    page.reload()
    page.wait_for_timeout(1000)

    # Click on Api Settings "ИИ и API"
    page.get_by_role("button", name="ИИ и API").click()
    page.wait_for_timeout(1000)

    # Check if the close button in modal has correct aria-label
    page.get_by_label("Закрыть").click()
    page.wait_for_timeout(1000)

    # Check Settings Modal
    page.get_by_role("button", name="Промты").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Закрыть").click()
    page.wait_for_timeout(1000)

    # Hover the logout button
    page.get_by_label("Выйти").hover()
    page.wait_for_timeout(1000)

    # Take screenshot
    page.screenshot(path="/home/jules/verification/screenshots/verification.png")
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(record_video_dir="/home/jules/verification/videos")
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
