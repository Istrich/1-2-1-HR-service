import re
import uuid
import aiohttp
from pathlib import Path

def normalize_url(url: str) -> str:
    m = re.search(r"drive\.google\.com/file/d/([^/]+)/", url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r"drive\.google\.com/.*?[?&]id=([^&]+)", url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    if "dropbox.com" in url:
        if "dl=" in url:
            url = re.sub(r"dl=\d", "dl=1", url)
        else:
            url = f"{url}{'&' if '?' in url else '?'}dl=1"
        m = re.search(r"www\.dropbox.com/s/([^/]+)/([^?]+)", url)
        if m:
            return f"https://dl.dropboxusercontent.com/s/{m.group(1)}/{m.group(2)}"
    return url

async def download_url_to_temp(url: str, tmpdir: Path) -> Path:
    normalized = normalize_url(url)
    dest_path = tmpdir / uuid.uuid4().hex
    async with aiohttp.ClientSession() as session:
        async with session.get(normalized) as resp:
            if resp.status != 200:
                raise ValueError(f"Не удалось скачать (HTTP {resp.status}).")
            ct = resp.headers.get("Content-Type", "").lower()
            if "text/html" in ct:
                raise ValueError("По ссылке — веб-страница, а не файл.")
            first = await resp.content.read(4096)
            s = first.lstrip().lower()
            if s.startswith(b"<!doctype html") or s.startswith(b"<html"):
                raise ValueError("По ссылке загружается HTML.")
            with open(dest_path, "wb") as f:
                f.write(first)
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    f.write(chunk)
    return dest_path
