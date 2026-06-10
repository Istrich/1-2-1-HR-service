from playwright.sync_api import sync_playwright, expect
import os

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()

    # Bypass login
    context.add_init_script("""
        window.localStorage.setItem('hr121_token', 'test_token');
        window.localStorage.setItem('hr121_user', 'test_user');
    """)

    page = context.new_page()
    page.goto('file://' + os.path.abspath('static/index.html'))
    page.wait_for_selector('text=HR 1-2-1')

    # Take a screenshot to verify it loads main page without breaking
    page.screenshot(path="ui_screenshot_playwright.png")

    browser.close()
    print("UI load tested successfully!")
