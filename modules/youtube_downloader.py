import re
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class YouTubeDownloadWorker(QThread):
    log = Signal(str)
    progress = Signal(int)
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, urls, output_dir, audio_only=False, playlist=False, parent=None):
        super().__init__(parent)
        self.urls = urls
        self.output_dir = Path(output_dir)
        self.audio_only = audio_only
        self.playlist = playlist
        self.current_process = None
        self.cancelled = False
        self.root_dir = Path(__file__).resolve().parents[1]

    def cancel(self):
        self.cancelled = True
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
            except Exception:
                try:
                    self.current_process.kill()
                except Exception:
                    pass

    def run(self):
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            yt_dlp = self._find_tool("yt-dlp.exe", "yt-dlp")
            ffmpeg = self._find_tool("ffmpeg.exe", "ffmpeg")
            total = max(1, len(self.urls))
            for index, url in enumerate(self.urls, start=1):
                if self.cancelled:
                    raise RuntimeError("Download cancelled.")
                self.log.emit(f"Starting {index}/{total}: {url}")
                self._run_download(yt_dlp, ffmpeg, url, index, total)
            self.progress.emit(100)
            self.finished_ok.emit()
        except Exception as exc:
            self.failed.emit(str(exc))

    def _run_download(self, yt_dlp, ffmpeg, url, index, total):
        template = str(self.output_dir / "%(autonumber)03d - %(title).180B.%(ext)s")
        cmd = [yt_dlp, "--newline", "--ffmpeg-location", str(Path(ffmpeg).parent)]
        cmd.append("--yes-playlist" if self.playlist else "--no-playlist")
        if self.audio_only:
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            cmd += [
                "-f",
                "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
                "--merge-output-format",
                "mp4",
            ]
        cmd += ["-o", template, url]
        self.log.emit("Running: " + " ".join(str(part) for part in cmd))

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.current_process = proc
        lines = []
        try:
            for raw_line in proc.stdout:
                if self.cancelled:
                    raise RuntimeError("Download cancelled.")
                line = raw_line.strip()
                if not line:
                    continue
                lines.append(line)
                self.log.emit(line)
                percent = parse_download_percent(line)
                if percent is not None:
                    overall = int(((index - 1) * 100 + percent) / total)
                    self.progress.emit(max(0, min(100, overall)))
            proc.wait()
        finally:
            self.current_process = None
        if proc.returncode != 0:
            summary = "\n".join(lines[-8:]) or f"yt-dlp failed with exit code {proc.returncode}"
            raise RuntimeError(summary)

    def _find_tool(self, bundled_name, path_name):
        bundled = self.root_dir / "tools" / bundled_name
        if bundled.exists():
            return str(bundled)
        found = shutil.which(path_name)
        if found:
            return found
        raise RuntimeError(f"{path_name} not found. Put {bundled_name} in tools/ or add it to PATH.")


class YouTubeDownloaderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_output = Path(__file__).resolve().parents[1] / "downloads"
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("YouTube Downloader")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89B4FA;")
        subtitle = QLabel("Tek video, playlist veya cok satirli URL listesini video ya da MP3 olarak indir.")
        subtitle.setStyleSheet("color: #A6ADC8; font-size: 13px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        input_group = QGroupBox("Download")
        input_layout = QVBoxLayout(input_group)
        self.url_box = QTextEdit()
        self.url_box.setPlaceholderText("YouTube video veya playlist URL'si. Birden fazla URL icin her satira bir tane yaz.")
        self.url_box.setMaximumHeight(110)
        input_layout.addWidget(self.url_box)

        output_row = QHBoxLayout()
        self.output_input = QLineEdit(str(self.default_output))
        self.btn_browse = QPushButton("Browse")
        self.btn_browse.clicked.connect(self.choose_output_folder)
        output_row.addWidget(QLabel("Output"))
        output_row.addWidget(self.output_input, 1)
        output_row.addWidget(self.btn_browse)
        input_layout.addLayout(output_row)

        options_row = QHBoxLayout()
        self.audio_only_check = QCheckBox("Sadece MP3 indir")
        self.playlist_check = QCheckBox("Playlist/list varsa tamamini indir")
        options_row.addWidget(self.audio_only_check)
        options_row.addWidget(self.playlist_check)
        options_row.addStretch()
        input_layout.addLayout(options_row)

        button_row = QHBoxLayout()
        self.btn_start = QPushButton("Download")
        self.btn_start.setStyleSheet("background-color: #A6E3A1; color: #11111B; font-weight: bold;")
        self.btn_start.clicked.connect(self.start_download)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("background-color: #F38BA8; color: #11111B; font-weight: bold;")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_download)
        button_row.addWidget(self.btn_start)
        button_row.addWidget(self.btn_cancel)
        button_row.addStretch()
        input_layout.addLayout(button_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        input_layout.addWidget(self.progress)
        layout.addWidget(input_group)

        logs_group = QGroupBox("Logs")
        logs_layout = QVBoxLayout(logs_group)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        logs_layout.addWidget(self.log_box)
        layout.addWidget(logs_group, 1)

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Output folder", self.output_input.text())
        if folder:
            self.output_input.setText(folder)

    def start_download(self):
        if self.worker and self.worker.isRunning():
            return
        urls = [line.strip() for line in self.url_box.toPlainText().splitlines() if line.strip()]
        if not urls:
            self.append_log("ERROR: En az bir YouTube URL gir.")
            return
        self.progress.setValue(0)
        self.set_controls_enabled(False)
        self.worker = YouTubeDownloadWorker(
            urls,
            self.output_input.text().strip() or str(self.default_output),
            audio_only=self.audio_only_check.isChecked(),
            playlist=self.playlist_check.isChecked(),
            parent=self,
        )
        self.worker.log.connect(self.append_log)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished_ok.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def cancel_download(self):
        if self.worker and self.worker.isRunning():
            self.append_log("Cancelling download...")
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)

    def set_controls_enabled(self, enabled):
        for widget in [self.url_box, self.output_input, self.btn_browse, self.audio_only_check, self.playlist_check, self.btn_start]:
            widget.setEnabled(enabled)
        self.btn_cancel.setEnabled(not enabled)

    def append_log(self, message):
        self.log_box.append(str(message).replace("\n", "<br>"))
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def on_finished(self):
        self.append_log("DONE: Download completed.")
        self.progress.setValue(100)
        self.set_controls_enabled(True)

    def on_failed(self, message):
        if "cancelled" in message.lower():
            self.append_log("Cancelled.")
        else:
            self.append_log(f"ERROR: {message}")
        self.set_controls_enabled(True)


def parse_download_percent(line):
    match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line or "")
    return float(match.group(1)) if match else None
