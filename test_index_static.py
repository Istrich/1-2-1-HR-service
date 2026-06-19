from bs4 import BeautifulSoup

def main():
    with open("static/index.html", "r") as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    scripts = soup.find_all("script", {"type": "text/babel"})
    if not scripts:
        print("Babel script not found")
        return

    script_content = scripts[0].string

    # Check for inputs with search/text type and their aria labels
    if 'aria-label={placeholder}' in script_content and 'title={placeholder}' in script_content:
        print("PanelSearchToolbar aria-label found")
    else:
        print("PanelSearchToolbar aria-label missing")

    if 'aria-label="Поиск по названию"' in script_content and 'title="Поиск по названию"' in script_content:
        print("HistoryPage aria-label found")
    else:
        print("HistoryPage aria-label missing")

    if 'aria-label="Ссылка на запись"' in script_content and 'title="Ссылка на запись"' in script_content:
        print("UploadPage aria-label found")
    else:
        print("UploadPage aria-label missing")

    if 'aria-label="Предыдущее вхождение"' in script_content and 'aria-label="Следующее вхождение"' in script_content:
        print("PanelSearchToolbar prev/next buttons aria-label found")
    else:
        print("PanelSearchToolbar prev/next buttons aria-label missing")

    if 'aria-valuemin="0" aria-valuemax="100"' in script_content or 'aria-valuemin={0} aria-valuemax={100}' in script_content:
        print("AudioPlayer aria-valuemin/max found")
    else:
        print("AudioPlayer aria-valuemin/max missing")

    if 'const{useState' in script_content:
        print("React hooks found")

main()
