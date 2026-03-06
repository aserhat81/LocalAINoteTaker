import sys
import locale
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QComboBox, QTextEdit,
                               QGroupBox, QStatusBar, QMessageBox,
                               QDialog, QListWidget, QSplitter, QProgressBar,
                               QTabWidget, QToolBar, QFontComboBox, QSpinBox,
                               QColorDialog, QLineEdit, QFrame, QCheckBox,
                               QSizePolicy, QDateEdit)
from PySide6.QtCore import Qt, QRegularExpression, QDate
from PySide6.QtGui import (QTextCursor, QTextCharFormat, QFont, QColor,
                           QTextDocument, QKeySequence, QAction, QIcon)

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
        "analyzing": "--- Toplantı Bitti. {model} ile Analiz Ediliyor... ---",
        "analyzing_status": "Toplantı özetleniyor, AI çalışıyor...",
        "saved_status": "Kayıt veritabanına eklendi.",
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
        # Rich text editor
        "rte_color": "🎨 Renk",
        "rte_find": "🔍 Bul & Değiştir",
        "rte_find_label": "Bul:",
        "rte_find_ph": "Aranacak metin...",
        "rte_replace_label": "Değiştir:",
        "rte_replace_ph": "Yeni metin...",
        "rte_case": "Büyük/Küçük",
        "rte_next": "▶ İleri",
        "rte_prev": "◀ Geri",
        "rte_replace_one": "Değiştir",
        "rte_replace_all": "Tümünü Değiştir",
        "rte_found": "✓ Bulundu",
        "rte_not_found": "✗ Bulunamadı",
        "rte_replaced": "✓ {} adet değiştirildi",
        "rte_color_dlg": "Metin Rengi Seç",
        # History dialog
        "btn_save": "💾 Kaydet",
        "saved_ok": "✓ Kaydedildi",
        "unsaved_title": "Kaydedilmemiş Değişiklikler",
        "unsaved_switch": "Mevcut toplantıda kaydedilmemiş değişiklikler var.\nYine de geçmek istiyor musunuz?",
        "unsaved_close": "Kaydedilmemiş değişiklikler var. Çıkmak istediğinize emin misiniz?",
        "tab_summary": "📋 Özet",
        "tab_transcript": "📝 Transkript",
        "btn_reanalyze": "🤖 Yeniden Özetle",
        "reanalyzing": "⏳ Analiz ediliyor...",
        "reanalyze_done": "✓ Yeni özet oluşturuldu ve kaydedildi",
        "reanalyze_err": "❌ Analiz hatası:",
        "no_transcript": "Transkript bulunamadı.",
        "filter_btn": "🔍 Filtrele",
        "filter_all": "Tarih: Tümü",
        "participants_label": "Katılımcılar:",
        "search_placeholder": "Toplantılarda ara (örn: genesys)...",
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
        "analyzing": "--- Meeting Ended. Analyzing with {model}... ---",
        "analyzing_status": "Summarizing meeting, AI is working...",
        "saved_status": "Meeting saved to database.",
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
        # Rich text editor
        "rte_color": "🎨 Color",
        "rte_find": "🔍 Find & Replace",
        "rte_find_label": "Find:",
        "rte_find_ph": "Search text...",
        "rte_replace_label": "Replace:",
        "rte_replace_ph": "New text...",
        "rte_case": "Match Case",
        "rte_next": "▶ Next",
        "rte_prev": "◀ Prev",
        "rte_replace_one": "Replace",
        "rte_replace_all": "Replace All",
        "rte_found": "✓ Found",
        "rte_not_found": "✗ Not found",
        "rte_replaced": "✓ {} replaced",
        "rte_color_dlg": "Select Text Color",
        # History dialog
        "btn_save": "💾 Save",
        "saved_ok": "✓ Saved",
        "unsaved_title": "Unsaved Changes",
        "unsaved_switch": "There are unsaved changes in the current meeting.\nDo you want to switch anyway?",
        "unsaved_close": "There are unsaved changes. Are you sure you want to close?",
        "tab_summary": "📋 Summary",
        "tab_transcript": "📝 Transcript",
        "btn_reanalyze": "🤖 Re-analyze",
        "reanalyzing": "⏳ Analyzing...",
        "reanalyze_done": "✓ New summary generated and saved",
        "reanalyze_err": "❌ Analysis error:",
        "no_transcript": "No transcript found.",
        "filter_btn": "🔍 Filter",
        "filter_all": "Date: All",
        "participants_label": "Participants:",
        "search_placeholder": "Search in meetings...",
    }
}

