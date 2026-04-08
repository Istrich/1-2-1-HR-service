"""
Desktop launcher for HR 1-2-1 Web (Windows-ready).

Keeps the existing web mode intact:
- `python app.py` still works as before
- this file only adds an optional desktop wrapper
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview


HOST = "127.0.0.1"
PORT = int(os.getenv("HR121_DESKTOP_PORT", "8080"))
TITLE = "HR 1-2-1 Web"


def _resource_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    return Path(__file__).resolve().parent


def _wait_for_port(host: str, port: int, timeout_sec: float = 20.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.4)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.2)
    raise TimeoutError(f"Server did not start on {host}:{port} in {timeout_sec:.1f}s")


def _run_server() -> None:
    # app.py uses relative paths for static/outputs, so we point cwd to bundled resources.
    os.chdir(_resource_base_dir())
    from app import app  # pylint: disable=import-outside-toplevel

    config = uvicorn.Config(
        app=app,
        host=HOST,
        port=PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


def main() -> None:
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    _wait_for_port(HOST, PORT)
    webview.create_window(TITLE, f"http://{HOST}:{PORT}")
    webview.start()


if __name__ == "__main__":
    main()
