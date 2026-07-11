from __future__ import annotations

import ctypes
import functools
import logging
import os
import socket
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import uvicorn

APP_NAME = "Vamos Subscription Tracker"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 5174


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base.joinpath(*parts)


def data_dir() -> Path:
    candidates = [
        os.getenv("APPDATA"),
        os.getenv("LOCALAPPDATA"),
        tempfile.gettempdir(),
        str(Path.home()),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        root = Path(candidate) / "Vamos Subscription Tracker"
        try:
            root.mkdir(parents=True, exist_ok=True)
            probe = root / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return root
        except OSError:
            continue
    raise RuntimeError("Не удалось найти папку для хранения данных приложения.")


def configure_environment() -> None:
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{(data_dir() / 'app.db').as_posix()}")
    server_path = resource_path("server")
    if server_path.exists():
        sys.path.insert(0, str(server_path))


def configure_logging() -> None:
    try:
        logging.basicConfig(
            filename=data_dir() / "launcher.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    except OSError:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def message_box(text: str, title: str = APP_NAME, icon: int = 0x40) -> None:
    ctypes.windll.user32.MessageBoxW(None, text, title, icon)


class SpaHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        requested = Path(self.translate_path(self.path))
        if not requested.exists() and "." not in Path(self.path).name:
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, format: str, *args: object) -> None:
        return


def wait_for_port(host: str, port: int, timeout: float = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.25)
    return False


class VamosLauncher:
    def __init__(self) -> None:
        self.backend_server: uvicorn.Server | None = None
        self.frontend_server: ThreadingHTTPServer | None = None

    def start(self) -> None:
        try:
            configure_logging()
            configure_environment()
            logging.info("Starting Vamos launcher")
            self.start_backend()
            self.start_frontend()
            if not wait_for_port(BACKEND_HOST, BACKEND_PORT):
                raise RuntimeError(f"Backend не ответил на порт {BACKEND_PORT}.")
            if not wait_for_port(FRONTEND_HOST, FRONTEND_PORT):
                raise RuntimeError(f"Frontend не ответил на порт {FRONTEND_PORT}.")
            webbrowser.open(f"http://{FRONTEND_HOST}:{FRONTEND_PORT}")
            message_box(
                "Приложение запущено.\n\n"
                f"Frontend: http://{FRONTEND_HOST}:{FRONTEND_PORT}\n"
                f"Backend: http://{BACKEND_HOST}:{BACKEND_PORT}\n\n"
                "Нажмите OK, чтобы остановить приложение.",
            )
        except Exception as exc:
            logging.exception("Launcher failed")
            message_box(f"Не удалось запустить приложение:\n\n{exc}", icon=0x10)
        finally:
            self.stop()

    def start_backend(self) -> None:
        from app.main import app

        config = uvicorn.Config(app, host=BACKEND_HOST, port=BACKEND_PORT, log_level="warning", log_config=None)
        self.backend_server = uvicorn.Server(config)
        thread = threading.Thread(target=self._run_backend, daemon=True)
        thread.start()

    def _run_backend(self) -> None:
        try:
            assert self.backend_server is not None
            self.backend_server.run()
        except Exception:
            logging.exception("Backend server failed")

    def start_frontend(self) -> None:
        dist_path = resource_path("client_dist")
        if not (dist_path / "index.html").exists():
            dist_path = resource_path("client", "dist")
        if not (dist_path / "index.html").exists():
            raise RuntimeError("Не найдена собранная frontend-папка client/dist. Сначала соберите EXE через launcher/build_exe.ps1.")
        handler = functools.partial(SpaHandler, directory=str(dist_path))
        self.frontend_server = ThreadingHTTPServer((FRONTEND_HOST, FRONTEND_PORT), handler)
        threading.Thread(target=self.frontend_server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        if self.backend_server:
            self.backend_server.should_exit = True
        if self.frontend_server:
            self.frontend_server.shutdown()


if __name__ == "__main__":
    VamosLauncher().start()
