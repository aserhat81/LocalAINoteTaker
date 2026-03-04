import subprocess
import threading
import time
import sys
import psutil
import requests
from PySide6.QtCore import QObject, Signal


class FlmManager(QObject):
    flm_status_changed = Signal(bool, str)  # is_ready, message

    def __init__(self):
        super().__init__()
        self.process = None         # Bizim başlattığımız süreç
        self.external_pid = None    # Dışarıdan çalışan süreç PID'i
        self.is_running = False
        self.is_ready = False
        self.monitor_thread = None

        # Uygulama açılınca arka planda FLM çalışıyor mu kontrol et
        threading.Thread(target=self._initial_check, daemon=True).start()

    # ------------------------------------------------------------------ #
    # Kontrol                                                              #
    # ------------------------------------------------------------------ #

    def _initial_check(self):
        """Uygulama açılınca FLM zaten çalışıyor mu kontrol eder."""
        time.sleep(1)  # UI yüklenmesini bekle
        self._ping_once()

    def _ping_once(self):
        """Portu kontrol eder. Çalışıyorsa sinyal gönderir, True döner."""
        try:
            resp = requests.get("http://127.0.0.1:52625/v1/models", timeout=2)
            if resp.status_code == 200:
                self.is_running = True
                self.is_ready = True
                self.external_pid = self._find_pid_on_port(52625)
                self.flm_status_changed.emit(True, "Zaten Çalışıyor (Hazır)")
                return True
        except Exception:
            pass
        return False

    def _find_pid_on_port(self, port):
        """Belirtilen portu dinleyen sürecin PID'ini döndürür."""
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    return conn.pid
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------ #
    # Başlat / Durdur                                                      #
    # ------------------------------------------------------------------ #

    def start_service(self):
        """FLM'i başlatır. Zaten çalışıyorsa ikinci instance açmaz."""
        # Zaten çalışıyor mu?
        if self._ping_once():
            return  # _ping_once sinyal gönderdi, çık

        self.flm_status_changed.emit(False, "Başlatılıyor...")
        self.is_ready = False
        self.external_pid = None

        try:
            # "flm serve" komutu — port 52625'te REST API açar
            cmd = ["flm", "serve", "gemma3:4b", "--asr", "1"]

            creationflags = 0
            startupinfo = None
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            # stdout/stderr'i DEVNULL'a yönlendir — PIPE kullanmak
            # pipe buffer'ı doldurup FLM'i kilitliyor
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                startupinfo=startupinfo
            )
            self.is_running = True

            # Hazırlık tespiti sadece API ping ile yapılır (log okuma yok)
            self.monitor_thread = threading.Thread(
                target=self._ping_until_ready, daemon=True
            )
            self.monitor_thread.start()

        except FileNotFoundError:
            self.is_running = False
            self.flm_status_changed.emit(False, "Hata: 'flm' komutu bulunamadı. Kurulu mu?")
        except Exception as e:
            self.is_running = False
            self.flm_status_changed.emit(False, f"Hata: {str(e)}")

    def stop_service(self):
        """Bizim başlattığımız veya dışarıdan çalışan FLM'i durdurur."""
        # 1. Bizim başlattığımız process
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

        # 2. Dışarıdan çalışan process
        if self.external_pid:
            try:
                psutil.Process(self.external_pid).kill()
            except Exception:
                pass
            self.external_pid = None

        self.is_running = False
        self.is_ready = False
        self.flm_status_changed.emit(False, "Durduruldu.")

    # ------------------------------------------------------------------ #
    # Log izleyici                                                         #
    # ------------------------------------------------------------------ #

    def _ping_until_ready(self):
        """FLM hazır olana kadar her 3 sn'de bir API ping atar."""
        # Model yüklemesi uzun sürebilir (Gemma3: 1-3 dk)
        max_wait = 300  # 5 dakika timeout
        elapsed = 0

        while self.is_running and elapsed < max_wait:
            # Süreç kapandı mı kontrol et
            if self.process and self.process.poll() is not None:
                break

            try:
                resp = requests.get("http://127.0.0.1:52625/v1/models", timeout=2)
                if resp.status_code == 200:
                    self.is_ready = True
                    self.flm_status_changed.emit(True, "Hazır! (Port: 52625)")
                    return
            except Exception:
                pass

            # Her 10 sn'de kullanıcıya "hâlâ yüklüyor" mesajı ver
            if elapsed > 0 and elapsed % 10 == 0:
                self.flm_status_changed.emit(False, f"Modeller yükleniyor... ({elapsed}s)")

            time.sleep(3)
            elapsed += 3

        if not self.is_ready:
            self.flm_status_changed.emit(False, "Zaman aşımı: Servis başlatılamadı.")
            self.is_running = False
            self.process = None

    def _monitor_logs(self):
        """Eski log okuyucu - artık kullanılmıyor, geriye dönük uyumluluk için."""
        pass

