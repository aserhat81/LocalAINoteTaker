import subprocess
import sys
import threading
import time

import psutil
import requests
from PySide6.QtCore import QObject, Signal


class FlmManager(QObject):
    flm_status_changed = Signal(bool, str)  # is_ready, message
    DEFAULT_MODEL = "qwen3.5:4b"

    def __init__(self):
        super().__init__()
        self.process = None
        self.external_pid = None
        self.is_running = False
        self.is_ready = False
        self.monitor_thread = None
        self.current_model = self.DEFAULT_MODEL

        threading.Thread(target=self._initial_check, daemon=True).start()

    def _initial_check(self):
        time.sleep(1)
        self._ping_once()

    def _ping_once(self):
        try:
            resp = requests.get("http://127.0.0.1:52625/v1/models", timeout=2)
            if resp.status_code == 200:
                self.is_running = True
                self.is_ready = True
                self.external_pid = self._find_pid_on_port(52625)
                self.flm_status_changed.emit(True, "Zaten Calisiyor (Hazir)")
                return True
        except Exception:
            pass
        return False

    def _find_pid_on_port(self, port):
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port == port and conn.status == "LISTEN":
                    return conn.pid
        except Exception:
            pass
        return None

    def start_service(self, model_name=None):
        if self._ping_once():
            return

        selected_model = (model_name or self.DEFAULT_MODEL).strip() or self.DEFAULT_MODEL
        self.flm_status_changed.emit(False, "Baslatiliyor...")
        self.is_ready = False
        self.external_pid = None
        self.current_model = selected_model

        try:
            cmd = ["flm", "serve", selected_model, "--asr", "1"]

            creationflags = 0
            startupinfo = None
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            self.is_running = True

            self.monitor_thread = threading.Thread(
                target=self._ping_until_ready, daemon=True
            )
            self.monitor_thread.start()

        except FileNotFoundError:
            self.is_running = False
            self.flm_status_changed.emit(False, "Hata: 'flm' komutu bulunamadi. Kurulu mu?")
        except Exception as e:
            self.is_running = False
            self.flm_status_changed.emit(False, f"Hata: {str(e)}")

    def stop_service(self):
        if self.process:
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                print(f"Stop hata: {e}")
            self.process = None

        if self.external_pid:
            try:
                psutil.Process(self.external_pid).kill()
            except Exception:
                pass
            self.external_pid = None

        self.is_running = False
        self.is_ready = False
        self.flm_status_changed.emit(False, "Durduruldu.")

    def _ping_until_ready(self):
        max_wait = 300
        elapsed = 0

        while self.is_running and elapsed < max_wait:
            if self.process and self.process.poll() is not None:
                break

            try:
                resp = requests.get("http://127.0.0.1:52625/v1/models", timeout=2)
                if resp.status_code == 200:
                    self.is_ready = True
                    self.flm_status_changed.emit(
                        True, f"Hazir! (Port: 52625, Model: {self.current_model})"
                    )
                    return
            except Exception:
                pass

            if elapsed > 0 and elapsed % 10 == 0:
                self.flm_status_changed.emit(
                    False, f"Modeller yukleniyor... ({elapsed}s)"
                )

            time.sleep(3)
            elapsed += 3

        if not self.is_ready:
            self.flm_status_changed.emit(False, "Zaman asimi: Servis baslatilamadi.")
            self.is_running = False
            self.process = None

    def _monitor_logs(self):
        pass
