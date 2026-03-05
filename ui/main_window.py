import sys
import locale
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QComboBox, QTextEdit,
                               QGroupBox, QStatusBar, QMessageBox,
                               QDialog, QListWidget, QSplitter, QProgressBar)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from core.flm_manager import FlmManager
from core.audio_capture import AudioCaptureManager
from core.asr_client import AsrClientThread
from core.llm_analyzer import LlmAnalyzerThread
from database.db_manager import DatabaseManager
from utils.email_sender import send_email_mailto

# ─── Lokalizasyon sözlüğü ────────────────────────────────────────────────────
I18N = {
    "tr": {
        "window_title": "Local AI Note Taker by Serhat",
        "btn_history": "📂 Geçmiş Toplantılar",
        "lang_label": "Dil:",
        "service_group": "FastFlowLM Servis Durumu",
        "status_off": "🔴 Kapalı",
        "btn_start_flm": "Servisi Başlat (NPU)",
        "btn_stop_flm": "Durdur",
        "btn_flm_external": "Harici Servis Aktif",
        "record_group": "Toplantı Kayıt ve Altyazı",
        "mic_label": "Mikrofon:",
        "mode_label": "Mod:",
        "mode_online": "Online Toplantı (Sistem + Mikrofon)",
        "mode_mic": "Sadece Mikrofon (Dikte)",
        "btn_start_rec": "▶ Kayda Başla",
        "btn_pause_rec": "⏸ Kaydı Duraklat",
        "btn_resume_rec": "▶ Kayda Devam Et",
        "btn_finish": "⏹ Toplantıyı Bitir & Özet Çıkart",
        "btn_new_rec": "▶ Yeni Kayda Başla",
        "subtitle_placeholder": "Altyazılar burada gerçek zamanlı olarak akacak...",
        "status_ready": "Sistem hazır. Lütfen FastFlowLM servisini başlatın.",
        "rec_started": "<b>--- Toplantı Kaydı Başladı ---</b><br>",
        "analyzing": "--- Toplantı Bitti. Gemma3 ile Analiz Ediliyor... ---",
        "analyzing_status": "Toplantı özetleniyor, AI çalışıyor...",
        "saved_status": "Kayıt veritabanına eklendi.",
        "email_title": "Toplantı Bitti",
        "email_msg": "Toplantı özetlendi ve kaydedildi.\nÖzeti e-posta ile göndermek ister misiniz?",
        "email_subject": "Toplantı Notu: ",
        "history_title": "Geçmiş Toplantılar",
        "history_list_label": "Toplantılar",
        "history_detail_label": "Detay Seçin",
        "btn_send_email": "📧 E-Posta ile Gönder",
        "default_mic": "Varsayılan Sistem Mikrofonu",
        "analysis_failed": "Analiz Başarısız:",
        "btn_about": "❓ Hakkında",
        "about_title": "Hakkında",
        "about_text": "<b>Local AI Note Taker</b><br><br>Bu uygulama <b>AMD NPU</b> kullanılarak geliştirilmiştir.<br><br>Geliştirici Serhat Youtube kanalı da Teknoloji ve Hayat: <a href='https://www.youtube.com/@TeknolojiHayat' style='color:#89B4FA;'>https://www.youtube.com/@TeknolojiHayat</a>",
    },
    "en": {
        "window_title": "Local AI Note Taker by Serhat",
        "btn_history": "📂 Meeting History",
        "lang_label": "Language:",
        "service_group": "FastFlowLM Service Status",
        "status_off": "🔴 Offline",
        "btn_start_flm": "Start Service (NPU)",
        "btn_stop_flm": "Stop",
        "btn_flm_external": "External Service Active",
        "record_group": "Meeting Recording & Subtitles",
        "mic_label": "Microphone:",
        "mode_label": "Mode:",
        "mode_online": "Online Meeting (System + Mic)",
        "mode_mic": "Microphone Only (Dictation)",
        "btn_start_rec": "▶ Start Recording",
        "btn_pause_rec": "⏸ Pause Recording",
        "btn_resume_rec": "▶ Resume Recording",
        "btn_finish": "⏹ Finish Meeting & Summarize",
        "btn_new_rec": "▶ Start New Recording",
        "subtitle_placeholder": "Real-time subtitles will appear here...",
        "status_ready": "Ready. Please start the FastFlowLM service.",
        "rec_started": "<b>--- Meeting Recording Started ---</b><br>",
        "analyzing": "--- Meeting Ended. Analyzing with Gemma3... ---",
        "analyzing_status": "Summarizing meeting, AI is working...",
        "saved_status": "Meeting saved to database.",
        "email_title": "Meeting Finished",
        "email_msg": "Meeting was summarized and saved.\nWould you like to send the summary by email?",
        "email_subject": "Meeting Notes: ",
        "history_title": "Meeting History",
        "history_list_label": "Meetings",
        "history_detail_label": "Select a Meeting",
        "btn_send_email": "📧 Send by Email",
        "default_mic": "Default System Microphone",
        "analysis_failed": "Analysis Failed:",
        "btn_about": "❓ About",
        "about_title": "About",
        "about_text": "<b>Local AI Note Taker</b><br><br>This application was developed using <b>AMD NPU</b>.<br><br>Developer Serhat YouTube Channel Teknoloji ve Hayat: <a href='https://www.youtube.com/@TeknolojiHayat' style='color:#89B4FA;'>https://www.youtube.com/@TeknolojiHayat</a>",
    }
}

