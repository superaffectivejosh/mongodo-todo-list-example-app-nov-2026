"""Start the local app and open Chrome after the server is ready."""
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

URL = "http://127.0.0.1:8000"


def open_when_ready():
    for _ in range(100):
        try:
            with urllib.request.urlopen(f"{URL}/api/health", timeout=1):
                if sys.platform == "darwin":
                    result = subprocess.run(["open", "-a", "Google Chrome", URL], capture_output=True)
                    if result.returncode == 0:
                        return
                webbrowser.open(URL)
                return
        except (OSError, urllib.error.URLError):
            time.sleep(0.4)


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).resolve().parent)
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", 8000)) == 0:
            raise SystemExit("Port 8000 is already in use. Open http://127.0.0.1:8000 or stop the existing server.")
    threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, proxy_headers=False)
