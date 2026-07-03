from __future__ import annotations

import socket
import threading
import time
import webbrowser
from pathlib import Path
from wsgiref.simple_server import make_server

from index import LIBRARY_ROOT, app


HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def open_browser_when_ready(url: str, retries: int = 40) -> None:
    for _ in range(retries):
        if port_in_use(HOST, PORT):
            webbrowser.open(url)
            return
        time.sleep(0.25)
    webbrowser.open(url)


def serve() -> None:
    LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)
    server = make_server(HOST, PORT, app)
    browser_thread = threading.Thread(
        target=open_browser_when_ready,
        args=(URL,),
        daemon=True,
    )
    browser_thread.start()
    server.serve_forever()


if __name__ == "__main__":
    if port_in_use(HOST, PORT):
        webbrowser.open(URL)
    else:
        serve()
