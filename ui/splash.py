import sys
import os
import urllib.request
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar, 
                               QMessageBox, QApplication, QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPalette

from core.hw_check import check_amd_npu, check_flm_installed

class BootstrapperThread(QThread):
    progress_update = Signal(int, str)
    error_occurred = Signal(str, str) # title, message
    flm_missing = Signal()
    checks_passed = Signal()

    def __init__(self):
        super().__init__()
        self.skip_npu = False # Set to true for debugging on non-AMD machines if needed

    def run(self):
        self.progress_update.emit(10, "Sistem donanımı taranıyor...")
        self.msleep(1000) # Gelişmiş hissiyat için ufak bir bekleme
        
        # 1. NPU Kontrolü
        if not self.skip_npu:
            self.progress_update.emit(30, "AMD NPU denetleniyor...")
            has_npu = check_amd_npu()
            if not has_npu:
                self.error_occurred.emit("Uyumsuz Donanım", 
                                         "Bu uygulama yerel yapay zeka işlemleri için AMD NPU (Neural Processing Unit) donanımına ihtiyaç duyar. Sisteminizde aktif bir AMD NPU bulunamadı.\n\nUygulama kapatılacak.")
                return
                
        self.progress_update.emit(50, "AMD NPU Bulundu. FLM Servisleri denetleniyor...")
        self.msleep(1000)
        
        # 2. FLM Kontrolü
        has_flm = check_flm_installed()
        if not has_flm:
            self.progress_update.emit(60, "FastFlowLM (FLM) bulunamadı. Kurulum bekleniyor...")
            self.flm_missing.emit()
            return
            
        self.progress_update.emit(90, "Tüm sistem gereksinimleri karşılandı. Başlatılıyor...")
        self.msleep(1000)
        self.progress_update.emit(100, "Başlatılıyor...")
        self.checks_passed.emit()


class DownloadFlmThread(QThread):
    download_progress = Signal(int)
    download_finished = Signal(str)
    download_error = Signal(str)

    def run(self):
        url = "https://github.com/FastFlowLM/FastFlowLM/releases/latest/download/flm-setup.exe"
        temp_dir = os.environ.get('TEMP', 'C:\\Temp')
        dest_path = os.path.join(temp_dir, "flm-setup.exe")
        
        try:
            def report_hook(count, block_size, total_size):
                if total_size > 0:
                    percent = int(count * block_size * 100 / total_size)
                    if percent > 100: percent = 100
                    self.download_progress.emit(percent)
                    
            urllib.request.urlretrieve(url, dest_path, reporthook=report_hook)
            self.download_finished.emit(dest_path)
        except Exception as e:
            self.download_error.emit(str(e))


class SplashScreen(QWidget):
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 300)
        
        self.setup_ui()
        self.start_bootstrapper()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main background frame
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
        
        # Title
        self.title_label = QLabel("Local AI Note Taker by Serhat")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #CBA6F7; font-size: 26px; font-weight: bold; font-family: 'Segoe UI', sans-serif;")
        
        self.subtitle_label = QLabel("Powered by AMD NPU")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("color: #A6ADC8; font-size: 14px; font-family: 'Segoe UI', sans-serif;")
        
        # Status
        self.status_label = QLabel("Sistem başlatılıyor...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #CDD6F4; font-size: 13px; margin-top: 20px;")
        
        # Progress Bar
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
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #89B4FA, stop:1 #CBA6F7);
                border-radius: 3px;
            }
        """)
        
        # Action Button (Hidden by default)
        self.action_btn = QPushButton("FastFlowLM İndir ve Kur")
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
        # DEV MODE: Bypass NPU check on dev machines if needed. Set to False for production!
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
        self.status_label.setText("Gereksinim Eksik: FastFlowLM Yüklü Değil.")
        self.action_btn.show()

    def start_flm_download(self):
        self.action_btn.setEnabled(False)
        self.action_btn.setText("İndiriliyor... %0")
        
        self.downloader = DownloadFlmThread()
        self.downloader.download_progress.connect(self.update_download_progress)
        self.downloader.download_finished.connect(self.install_flm)
        self.downloader.download_error.connect(self.handle_download_error)
        self.downloader.start()

    def update_download_progress(self, val):
        self.action_btn.setText(f"İndiriliyor... %{val}")
        self.progress_bar.setValue(val)

    def handle_download_error(self, err):
        QMessageBox.critical(self, "İndirme Hatası", f"FLM indirilirken bir hata oluştu:\n{err}")
        self.action_btn.setEnabled(True)
        self.action_btn.setText("Tekrar Dene")

    def install_flm(self, exe_path):
        self.action_btn.setText("Kurulum ekranını takip edin...")
        self.status_label.setText("FLM Kurulum Sihirbazı çalıştırılıyor...")
        
        try:
            # Setup'ı çalıştır ve bitmesini bekle (Kullanıcı manuel kuracak)
            subprocess.run([exe_path], check=False)
            
            # Kurulum bittikten sonra tekrar kontrol et
            self.action_btn.hide()
            self.status_label.setText("Kurulum doğrulama yapılıyor...")
            self.start_bootstrapper() # Tekrar baştan kontrol et
        except Exception as e:
            QMessageBox.critical(self, "Kurulum Hatası", f"Uygulama başlatılamadı:\n{e}")
            self.action_btn.setEnabled(True)
            self.action_btn.setText("Tekrar Dene")

    def on_checks_passed(self):
        # Kısa bir gecikme ile ana pencereye geç
        QTimer.singleShot(500, self.finished.emit)