def detect_os_lang():
    """İşletim sistemi dilini tespit et, TR veya EN döndür."""
    try:
        lang = locale.getdefaultlocale()[0] or ""
        return "tr" if lang.lower().startswith("tr") else "en"
    except Exception:
        return "en"


# ─── Rich Text Editor Toolbar ────────────────────────────────────────────────

class RichTextEditor(QWidget):
    """Toolbar + QTextEdit birleşimi rich text editör bileşeni."""
    def __init__(self, lang="tr", parent=None):
        super().__init__(parent)
        self._lang = lang
        t = I18N[lang]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # ── Toolbar ──
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("background-color: #181825; border-bottom: 1px solid #313244;")
        tb_layout = QHBoxLayout(toolbar_widget)
        tb_layout.setContentsMargins(6, 4, 6, 4)
        tb_layout.setSpacing(4)

        # Bold
        self.btn_bold = QPushButton("B")
        self.btn_bold.setCheckable(True)
        self.btn_bold.setFixedSize(28, 26)
        self.btn_bold.setStyleSheet(
            "QPushButton { font-weight: bold; background: #313244; color: #CDD6F4;"
            " border-radius: 4px; }"
            "QPushButton:checked { background: #89B4FA; color: #11111B; }"
            "QPushButton:hover { background: #45475A; }"
        )
        self.btn_bold.clicked.connect(self.toggle_bold)
        tb_layout.addWidget(self.btn_bold)

        # Italic
        self.btn_italic = QPushButton("I")
        self.btn_italic.setCheckable(True)
        self.btn_italic.setFixedSize(28, 26)
        self.btn_italic.setStyleSheet(
            "QPushButton { font-style: italic; background: #313244; color: #CDD6F4;"
            " border-radius: 4px; }"
            "QPushButton:checked { background: #89B4FA; color: #11111B; }"
            "QPushButton:hover { background: #45475A; }"
        )
        self.btn_italic.clicked.connect(self.toggle_italic)
        tb_layout.addWidget(self.btn_italic)

        # Underline
        self.btn_underline = QPushButton("U")
        self.btn_underline.setCheckable(True)
        self.btn_underline.setFixedSize(28, 26)
        self.btn_underline.setStyleSheet(
            "QPushButton { text-decoration: underline; background: #313244; color: #CDD6F4;"
            " border-radius: 4px; }"
            "QPushButton:checked { background: #89B4FA; color: #11111B; }"
            "QPushButton:hover { background: #45475A; }"
        )
        self.btn_underline.clicked.connect(self.toggle_underline)
        tb_layout.addWidget(self.btn_underline)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #45475A;")
        tb_layout.addWidget(sep1)

        # Font Size
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 48)
        self.font_size.setValue(12)
        self.font_size.setFixedWidth(56)
        self.font_size.setStyleSheet(
            "QSpinBox { background: #313244; color: #CDD6F4; border: 1px solid #45475A;"
            " border-radius: 4px; padding: 2px; }"
        )
        self.font_size.valueChanged.connect(self.change_font_size)
        tb_layout.addWidget(QLabel("Pt:"))
        tb_layout.addWidget(self.font_size)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: #45475A;")
        tb_layout.addWidget(sep2)

        # Text Color
        self.btn_color = QPushButton(t["rte_color"])
        self.btn_color.setFixedHeight(26)
        self.btn_color.setStyleSheet(
            "QPushButton { background: #313244; color: #CDD6F4; border-radius: 4px; padding: 0 6px; }"
            "QPushButton:hover { background: #45475A; }"
        )
        self.btn_color.clicked.connect(self.change_text_color)
        tb_layout.addWidget(self.btn_color)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.VLine)
        sep3.setStyleSheet("color: #45475A;")
        tb_layout.addWidget(sep3)

        # Find & Replace toggle
        self.btn_find_replace = QPushButton(t["rte_find"])
        self.btn_find_replace.setFixedHeight(26)
        self.btn_find_replace.setStyleSheet(
            "QPushButton { background: #313244; color: #CDD6F4; border-radius: 4px; padding: 0 6px; }"
            "QPushButton:hover { background: #F9E2AF; color: #11111B; }"
        )
        self.btn_find_replace.setToolTip("Ctrl+H")
        self.btn_find_replace.clicked.connect(self.toggle_find_replace)
        tb_layout.addWidget(self.btn_find_replace)

        tb_layout.addStretch()
        layout.addWidget(toolbar_widget)

        # ── Find & Replace Panel ──
        self.find_panel = QWidget()
        self.find_panel.setStyleSheet("background-color: #181825; border-bottom: 1px solid #313244;")
        fp_layout = QHBoxLayout(self.find_panel)
        fp_layout.setContentsMargins(8, 6, 8, 6)
        fp_layout.setSpacing(6)

        fp_layout.addWidget(QLabel(t["rte_find_label"]))
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText(t["rte_find_ph"])
        self.find_input.setFixedWidth(180)
        self.find_input.setStyleSheet(
            "QLineEdit { background: #313244; color: #CDD6F4; border: 1px solid #45475A;"
            " border-radius: 4px; padding: 4px 8px; }"
        )
        self.find_input.returnPressed.connect(self.find_next)
        fp_layout.addWidget(self.find_input)

        fp_layout.addWidget(QLabel(t["rte_replace_label"]))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText(t["rte_replace_ph"])
        self.replace_input.setFixedWidth(180)
        self.replace_input.setStyleSheet(
            "QLineEdit { background: #313244; color: #CDD6F4; border: 1px solid #45475A;"
            " border-radius: 4px; padding: 4px 8px; }"
        )
        fp_layout.addWidget(self.replace_input)

        self.case_check = QCheckBox(t["rte_case"])
        self.case_check.setStyleSheet("color: #A6ADC8;")
        fp_layout.addWidget(self.case_check)

        btn_find_next = QPushButton(t["rte_next"])
        btn_find_next.setFixedHeight(26)
        btn_find_next.setStyleSheet(
            "QPushButton { background: #313244; color: #CDD6F4; border-radius: 4px; padding: 0 8px; }"
            "QPushButton:hover { background: #45475A; }"
        )
        btn_find_next.clicked.connect(self.find_next)
        fp_layout.addWidget(btn_find_next)

        btn_find_prev = QPushButton(t["rte_prev"])
        btn_find_prev.setFixedHeight(26)
        btn_find_prev.setStyleSheet(
            "QPushButton { background: #313244; color: #CDD6F4; border-radius: 4px; padding: 0 8px; }"
            "QPushButton:hover { background: #45475A; }"
        )
        btn_find_prev.clicked.connect(self.find_prev)
        fp_layout.addWidget(btn_find_prev)

        btn_replace_one = QPushButton(t["rte_replace_one"])
        btn_replace_one.setFixedHeight(26)
        btn_replace_one.setStyleSheet(
            "QPushButton { background: #F9E2AF; color: #11111B; border-radius: 4px; padding: 0 8px; font-weight: bold; }"
            "QPushButton:hover { background: #FAB387; }"
        )
        btn_replace_one.clicked.connect(self.replace_one)
        fp_layout.addWidget(btn_replace_one)

        btn_replace_all = QPushButton(t["rte_replace_all"])
        btn_replace_all.setFixedHeight(26)
        btn_replace_all.setStyleSheet(
            "QPushButton { background: #A6E3A1; color: #11111B; border-radius: 4px; padding: 0 8px; font-weight: bold; }"
            "QPushButton:hover { background: #94E2D5; }"
        )
        btn_replace_all.clicked.connect(self.replace_all)
        fp_layout.addWidget(btn_replace_all)

        self.find_status = QLabel("")
        self.find_status.setStyleSheet("color: #F9E2AF; font-size: 12px;")
        fp_layout.addWidget(self.find_status)
        fp_layout.addStretch()

        btn_close_fp = QPushButton("✕")
        btn_close_fp.setFixedSize(22, 22)
        btn_close_fp.setStyleSheet(
            "QPushButton { background: #F38BA8; color: #11111B; border-radius: 4px; font-weight: bold; }"
        )
        btn_close_fp.clicked.connect(self.toggle_find_replace)
        fp_layout.addWidget(btn_close_fp)

        self.find_panel.hide()
        layout.addWidget(self.find_panel)

        # ── Text Area ──
        self.editor = QTextEdit()
        self.editor.setStyleSheet(
            "QTextEdit { background-color: #11111B; color: #CDD6F4;"
            " border: none; padding: 12px; font-size: 13px; line-height: 1.6; }"
        )
        self.editor.cursorPositionChanged.connect(self._sync_toolbar)
        layout.addWidget(self.editor)

        # Shortcut Ctrl+H
        self._shortcut_find = QAction(self)
        self._shortcut_find.setShortcut(QKeySequence("Ctrl+H"))
        self._shortcut_find.triggered.connect(self.toggle_find_replace)
        self.addAction(self._shortcut_find)

    # ── Formatting helpers ────────────────────────────────────────────────────

    def toggle_bold(self):
        fmt = QTextCharFormat()
        w = QFont.Bold if self.btn_bold.isChecked() else QFont.Normal
        fmt.setFontWeight(w)
        self._apply_format(fmt)

    def toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.btn_italic.isChecked())
        self._apply_format(fmt)

    def toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.btn_underline.isChecked())
        self._apply_format(fmt)

    def change_font_size(self, size):
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self._apply_format(fmt)

    def change_text_color(self):
        color = QColorDialog.getColor(QColor("#CDD6F4"), self, I18N[self._lang]["rte_color_dlg"])
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self._apply_format(fmt)

    def _apply_format(self, fmt):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        else:
            self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def _sync_toolbar(self):
        """İmleç konumuna göre toolbar butonlarını güncelle."""
        fmt = self.editor.currentCharFormat()
        self.btn_bold.blockSignals(True)
        self.btn_italic.blockSignals(True)
        self.btn_underline.blockSignals(True)
        self.btn_bold.setChecked(fmt.fontWeight() == QFont.Bold)
        self.btn_italic.setChecked(fmt.fontItalic())
        self.btn_underline.setChecked(fmt.fontUnderline())
        self.btn_bold.blockSignals(False)
        self.btn_italic.blockSignals(False)
        self.btn_underline.blockSignals(False)
        if fmt.fontPointSize() > 0:
            self.font_size.blockSignals(True)
            self.font_size.setValue(int(fmt.fontPointSize()))
            self.font_size.blockSignals(False)

    # ── Find & Replace ────────────────────────────────────────────────────────

    def toggle_find_replace(self):
        visible = self.find_panel.isVisible()
        self.find_panel.setVisible(not visible)
        if not visible:
            self.find_input.setFocus()
            self.find_input.selectAll()

    def _get_flags(self):
        flags = QTextDocument.FindFlags()
        if self.case_check.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        return flags

    def find_next(self):
        text = self.find_input.text()
        if not text:
            return
        found = self.editor.find(text, self._get_flags())
        if not found:
            # Başa sar
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.editor.setTextCursor(cursor)
            found = self.editor.find(text, self._get_flags())
        t = I18N[self._lang]
        self.find_status.setText(t["rte_found"] if found else t["rte_not_found"])

    def find_prev(self):
        text = self.find_input.text()
        if not text:
            return
        flags = self._get_flags() | QTextDocument.FindBackward
        found = self.editor.find(text, flags)
        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.editor.setTextCursor(cursor)
            found = self.editor.find(text, flags)
        t = I18N[self._lang]
        self.find_status.setText(t["rte_found"] if found else t["rte_not_found"])

    def replace_one(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText().lower() == self.find_input.text().lower():
            cursor.insertText(self.replace_input.text())
        self.find_next()

    def replace_all(self):
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        if not find_text:
            return
        doc = self.editor.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        count = 0
        flags = self._get_flags()
        while True:
            found_cursor = doc.find(find_text, cursor, flags)
            if found_cursor.isNull():
                break
            found_cursor.insertText(replace_text)
            cursor = found_cursor
            count += 1
        cursor.endEditBlock()
        t = I18N[self._lang]
        self.find_status.setText(t["rte_replaced"].format(count) if count else t["rte_not_found"])

    # ── Public helpers ────────────────────────────────────────────────────────

    def set_plain_text(self, text):
        self.editor.setPlainText(text)

    def to_plain_text(self):
        return self.editor.toPlainText()

    def set_readonly(self, val):
        self.editor.setReadOnly(val)

    def is_modified(self):
        return self.editor.document().isModified()

    def set_modified(self, val):
        self.editor.document().setModified(val)


# ─── History Dialog ───────────────────────────────────────────────────────────

class HistoryDialog(QDialog):
    def __init__(self, db, lang="tr", parent=None):
        super().__init__(parent)
        self.db = db
        self.lang = lang
        t = I18N[lang]
        self.setWindowTitle(t["history_title"])
        self.setMinimumSize(1000, 620)
        self.current_meeting_id = None
        self.current_title = ""
        self._llm_thread = None  # Re-analyze için

        self.setStyleSheet("""
            QDialog { background-color: #1E1E2E; color: #CDD6F4; }
            QLabel { color: #CDD6F4; }
            QListWidget {
                background-color: #11111B; color: #A6E3A1;
                border: 1px solid #313244; padding: 5px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #313244; color: #CBA6F7;
            }
            QListWidget::item:hover { background-color: #1E1E2E; }
            QTabWidget::pane { border: 1px solid #313244; border-radius: 0 0 6px 6px; }
            QTabBar::tab {
                background: #181825; color: #A6ADC8;
                padding: 6px 18px; border-radius: 4px 4px 0 0;
                margin-right: 2px;
            }
            QTabBar::tab:selected { background: #313244; color: #CDD6F4; }
            QTabBar::tab:hover { background: #45475A; }
            QPushButton {
                background-color: #313244; color: #CDD6F4;
                padding: 7px 14px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45475A; }
            QPushButton:disabled { background-color: #181825; color: #585B70; }
            QLabel#meeting_title_label { font-size: 16px; color: #CBA6F7; font-weight: bold; }
        """)

        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        splitter = QSplitter(Qt.Horizontal)

        # ── Sol panel: toplantı listesi ──
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        list_header = QLabel(t["history_list_label"])
        list_header.setStyleSheet("font-weight: bold; color: #89B4FA; font-size: 13px;")
        left_layout.addWidget(list_header)

        # Filtre paneli (Arama + Tarih)
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(6)
        
        # Arama kutusu
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(t["search_placeholder"])
        self.search_box.setStyleSheet("background-color: #181825; color: #CDD6F4; border: 1px solid #45475A; border-radius: 4px; padding: 6px;")
        self.search_box.returnPressed.connect(self.load_meetings)
        filter_layout.addWidget(self.search_box)
        
        # Tarih filtresi (Varsayılan olarak son 5 gün görünür ve etkindir)
        dates_layout = QHBoxLayout()
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-5))
        self.date_from.setStyleSheet("background-color: #181825; color: #CDD6F4; border: 1px solid #45475A;")
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setStyleSheet("background-color: #181825; color: #CDD6F4; border: 1px solid #45475A;")
        
        dates_layout.addWidget(self.date_from)
        dates_layout.addWidget(self.date_to)

        self.btn_filter = QPushButton(t["filter_btn"])
        self.btn_filter.setStyleSheet("background-color: #313244; color: #CDD6F4; padding: 4px; border-radius: 4px;")
        self.btn_filter.clicked.connect(self.load_meetings)
        
        filter_layout.addLayout(dates_layout)
        filter_layout.addWidget(self.btn_filter)
        left_layout.addLayout(filter_layout)

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_meeting_selected)
        left_layout.addWidget(self.list_widget)

        # ── Sağ panel: sekme editörleri ──
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.detail_title_label = QLabel(t["history_detail_label"])
        self.detail_title_label.setObjectName("meeting_title_label")
        right_layout.addWidget(self.detail_title_label)
        
        # Katılımcılar kutusu
        part_layout = QHBoxLayout()
        part_label = QLabel(t["participants_label"])
        part_label.setStyleSheet("color: #BAC2DE; font-size: 13px;")
        self.participants_edit = QLineEdit()
        self.participants_edit.setStyleSheet("background-color: #181825; color: #CDD6F4; border: 1px solid #45475A; border-radius: 4px; padding: 4px;")
        part_layout.addWidget(part_label)
        part_layout.addWidget(self.participants_edit)
        right_layout.addLayout(part_layout)

        self.tabs = QTabWidget()

        # Özet sekmesi
        self.summary_editor = RichTextEditor(lang=lang)
        self.summary_editor.set_readonly(False)
        self.tabs.addTab(self.summary_editor, t["tab_summary"])

        # Transkript sekmesi
        self.transcript_editor = RichTextEditor(lang=lang)
        self.transcript_editor.set_readonly(False)
        self.tabs.addTab(self.transcript_editor, t["tab_transcript"])

        right_layout.addWidget(self.tabs)

        # Butonlar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.save_indicator = QLabel("")
        self.save_indicator.setStyleSheet("color: #A6E3A1; font-size: 12px;")
        btn_bar.addWidget(self.save_indicator)
        btn_bar.addStretch()

        self.btn_reanalyze = QPushButton(t["btn_reanalyze"])
        self.btn_reanalyze.setStyleSheet(
            "QPushButton { background-color: #CBA6F7; color: #11111B; padding: 7px 16px;"
            " border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #F5C2E7; }"
            "QPushButton:disabled { background-color: #181825; color: #585B70; }"
        )
        self.btn_reanalyze.setEnabled(False)
        self.btn_reanalyze.clicked.connect(self.reanalyze_current)
        btn_bar.addWidget(self.btn_reanalyze)

        self.btn_save = QPushButton(t["btn_save"])
        self.btn_save.setStyleSheet(
            "QPushButton { background-color: #A6E3A1; color: #11111B; padding: 7px 16px;"
            " border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #94E2D5; }"
            "QPushButton:disabled { background-color: #181825; color: #585B70; }"
        )
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_current)
        btn_bar.addWidget(self.btn_save)

        self.btn_email = QPushButton(t["btn_send_email"])
        self.btn_email.setStyleSheet(
            "QPushButton { background-color: #89B4FA; color: #11111B; padding: 7px 16px;"
            " border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #B4BEFE; }"
            "QPushButton:disabled { background-color: #181825; color: #585B70; }"
        )
        self.btn_email.setEnabled(False)
        self.btn_email.clicked.connect(self.send_current_email)
        btn_bar.addWidget(self.btn_email)

        right_layout.addLayout(btn_bar)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([240, 760])
        layout.addWidget(splitter)

        self.load_meetings()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def load_meetings(self):
        self.list_widget.clear()
        
        start_date = self.date_from.date().toString("yyyy-MM-dd")
        end_date = self.date_to.date().toString("yyyy-MM-dd")
            
        search_term = self.search_box.text().strip()
        if not search_term:
            search_term = None
            
        for rec in self.db.get_recent_meetings(start_date=start_date, end_date=end_date, search_term=search_term):
            title = rec[1]
            if not title:
                title = "Genel Toplantı Özeti" if self.lang == "tr" else "General Meeting Summary"
            self.list_widget.addItem(f"{rec[2][:16]}\n{title}")
            self.list_widget.item(self.list_widget.count() - 1).setData(Qt.UserRole, rec[0])

    def on_meeting_selected(self):
        items = self.list_widget.selectedItems()
        if not items:
            return
        # Kaydedilmemiş değişiklik uyarısı
        if self._has_unsaved_changes():
            t2 = I18N[self.lang]
            reply = QMessageBox.question(
                self, t2["unsaved_title"], t2["unsaved_switch"],
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        self.current_meeting_id = items[0].data(Qt.UserRole)
        record = self.db.get_meeting_by_id(self.current_meeting_id)
        if record:
            self.current_title = record[0]
            self.detail_title_label.setText(f"🗓 {record[0]}  ·  {record[1]}")
            self.participants_edit.setText(record[4] or "")
            self.summary_editor.set_plain_text(record[3] or "")
            self.transcript_editor.set_plain_text(record[2] or "")
            self.summary_editor.set_modified(False)
            self.transcript_editor.set_modified(False)
            self.btn_save.setEnabled(True)
            self.btn_email.setEnabled(True)
            self.btn_reanalyze.setEnabled(True)
            self.save_indicator.setText("")

    def _has_unsaved_changes(self):
        return (self.summary_editor.is_modified() or
                self.transcript_editor.is_modified())

    def save_current(self):
        if self.current_meeting_id is None:
            return
        self.db.update_meeting(
            self.current_meeting_id,
            transcript=self.transcript_editor.to_plain_text(),
            summary=self.summary_editor.to_plain_text(),
            participants=self.participants_edit.text()
        )
        self.summary_editor.set_modified(False)
        self.transcript_editor.set_modified(False)
        self.save_indicator.setText(I18N[self.lang]["saved_ok"])
        self.load_meetings()

    def reanalyze_current(self):
        """Transkripti al, yeni LLM'e gönder, dönen özeti kaydet."""
        if self.current_meeting_id is None:
            return
        transcript = self.transcript_editor.to_plain_text().strip()
        if not transcript:
            self.save_indicator.setText(I18N[self.lang]["no_transcript"])
            return
        t2 = I18N[self.lang]
        # Butonları devre dışı bırak
        self.btn_reanalyze.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_reanalyze.setText(t2["reanalyzing"])
        self.save_indicator.setText(t2["reanalyzing"])
        # LLM thread'ı başlat
        self._llm_thread = LlmAnalyzerThread(transcript, language=self.lang)
        self._llm_thread.analysis_ready.connect(self._on_reanalyze_done)
        self._llm_thread.analysis_error.connect(self._on_reanalyze_error)
        self._llm_thread.analysis_progress.connect(self._on_reanalyze_progress)
        self._llm_thread.start()

    def _on_reanalyze_progress(self, message):
        self.save_indicator.setText(f"ℹ️ {message}")

    def _on_reanalyze_done(self, title, participants, summary):
        t2 = I18N[self.lang]
        # Özet editorünü güncelle
        self.summary_editor.set_plain_text(summary)
        self.summary_editor.set_modified(False)
        self.participants_edit.setText(participants)
        # Veritabanına kaydet
        self.db.update_meeting(
            self.current_meeting_id,
            title=title,
            summary=summary,
            participants=participants
        )
        # Başlığı güncelle
        self.current_title = title
        self.detail_title_label.setText(f"🗓 {title}")
        self.save_indicator.setText(t2["reanalyze_done"])
        self.btn_reanalyze.setText(t2["btn_reanalyze"])
        self.btn_reanalyze.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.load_meetings()

    def _on_reanalyze_error(self, err_msg):
        t2 = I18N[self.lang]
        self.save_indicator.setText(f"{t2['reanalyze_err']} {err_msg}")
        self.save_indicator.setStyleSheet("color: #F38BA8; font-size: 12px;")
        self.btn_reanalyze.setText(t2["btn_reanalyze"])
        self.btn_reanalyze.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.load_meetings()

    def send_current_email(self):
        t = I18N[self.lang]
        send_email_mailto(
            f"{t['email_subject']}{self.current_title}",
            self.summary_editor.to_plain_text()
        )

    def closeEvent(self, event):
        if self._has_unsaved_changes():
            t2 = I18N[self.lang]
            reply = QMessageBox.question(
                self, t2["unsaved_title"], t2["unsaved_close"],
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        event.accept()


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
        self.audio_manager.stop_recording()
        self.btn_start_record.setText(self.t("btn_new_rec"))
        self.btn_start_record.setStyleSheet("background-color: #89B4FA; color: #11111B;")
        self.mode_combo.setEnabled(True)
        self.mic_combo.setEnabled(True)
        self.btn_finish_meeting.setEnabled(False)

        self.meeting_active = False
        self._finishing = True  # LLM analizini beklemeye al

        # Event loop'taki son ses paketlerinin ulaşabilmesi için ufak bir bekleme
        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, self._check_asr_and_start_llm)

    def _check_asr_and_start_llm(self):
        # Hala işlenmesi beklenen veya devam eden Whisper (ASR) süreci var mı?
        if getattr(self, '_finishing', False):
            if self.asr_queue or self.asr_threads:
                # Hala devam ediyor, bitince yeniden tetiklenecek
                self.statusBar_widget.showMessage(self.t("analyzing_status") + " (Son transkriptler işleniyor...)")
                return
            
            # Kuyruk bitti, LLM'i başlat!
            self._finishing = False
            color_warn = "#F9E2AF"
            analyzing_msg = self.t('analyzing').format(model=LlmAnalyzerThread.MODEL_NAME)
            self.subtitle_box.append(f"<br><span style='color: {color_warn};'><b>{analyzing_msg}</b></span><br>")
            self.statusBar_widget.showMessage(self.t("analyzing_status"))

            lang = "tr" if self.lang_combo.currentIndex() == 0 else "en"
            self.llm_thread = LlmAnalyzerThread(self.full_transcript_buffer, language=lang)
            self.llm_thread.analysis_ready.connect(self.on_analysis_completed)
            self.llm_thread.analysis_error.connect(self.on_analysis_error)
            self.llm_thread.analysis_progress.connect(self.on_analysis_progress)
            self.llm_thread.start()

    def on_analysis_progress(self, message):
        self.statusBar_widget.showMessage(message)
        # Sadece son eklenen "Analiz ediliyor" satırını silmeden bir alt satıra progres eklemektense,
        # kısa süreli bir mesaj olarak status bar'da kalması daha temizdir.

    def on_analysis_completed(self, title, participants, summary):
        self.db.save_meeting(title, self.full_transcript_buffer, summary, participants=participants)
        disp_html = f"<br><b><span style='color: #A6E3A1; font-size:16px;'>{title}</span></b><br><span style='color: #F5C2E7; font-size:13px;'>Katılımcılar: {participants}</span><br><span style='color: #CDD6F4;'>{summary}</span>"
        self.subtitle_box.append(disp_html.replace('\n', '<br>'))
        self.statusBar_widget.showMessage(self.t("saved_status"))

    def on_analysis_error(self, err_msg):
        self.statusBar_widget.showMessage(err_msg)
        self.subtitle_box.append(f"<br><b style='color:#F38BA8;'>{self.t('analysis_failed')}</b> {err_msg}")
        
        # Hata olsa bile LLM'den dönmediği için kaybolmasın diye sadece transkripti kaydet
        fallback_title = "Analiz Edilemeyen Toplantı" if self._lang == "tr" else "Unanalyzed Meeting"
        fallback_summary = f"Analiz Hatası: {err_msg}" if self._lang == "tr" else f"Analysis Error: {err_msg}"
        self.db.save_meeting(fallback_title, self.full_transcript_buffer, fallback_summary, participants="")
        self.statusBar_widget.showMessage(self.t("saved_status"))

    # ─── ASR ─────────────────────────────────────────────────────────────────

    # ─── ASR ─────────────────────────────────────────────────────────────────

    def on_audio_chunk_ready(self, wav_bytes, source_label):
        # Toplantı bitip analiz de başladıktan sonra gelen çok geçikmiş paketleri yoksay
        if not self.meeting_active and not getattr(self, '_finishing', False):
            return
        # Paketleri sıraya al (Queue)
        self.asr_queue.append((wav_bytes, source_label))
        self._process_asr_queue()

    def _process_asr_queue(self):
        # NPU'da tek Whisper işlemi daha verimli; 2 paralel iş NPU'yu bölerek ikisini de yavaşlatır
        MAX_CONCURRENT = 1
        
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

        # Eğer finish aşamasındaysak ve liste kalmadıysa LLM'yi tetikle
        if getattr(self, '_finishing', False):
            self._check_asr_and_start_llm()

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
