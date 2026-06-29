import subprocess
import sys
import threading
import time

import psutil
import requests
from PySide6.QtCore import QObject, Signal


class FlmManager(QObject):
    flm_status_changed = Signal(bool, str)  # is_ready, message
    llm_service_ready = Signal(bool, str)  # is_ready, message
    DEFAULT_MODEL = "qwen3.5:4b"

    def __init__(self):
        super().__init__()
        self.process = None
        self.external_pid = None
        self.is_running = False
        self.is_ready = False
        self.monitor_thread = None
        self.current_model = self.DEFAULT_MODEL
        self.service_mode = "stopped"

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
                self.service_mode = "external"
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
        self.flm_status_changed.emit(False, "ASR servisi baslatiliyor...")
        self.is_ready = False
        self.external_pid = None
        self.current_model = selected_model
        self.service_mode = "asr"

        try:
            cmd = ["flm", "serve", "--asr", "1"]
            self._start_process(cmd)
            self._start_monitor()

        except FileNotFoundError:
            self.is_running = False
            self.service_mode = "stopped"
            self.flm_status_changed.emit(False, "Hata: 'flm' komutu bulunamadi. Kurulu mu?")
        except Exception as e:
            self.is_running = False
            self.service_mode = "stopped"
            self.flm_status_changed.emit(False, f"Hata: {str(e)}")

    def start_llm_service(self, model_name=None):
        selected_model = (model_name or self.DEFAULT_MODEL).strip() or self.DEFAULT_MODEL
        if self.is_running:
            self.stop_service(emit_status=False)

        self.flm_status_changed.emit(False, f"LLM modeli yukleniyor: {selected_model}")
        self.is_ready = False
        self.external_pid = None
        self.current_model = selected_model
        self.service_mode = "llm"

        try:
            cmd = ["flm", "serve", selected_model]
            self._start_process(cmd)
            self._start_monitor()

        except FileNotFoundError:
            self.is_running = False
            self.service_mode = "stopped"
            self.llm_service_ready.emit(False, "Hata: 'flm' komutu bulunamadi. Kurulu mu?")
            self.flm_status_changed.emit(False, "Hata: 'flm' komutu bulunamadi. Kurulu mu?")
        except Exception as e:
            self.is_running = False
            self.service_mode = "stopped"
            self.llm_service_ready.emit(False, f"Hata: {str(e)}")
            self.flm_status_changed.emit(False, f"Hata: {str(e)}")

    def restart_asr_service(self):
        selected_model = self.current_model
        self.stop_service(emit_status=False)
        self.start_service(selected_model)

    def _start_process(self, cmd):
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

    def _start_monitor(self):
        self.monitor_thread = threading.Thread(
            target=self._ping_until_ready, daemon=True
        )
        self.monitor_thread.start()

    def stop_service(self, emit_status=True):
        if self.process:
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                    try:
                        child.wait(5)
                    except psutil.TimeoutExpired:
                        pass
                parent.kill()
                try:
                    parent.wait(5)
                except psutil.TimeoutExpired:
                    pass
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                print(f"Stop hata: {e}")
            self.process = None

        if self.external_pid:
            try:
                proc = psutil.Process(self.external_pid)
                proc.kill()
                try:
                    proc.wait(5)
                except psutil.TimeoutExpired:
                    pass
            except Exception:
                pass
            self.external_pid = None

        self.is_running = False
        self.is_ready = False
        self.service_mode = "stopped"
        if emit_status:
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
                    if self.service_mode == "llm":
                        message = f"LLM hazir! (Port: 52625, Model: {self.current_model})"
                        self.flm_status_changed.emit(True, message)
                        self.llm_service_ready.emit(True, message)
                    else:
                        self.flm_status_changed.emit(
                            True, "ASR servisi hazir! (Port: 52625, LLM yuklenmedi)"
                        )
                    return
            except Exception:
                pass

            if elapsed > 0 and elapsed % 10 == 0:
                if self.service_mode == "llm":
                    self.flm_status_changed.emit(
                        False, f"LLM modeli yukleniyor... ({elapsed}s)"
                    )
                else:
                    self.flm_status_changed.emit(
                        False, f"ASR servisi aciliyor... ({elapsed}s)"
                    )

            time.sleep(3)
            elapsed += 3

        if not self.is_ready:
            message = "Zaman asimi: Servis baslatilamadi."
            if self.service_mode == "llm":
                self.llm_service_ready.emit(False, message)
            self.flm_status_changed.emit(False, message)
            self.is_running = False
            self.service_mode = "stopped"
            self.process = None

    def _monitor_logs(self):
        pass
