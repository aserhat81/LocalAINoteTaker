import os
import subprocess
import urllib.request

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from core.hw_check import check_amd_npu, check_flm_installed


class BootstrapperThread(QThread):
    progress_update = Signal(int, str)
    error_occurred = Signal(str, str)
    flm_missing = Signal()
    checks_passed = Signal()

    def __init__(self):
        super().__init__()
        self.skip_npu = False

    def run(self):
        self.progress_update.emit(10, "Sistem donanimi taraniyor...")
        self.msleep(500)

        has_npu = False
        if not self.skip_npu:
            self.progress_update.emit(30, "AMD NPU denetleniyor...")
            has_npu = check_amd_npu()

        self.progress_update.emit(60, "Yerel AI servisleri denetleniyor...")
        self.msleep(500)

        has_flm = check_flm_installed()
        if has_npu and has_flm:
            self.progress_update.emit(90, "FLM hazir. Baslatiliyor...")
        else:
            self.progress_update.emit(
                90,
                "Opsiyonel servisler daha sonra secilebilir. Baslatiliyor...",
            )

        self.msleep(500)
        self.progress_update.emit(100, "Baslatiliyor...")
        self.checks_passed.emit()


class DownloadFlmThread(QThread):
    download_progress = Signal(int)
    download_finished = Signal(str)
    download_error = Signal(str)

    def run(self):
        url = "https://github.com/FastFlowLM/FastFlowLM/releases/latest/download/flm-setup.exe"
        temp_dir = os.environ.get("TEMP", "C:\\Temp")
        dest_path = os.path.join(temp_dir, "flm-setup.exe")

        try:
            def report_hook(count, block_size, total_size):
                if total_size > 0:
                    percent = int(count * block_size * 100 / total_size)
                    if percent > 100:
                        percent = 100
                    self.download_progress.emit(percent)

            urllib.request.urlretrieve(url, dest_path, reporthook=report_hook)
            self.download_finished.emit(dest_path)
        except Exception as e:
            self.download_error.emit(str(e))


class SplashScreen(QWidget):
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 320)
        self.setStyleSheet("background:transparent;")

        self.setup_ui()
        self.start_bootstrapper()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.bg_frame = QWidget(self)
        self.bg_frame.setObjectName("BgFrame")
        self.bg_frame.setStyleSheet("""
            QWidget#BgFrame {
                background-color: #1E1E2E;
                border-radius: 15px;
                border: 1px solid #313244;
            }
        """)
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(30, 40, 30, 40)

        self.title_label = QLabel("Local AI Suite")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            "color: #CBA6F7; font-size: 26px; font-weight: bold; "
            "font-family: 'Segoe UI', sans-serif;"
        )

        self.subtitle_label = QLabel("Private local AI workspace with optional local providers")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet(
            "color: #A6ADC8; font-size: 14px; font-family: 'Segoe UI', sans-serif;"
        )

        self.status_label = QLabel("Sistem baslatiliyor...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #CDD6F4; font-size: 13px; margin-top: 20px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setObjectName("Progress")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #313244;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89B4FA, stop:1 #CBA6F7);
                border-radius: 3px;
            }
        """)

        self.action_btn = QPushButton("FastFlowLM Indir ve Kur")
        self.action_btn.setFixedHeight(40)
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.setStyleSheet("""
            QPushButton {
                background-color: #89B4FA;
                color: #11111B;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #B4BEFE;
            }
        """)
        self.action_btn.hide()
        self.action_btn.clicked.connect(self.start_flm_download)

        bg_layout.addWidget(self.title_label)
        bg_layout.addWidget(self.subtitle_label)
        bg_layout.addStretch()
        bg_layout.addWidget(self.status_label)
        bg_layout.addWidget(self.progress_bar)
        bg_layout.addWidget(self.action_btn)

        layout.addWidget(self.bg_frame)

    def start_bootstrapper(self):
        self.bootstrapper = BootstrapperThread()
        self.bootstrapper.skip_npu = False
        self.bootstrapper.progress_update.connect(self.update_progress)
        self.bootstrapper.error_occurred.connect(self.show_error_and_exit)
        self.bootstrapper.flm_missing.connect(self.prompt_flm_install)
        self.bootstrapper.checks_passed.connect(self.on_checks_passed)
        self.bootstrapper.start()

    def update_progress(self, val, text):
        self.progress_bar.setValue(val)
        self.status_label.setText(text)

    def show_error_and_exit(self, title, message):
        QMessageBox.critical(self, title, message)
        QApplication.quit()

    def prompt_flm_install(self):
        self.status_label.setText("FastFlowLM yuklu degil. Dilerseniz kurabilirsiniz.")
        self.action_btn.show()

    def start_flm_download(self):
        self.action_btn.setEnabled(False)
        self.action_btn.setText("Indiriliyor... %0")

        self.downloader = DownloadFlmThread()
        self.downloader.download_progress.connect(self.update_download_progress)
        self.downloader.download_finished.connect(self.install_flm)
        self.downloader.download_error.connect(self.handle_download_error)
        self.downloader.start()

    def update_download_progress(self, val):
        self.action_btn.setText(f"Indiriliyor... %{val}")
        self.progress_bar.setValue(val)

    def handle_download_error(self, err):
        QMessageBox.critical(self, "Indirme Hatasi", f"FLM indirilirken hata olustu:\n{err}")
        self.action_btn.setEnabled(True)
        self.action_btn.setText("Tekrar Dene")

    def install_flm(self, exe_path):
        self.action_btn.setText("Kurulum ekranini takip edin...")
        self.status_label.setText("FLM kurulum sihirbazi calistiriliyor...")

        try:
            subprocess.run([exe_path], check=False)
            self.action_btn.hide()
            self.status_label.setText("Kurulum dogrulaniyor...")
            self.start_bootstrapper()
        except Exception as e:
            QMessageBox.critical(self, "Kurulum Hatasi", f"Uygulama baslatilamadi:\n{e}")
            self.action_btn.setEnabled(True)
            self.action_btn.setText("Tekrar Dene")

    def on_checks_passed(self):
        QTimer.singleShot(500, self.finished.emit)