def detect_os_lang():
    """İşletim sistemi dilini tespit et, TR veya EN döndür."""
    try:
        lang = locale.getdefaultlocale()[0] or ""
        return "tr" if lang.lower().startswith("tr") else "en"
    except Exception:
        return "en"


class HistoryDialog(QDialog):
    def __init__(self, db, lang="tr", parent=None):
        super().__init__(parent)
        self.db = db
        self.lang = lang
        t = I18N[lang]
        self.setWindowTitle(t["history_title"])
        self.setMinimumSize(800, 500)
        self.current_title = ""
        self.current_summary = ""

        self.setStyleSheet("""
            QDialog { background-color: #1E1E2E; color: #CDD6F4; }
            QLabel { color: #CDD6F4; font-weight: bold; }
            QListWidget { background-color: #11111B; color: #A6E3A1; border: 1px solid #313244; padding: 5px; }
            QTextEdit { background-color: #11111B; color: #CDD6F4; border: 1px solid #313244; padding: 10px; }
            QPushButton { background-color: #89B4FA; color: #11111B; padding: 6px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #B4BEFE; }
        """)

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel(t["history_list_label"]))
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_meeting_selected)
        left_layout.addWidget(self.list_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_title = QLabel(t["history_detail_label"])
        self.detail_title.setStyleSheet("font-size: 18px; color: #CBA6F7;")
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)

        btn_layout = QHBoxLayout()
        self.btn_email = QPushButton(t["btn_send_email"])
        self.btn_email.clicked.connect(self.send_current_email)
        self.btn_email.setEnabled(False)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_email)

        right_layout.addWidget(self.detail_title)
        right_layout.addWidget(self.detail_text)
        right_layout.addLayout(btn_layout)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([250, 550])
        layout.addWidget(splitter)
        self.load_meetings()

    def load_meetings(self):
        self.list_widget.clear()
        for rec in self.db.get_recent_meetings():
            self.list_widget.addItem(f"{rec[2][:16]} - {rec[1]}")
            self.list_widget.item(self.list_widget.count() - 1).setData(Qt.UserRole, rec[0])

    def on_meeting_selected(self):
        items = self.list_widget.selectedItems()
        if not items:
            return
        record = self.db.get_meeting_by_id(items[0].data(Qt.UserRole))
        if record:
            self.current_title = record[0]
            self.current_summary = record[3]
            self.detail_title.setText(f"{record[0]} ({record[1]})")
            self.detail_text.setText(f"ÖZET / SUMMARY:\n{record[3]}\n\n---\nTRANSKRİPT:\n{record[2]}")
            self.btn_email.setEnabled(True)

    def send_current_email(self):
        t = I18N[self.lang]
        send_email_mailto(f"{t['email_subject']}{self.current_title}", self.current_summary)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(950, 700)
        self.setStyleSheet("""
            QMainWindow { background-color: #1E1E2E; color: #CDD6F4; }
            QLabel { color: #CDD6F4; }
            QGroupBox { border: 1px solid #45475A; border-radius: 6px; margin-top: 10px; font-weight: bold; color: #A6ADC8; }
            QGroupBox:title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QPushButton { background-color: #313244; color: #CDD6F4; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #45475A; }
            QPushButton:disabled { background-color: #181825; color: #585B70; }
            QComboBox { background-color: #313244; color: #CDD6F4; border: 1px solid #45475A; border-radius: 4px; padding: 4px; }
            QTextEdit { background-color: #11111B; color: #CBA6F7; border: 1px solid #313244; border-radius: 6px; padding: 10px; font-size: 14px; }
        """)

        # Managers
        self.flm_manager = FlmManager()
        self.flm_manager.flm_status_changed.connect(self.on_flm_status_changed)
        self.audio_manager = AudioCaptureManager()
        self.audio_manager.chunk_ready.connect(self.on_audio_chunk_ready)
        self.db = DatabaseManager()

        self.asr_threads = []   # Güçlü referans listesi
        self.asr_queue = []     # İşlem sırası kuyruğu
        self.meeting_active = False  # True iken ses paketleri işlenir
        self.llm_thread = None
        self.full_transcript_buffer = ""

        # Dili OS'dan algıla, sonra combo ile değiştirilebilir
        self._lang = detect_os_lang()

        self.setup_ui()
        self.apply_language()   # İlk dil uygulaması
        self.populate_mics()

    # ─── Dil ─────────────────────────────────────────────────────────────────

    def t(self, key):
        """Aktif dildeki metni döndürür."""
        return I18N[self._lang].get(key, key)

    def on_lang_changed(self, index):
        self._lang = "tr" if index == 0 else "en"
        self.apply_language()

    def apply_language(self):
        """Tüm UI öğelerini aktif dile günceller."""
        t = I18N[self._lang]
        self.setWindowTitle(t["window_title"])
        self.btn_history.setText(t["btn_history"])
        self.btn_about.setText(t["btn_about"])
        if hasattr(self, 'lang_label_widget'):
            self.lang_label_widget.setText(t["lang_label"])
        self.service_group.setTitle(t["service_group"])
        self.record_group.setTitle(t["record_group"])
        self.mic_label.setText(t["mic_label"])
        self.mode_label.setText(t["mode_label"])
        self.subtitle_box.setPlaceholderText(t["subtitle_placeholder"])
        self.statusBar_widget.showMessage(t["status_ready"])

        # Mod combo
        curr_mode = self.mode_combo.currentIndex()
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        self.mode_combo.addItems([t["mode_online"], t["mode_mic"]])
        self.mode_combo.setCurrentIndex(curr_mode)
        self.mode_combo.blockSignals(False)

        # Kayıt butonu metni (duruma göre)
        if not self.audio_manager.is_recording:
            self.btn_start_record.setText(t["btn_start_rec"])
        self.btn_finish_meeting.setText(t["btn_finish"])

        # FLM buton durumu
        if self.flm_manager.is_ready:
            self.status_indicator.setText("🟢 " + ("Çalışıyor" if self._lang == "tr" else "Running"))
            self.btn_start_flm.setText(t["btn_stop_flm"])
        else:
            self.status_indicator.setText(t["status_off"])
            self.btn_start_flm.setText(t["btn_start_flm"])

        # Mic combo varsayılan
        if self.mic_combo.count() > 0:
            self.mic_combo.setItemText(0, t["default_mic"])

    # ─── UI Setup ────────────────────────────────────────────────────────────

    def setup_ui(self):
        center = QWidget()
        self.setCentralWidget(center)
        main_layout = QVBoxLayout(center)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Top bar
        top = QHBoxLayout()
        app_title = QLabel("Local AI Note Taker by Serhat")
        app_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89B4FA;")

        self.btn_history = QPushButton()
        self.btn_history.clicked.connect(self.open_history)

        self.btn_about = QPushButton()
        self.btn_about.clicked.connect(self.show_about)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Türkçe", "English"])
        self.lang_combo.setCurrentIndex(0 if self._lang == "tr" else 1)
        self.lang_combo.currentIndexChanged.connect(self.on_lang_changed)

        self.lang_label_widget = QLabel()
        top.addWidget(app_title)
        top.addStretch()
        top.addWidget(self.btn_history)
        top.addWidget(self.btn_about)
        top.addSpacing(15)
        top.addWidget(self.lang_label_widget)
        top.addWidget(self.lang_combo)
        main_layout.addLayout(top)

        # Service group
        self.service_group = QGroupBox()
        service_layout = QHBoxLayout(self.service_group)
        self.status_indicator = QLabel()
        self.status_indicator.setStyleSheet("color: #F38BA8; font-weight: bold; font-size: 14px;")
        self.btn_start_flm = QPushButton()
        self.btn_start_flm.setStyleSheet("background-color: #A6E3A1; color: #11111B;")
        self.btn_start_flm.clicked.connect(self.toggle_flm_service)
        service_layout.addWidget(self.status_indicator)
        service_layout.addWidget(self.btn_start_flm)
        service_layout.addStretch()
        main_layout.addWidget(self.service_group)

        # Recording group
        self.record_group = QGroupBox()
        self.record_group.setEnabled(False)
        record_layout = QVBoxLayout(self.record_group)

        controls = QHBoxLayout()
        self.mic_label = QLabel()
        self.mic_combo = QComboBox()
        self.mic_combo.setMinimumWidth(200)
        self.mode_label = QLabel()
        self.mode_combo = QComboBox()

        self.btn_start_record = QPushButton()
        self.btn_start_record.setStyleSheet("background-color: #89B4FA; color: #11111B;")
        self.btn_start_record.clicked.connect(self.toggle_recording)

        self.btn_finish_meeting = QPushButton()
        self.btn_finish_meeting.setStyleSheet("background-color: #F38BA8; color: #11111B;")
        self.btn_finish_meeting.setEnabled(False)
        self.btn_finish_meeting.clicked.connect(self.finish_meeting)

        controls.addWidget(self.mic_label)
        controls.addWidget(self.mic_combo)
        controls.addSpacing(10)
        controls.addWidget(self.mode_label)
        controls.addWidget(self.mode_combo)
        controls.addWidget(self.btn_start_record)
        controls.addWidget(self.btn_finish_meeting)
        controls.addStretch()
        record_layout.addLayout(controls)

        # Ses Seviyesi Göstergesi (Audio Level)
        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(False)
        self.level_bar.setFixedHeight(8)
        self.level_bar.setStyleSheet("""
            QProgressBar { border: none; background-color: #181825; border-radius: 4px; }
            QProgressBar::chunk { background-color: #A6E3A1; border-radius: 4px; }
        """)
        record_layout.addWidget(self.level_bar)
        self.audio_manager.audio_level.connect(self.level_bar.setValue)

        self.subtitle_box = QTextEdit()
        self.subtitle_box.setReadOnly(True)
        record_layout.addWidget(self.subtitle_box)
        main_layout.addWidget(self.record_group)

        self.statusBar_widget = QStatusBar()
        self.setStatusBar(self.statusBar_widget)

    def populate_mics(self):
        mics = self.audio_manager.get_input_devices()
        self.mic_combo.clear()
        self.mic_combo.addItem(self.t("default_mic"), None)
        for mic in mics:
            self.mic_combo.addItem(mic["name"], mic["index"])

    # ─── FLM ─────────────────────────────────────────────────────────────────

    def toggle_flm_service(self):
        if not self.flm_manager.is_running:
            self.btn_start_flm.setText(self.t("btn_stop_flm"))
            self.btn_start_flm.setStyleSheet("background-color: #F38BA8; color: #11111B;")
            self.status_indicator.setText("🟡 " + ("Başlatılıyor..." if self._lang == "tr" else "Starting..."))
            self.status_indicator.setStyleSheet("color: #F9E2AF; font-weight: bold; font-size: 14px;")
            self.flm_manager.start_service()
        else:
            self.flm_manager.stop_service()

    def on_flm_status_changed(self, is_ready, message):
        if is_ready:
            self.status_indicator.setText("🟢 " + ("Çalışıyor" if self._lang == "tr" else "Running"))
            self.status_indicator.setStyleSheet("color: #A6E3A1; font-weight: bold; font-size: 14px;")
            self.btn_start_flm.setText(self.t("btn_stop_flm"))
            self.btn_start_flm.setStyleSheet("background-color: #F38BA8; color: #11111B;")
            self.record_group.setEnabled(True)
            self.statusBar_widget.showMessage(f"FLM: {message}")
        else:
            loading_words = ["Başlatılıyor", "Loading", "Configuring", "Starting", "Modeller"]
            if any(w in message for w in loading_words):
                self.status_indicator.setText(f"🟡 {message[:45]}...")
                self.status_indicator.setStyleSheet("color: #F9E2AF; font-weight: bold; font-size: 14px;")
            else:
                self.status_indicator.setText(self.t("status_off"))
                self.status_indicator.setStyleSheet("color: #F38BA8; font-weight: bold; font-size: 14px;")
                self.btn_start_flm.setText(self.t("btn_start_flm"))
                self.btn_start_flm.setStyleSheet("background-color: #A6E3A1; color: #11111B;")
                self.record_group.setEnabled(False)
            self.statusBar_widget.showMessage(f"FLM: {message}")

    # ─── Kayıt ───────────────────────────────────────────────────────────────

    def toggle_recording(self):
        if not self.audio_manager.is_recording:
            mode = "online" if self.mode_combo.currentIndex() == 0 else "mic_only"
            
            # Eğer uygulama 'yeni toplantı' modundaysa (yani BİTİR butonu kapalıysa) ekranı temizle
            if not self.btn_finish_meeting.isEnabled():
                self.full_transcript_buffer = ""
                self.subtitle_box.clear()
                self.subtitle_box.append(self.t("rec_started"))
            else:
                self.subtitle_box.append("<br><i>[Kayıt Devam Ediyor]</i><br>")
                
            self.meeting_active = True
            self.audio_manager.start_recording(mode, self.mic_combo.currentData())
            self.btn_start_record.setText(self.t("btn_pause_rec"))
            self.btn_start_record.setStyleSheet("background-color: #F9E2AF; color: #11111B;")
            self.mode_combo.setEnabled(False)
            self.mic_combo.setEnabled(False)
            self.btn_finish_meeting.setEnabled(True)
        else:
            self.audio_manager.stop_recording()
            self.btn_start_record.setText(self.t("btn_resume_rec"))
            self.btn_start_record.setStyleSheet("background-color: #89B4FA; color: #11111B;")
            self.subtitle_box.append("<i>[Kayıt Duraklatıldı]</i>")

    def finish_meeting(self):
        self.meeting_active = False   # Bundan sonra gelen ses paketleri işlenmeyecek
        self.asr_queue.clear()        # Kuyruktaki bekleyen paketleri temizle
        self.audio_manager.stop_recording()
        self.btn_start_record.setText(self.t("btn_new_rec"))
        self.btn_start_record.setStyleSheet("background-color: #89B4FA; color: #11111B;")
        self.mode_combo.setEnabled(True)
        self.mic_combo.setEnabled(True)
        self.btn_finish_meeting.setEnabled(False)

        color_warn = "#F9E2AF"
        self.subtitle_box.append(f"<br><span style='color: {color_warn};'><b>{self.t('analyzing')}</b></span><br>")
        self.statusBar_widget.showMessage(self.t("analyzing_status"))

        lang = "tr" if self.lang_combo.currentIndex() == 0 else "en"
        self.llm_thread = LlmAnalyzerThread(self.full_transcript_buffer, language=lang)
        self.llm_thread.analysis_ready.connect(self.on_analysis_completed)
        self.llm_thread.analysis_error.connect(self.on_analysis_error)
        self.llm_thread.start()

    def on_analysis_completed(self, title, summary):
        self.db.save_meeting(title, self.full_transcript_buffer, summary)
        disp_html = f"<br><b><span style='color: #A6E3A1; font-size:16px;'>{title}</span></b><br><span style='color: #CDD6F4;'>{summary}</span>"
        self.subtitle_box.append(disp_html.replace('\n', '<br>'))
        self.statusBar_widget.showMessage(self.t("saved_status"))

        reply = QMessageBox.question(
            self, self.t("email_title"), self.t("email_msg"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            send_email_mailto(f"{self.t('email_subject')}{title}", summary)

    def on_analysis_error(self, err_msg):
        self.statusBar_widget.showMessage(err_msg)
        self.subtitle_box.append(f"<br><b style='color:#F38BA8;'>{self.t('analysis_failed')}</b> {err_msg}")

    # ─── ASR ─────────────────────────────────────────────────────────────────

    # ─── ASR ─────────────────────────────────────────────────────────────────

    def on_audio_chunk_ready(self, wav_bytes, source_label):
        # Toplantı bitti ise (finish_meeting çağrıldıysa) ses paketlerini yok say
        if not self.meeting_active:
            return
        # Paketleri sıraya al (Queue)
        self.asr_queue.append((wav_bytes, source_label))
        self._process_asr_queue()

    def _process_asr_queue(self):
        # Aynı anda en fazla 2 Whisper işlemi yapılsın (NPU/CPU şişmemesi için)
        MAX_CONCURRENT = 2
        
        while len(self.asr_threads) < MAX_CONCURRENT and self.asr_queue:
            wav_bytes, source_label = self.asr_queue.pop(0)
            
            lang = "tr" if self.lang_combo.currentIndex() == 0 else "en"
            worker = AsrClientThread(wav_bytes, source_label, language=lang)
            worker.transcription_ready.connect(self.append_subtitle)
            worker.transcription_error.connect(self.show_asr_error)
            
            # İşlem bitince sıradaki paketi işle
            worker.finished.connect(lambda w=worker: self._remove_asr_thread(w))
            
            self.asr_threads.append(worker)
            worker.start()

    def _remove_asr_thread(self, worker):
        try:
            if worker in self.asr_threads:
                self.asr_threads.remove(worker)
        except Exception:
            pass
        # Bir iş bitti, sıradakini kontrol et
        self._process_asr_queue()

    def append_subtitle(self, text, source_label):
        self.full_transcript_buffer += f"[{source_label}]: {text}\n"
        color = "#89DCEB" if source_label == "BEN" else "#F9E2AF"
        formatted = f'<span style="color: {color};"><b>[{source_label}]</b></span>: {text}<br>'
        cursor = self.subtitle_box.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.subtitle_box.setTextCursor(cursor)
        self.subtitle_box.insertHtml(formatted)
        self.subtitle_box.verticalScrollBar().setValue(self.subtitle_box.verticalScrollBar().maximum())

    def show_asr_error(self, message):
        self.statusBar_widget.showMessage(message)

    def closeEvent(self, event):
        self.audio_manager.stop_recording()
        self.flm_manager.stop_service()
        # Queue'yu temizle
        self.asr_queue = []
        for t in self.asr_threads:
            try:
                t.wait(500)
            except Exception: pass
        if self.llm_thread and self.llm_thread.isRunning():
            try:
                self.llm_thread.wait(500)
            except Exception: pass
        event.accept()

    def show_about(self):
        t = I18N[self._lang]
        msg = QMessageBox(self)
        msg.setWindowTitle(t["about_title"])
        msg.setTextFormat(Qt.RichText)
        msg.setText(t["about_text"])
        msg.setStyleSheet("QLabel { color: #CDD6F4; min-width: 350px; font-size: 14px; } QMessageBox { background-color: #1E1E2E; } QPushButton { background-color: #313244; color: #CDD6F4; border-radius: 4px; padding: 6px 12px; } QPushButton:hover { background-color: #45475A; }")
        msg.exec()

    def open_history(self):
        HistoryDialog(self.db, lang=self._lang, parent=self).exec()
