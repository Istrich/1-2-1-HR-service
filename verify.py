import sys
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('file:///app/static/index.html')

    # Wait for the login screen to render
    page.wait_for_selector('.login-wrap')

    html = page.content()

    # Just inspect the DOM elements or React template directly
    with open('/app/static/index.html', 'r') as f:
        file_html = f.read()

    if 'aria-label="Закрыть"' in file_html:
        print("PASS: aria-label='Закрыть' found in source")
    else:
        print("FAIL: aria-label='Закрыть' not found in source")
        sys.exit(1)

    if 'aria-label={playing ? \'Пауза\' : \'Воспроизвести\'}' in file_html:
        print("PASS: aria-label for Play/Pause found in source")
    else:
        print("FAIL: aria-label for Play/Pause not found in source")
        sys.exit(1)

    browser.close()
