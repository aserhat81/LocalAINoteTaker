import json
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.shorts_pipeline import (
    STEP_AUDIO,
    STEP_BROWSER,
    STEP_CLEAN,
    STEP_METADATA,
    STEP_RENDER,
    STEP_SUBTITLES,
    STEP_TRANSCRIPT,
    STEP_VIDEO,
    ShortsPipeline,
    apply_chatgpt_studio_response,
    build_chatgpt_studio_prompt,
)
from services.chatgpt_browser_bridge import ChatGptBrowserBridge


STEP_LABELS = {
    STEP_VIDEO: "Video indir",
    STEP_AUDIO: "Sadece ses indir",
    STEP_TRANSCRIPT: "Altyazi / transcript indir",
    STEP_CLEAN: "Transcript temizle",
    STEP_BROWSER: "ChatGPT prompt hazirla / sonucu uygula",
    STEP_RENDER: "Secilen shorts'lari render et",
    STEP_SUBTITLES: "Sari altyazi gom",
    STEP_METADATA: "Metadata TXT uret",
}

REQUIRES = {
    STEP_CLEAN: [STEP_TRANSCRIPT],
    STEP_BROWSER: [STEP_TRANSCRIPT, STEP_CLEAN],
    STEP_RENDER: [STEP_VIDEO, STEP_TRANSCRIPT, STEP_CLEAN, STEP_BROWSER],
    STEP_SUBTITLES: [STEP_RENDER],
    STEP_METADATA: [STEP_BROWSER],
}

POST_BROWSER_STEPS = {STEP_RENDER, STEP_SUBTITLES, STEP_METADATA}

STATUS_ICON = {
    "idle": "○",
    "queued": "…",
    "running": "●",
    "success": "✓",
    "warning": "!",
    "error": "!",
    "cancelled": "x",
    "skipped": "-",
}


class ShortsWorker(QThread):
    log = Signal(str)
    step_status = Signal(str, str, str)
    step_progress = Signal(str, int, str)
    candidates_ready = Signal(list, str)
    project_ready = Signal(str)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, request, model_session_manager=None, parent=None):
        super().__init__(parent)
        self.request = request
        self.model_session_manager = model_session_manager
        self.pipeline = None

    def cancel(self):
        if self.pipeline:
            self.pipeline.cancel()

    def run(self):
        try:
            self.pipeline = ShortsPipeline(
                url=self.request["url"],
                output_root=self.request["output_root"],
                shorts_count=self.request["shorts_count"],
                max_duration=self.request["max_duration"],
                model_name=self.request["model_name"],
                selected_steps=self.request["selected_steps"],
                selected_clip_nos=self.request["selected_clip_nos"],
                existing_project_dir=self.request.get("existing_project_dir"),
                model_session_manager=self.model_session_manager,
                translate_english_with_local_ai=self.request.get("translate_english_with_local_ai", True),
                log=self.log.emit,
                progress=self.step_progress.emit,
            )
            result = self.pipeline.run(
                step_started=lambda step: self.step_status.emit(step, "running", ""),
                step_finished=lambda step, status, message="": self.step_status.emit(step, status, message),
                candidates_ready=lambda clips, project_dir: self.candidates_ready.emit(clips, project_dir),
                project_ready=self.project_ready.emit,
            )
            self.finished_ok.emit(result["project_dir"])
        except Exception as exc:
            self.failed.emit(str(exc))


class ChatGptBrowserAssistWorker(QThread):
    log = Signal(str)
    login_required = Signal(str)
    finished_ok = Signal(list, int, str)
    parse_failed = Signal(str, str)
    failed = Signal(str)

    def __init__(self, source_dir, analysis_dir, prompt, shorts_count, max_duration, search_ranges="", parent=None):
        super().__init__(parent)
        self.source_dir = Path(source_dir)
        self.analysis_dir = Path(analysis_dir)
        self.prompt = prompt
        self.shorts_count = shorts_count
        self.max_duration = max_duration
        self.search_ranges = search_ranges
        self._login_event = threading.Event()

    def continue_after_login(self):
        self._login_event.set()

    def _request_login(self, message):
        self._login_event.clear()
        self.login_required.emit(message)
        self._login_event.wait()

    def run(self):
        bridge = ChatGptBrowserBridge(log=self.log.emit)
        try:
            self.analysis_dir.mkdir(parents=True, exist_ok=True)
            (self.analysis_dir / "chatgpt_prompt.txt").write_text(self.prompt, encoding="utf-8")
            result = bridge.run_prompt(
                self.prompt,
                expect_json=False,
                on_login_required=self._request_login,
                timeout_seconds=300,
            )
            response_text = (result.get("text") or "").strip()
            (self.analysis_dir / "chatgpt_response.txt").write_text(response_text, encoding="utf-8")
            try:
                parsed, clips = apply_chatgpt_studio_response(
                    self.source_dir,
                    self.analysis_dir,
                    response_text,
                    shorts_count=self.shorts_count,
                    max_duration=self.max_duration,
                    search_ranges=self.search_ranges,
                )
            except Exception as exc:
                (self.analysis_dir / "chatgpt_raw_response.txt").write_text(response_text, encoding="utf-8")
                (self.analysis_dir / "chatgpt_parse_error.txt").write_text(str(exc), encoding="utf-8")
                self.parse_failed.emit(response_text, str(exc))
                return
            self.finished_ok.emit(clips, len(parsed), str(self.analysis_dir))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            bridge.close()


class ShortsStudioWidget(QWidget):
    def __init__(self, model_session_manager=None, default_model="qwen3.5:4b", parent=None):
        super().__init__(parent)
        self.model_session_manager = model_session_manager
        self.default_model = default_model
        self.default_output_root = Path(__file__).resolve().parents[1] / "output"
        self.worker = None
        self.chatgpt_worker = None
        self.current_project_dir = None
        self.current_url = ""
        self.candidates = []
        self.step_checks = {}
        self.step_status_labels = {}
        self.step_progress_bars = {}
        self.step_message_labels = {}
        self._syncing_checks = False
        self.total_selected_steps = 0
        self.completed_steps = set()
        self.current_worker_phase = None
        self.pending_post_browser_request = None

        self._build_ui()
        self._reset_step_statuses()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Shorts Studio")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89B4FA;")
        subtitle = QLabel("YouTube URL'den local AI destekli shorts adaylari ve render workflow'u.")
        subtitle.setStyleSheet("color: #A6ADC8; font-size: 13px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        controls_group = QGroupBox("Input")
        controls = QGridLayout(controls_group)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.textChanged.connect(self.refresh_run_enabled)
        self.output_input = QLineEdit(str(self.default_output_root))
        self.btn_browse = QPushButton("Browse")
        self.btn_browse.clicked.connect(self.choose_output_folder)
        self.count_combo = QComboBox()
        self.count_combo.addItems([str(value) for value in range(1, 11)])
        self.count_combo.setCurrentText("3")
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["60", "90", "180"])
        self.model_input = QLineEdit(self.default_model)
        self.range_enabled_check = QCheckBox("Sadece belirlediğim zaman aralıklarında ara")
        self.range_input = QTextEdit()
        self.range_input.setPlaceholderText("Her satıra bir aralık yaz: 00:00 03:00 veya 17:20-20:00")
        self.range_input.setMaximumHeight(70)

        controls.addWidget(QLabel("YouTube URL"), 0, 0)
        controls.addWidget(self.url_input, 0, 1, 1, 4)
        controls.addWidget(QLabel("Output root"), 1, 0)
        controls.addWidget(self.output_input, 1, 1, 1, 3)
        controls.addWidget(self.btn_browse, 1, 4)
        controls.addWidget(QLabel("Shorts sayisi"), 2, 0)
        controls.addWidget(self.count_combo, 2, 1)
        controls.addWidget(QLabel("Maks sure"), 2, 2)
        controls.addWidget(self.duration_combo, 2, 3)
        controls.addWidget(QLabel("Local model"), 3, 0)
        controls.addWidget(self.model_input, 3, 1, 1, 4)
        controls.addWidget(self.range_enabled_check, 4, 0, 1, 5)
        controls.addWidget(self.range_input, 5, 0, 1, 5)
        layout.addWidget(controls_group)

        steps_group = QGroupBox("Step checklist")
        steps_layout = QGridLayout(steps_group)
        steps_layout.addWidget(QLabel("Step"), 0, 0)
        steps_layout.addWidget(QLabel("Status"), 0, 1)
        steps_layout.addWidget(QLabel("Progress"), 0, 2)
        steps_layout.addWidget(QLabel("Message"), 0, 3)
        for row, step in enumerate(STEP_LABELS):
            row += 1
            check = QCheckBox(STEP_LABELS[step])
            check.stateChanged.connect(lambda _state, step_id=step: self.on_step_changed(step_id))
            check.stateChanged.connect(self.refresh_run_enabled)
            status = QLabel(f"{STATUS_ICON['idle']} idle")
            status.setAlignment(Qt.AlignCenter)
            status.setMinimumWidth(90)
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(0)
            progress.setTextVisible(True)
            message = QLabel("")
            message.setWordWrap(True)
            self.step_checks[step] = check
            self.step_status_labels[step] = status
            self.step_progress_bars[step] = progress
            self.step_message_labels[step] = message
            if step == STEP_BROWSER:
                status.setText(f"{STATUS_ICON['skipped']} skipped")
                message.setText("use panel below")
            steps_layout.addWidget(check, row, 0)
            steps_layout.addWidget(status, row, 1)
            steps_layout.addWidget(progress, row, 2)
            steps_layout.addWidget(message, row, 3)
        layout.addWidget(steps_group)

        self.global_progress = QProgressBar()
        self.global_progress.setRange(0, 100)
        self.global_progress.setValue(0)
        layout.addWidget(self.global_progress)

        button_row = QHBoxLayout()
        self.btn_run = QPushButton("Run Selected Steps")
        self.btn_run.setStyleSheet("background-color: #A6E3A1; color: #11111B; font-weight: bold;")
        self.btn_run.clicked.connect(self.run_selected_steps)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet("background-color: #F38BA8; color: #11111B; font-weight: bold;")
        self.btn_cancel.clicked.connect(self.cancel_job)
        button_row.addWidget(self.btn_run)
        button_row.addWidget(self.btn_cancel)
        button_row.addStretch()
        layout.addLayout(button_row)
        self.refresh_run_enabled()

        browser_group = QGroupBox("ChatGPT Copy / Paste")
        browser_layout = QVBoxLayout(browser_group)
        browser_buttons = QHBoxLayout()
        self.btn_prepare_chatgpt = QPushButton("Prepare ChatGPT Prompt")
        self.btn_prepare_chatgpt.clicked.connect(self.prepare_chatgpt_prompt)
        self.btn_copy_chatgpt = QPushButton("Copy Prompt")
        self.btn_copy_chatgpt.clicked.connect(self.copy_prompt_to_clipboard)
        self.btn_apply_chatgpt = QPushButton("Apply Result & Continue")
        self.btn_apply_chatgpt.clicked.connect(self.apply_chatgpt_result)
        self.btn_analyze_chatgpt_browser = QPushButton("Analyze with ChatGPT Browser Assist")
        self.btn_analyze_chatgpt_browser.clicked.connect(self.analyze_with_chatgpt_browser)
        self.btn_analyze_chatgpt_browser.setEnabled(False)
        browser_buttons.addWidget(self.btn_prepare_chatgpt)
        browser_buttons.addWidget(self.btn_copy_chatgpt)
        browser_buttons.addWidget(self.btn_apply_chatgpt)
        browser_buttons.addWidget(self.btn_analyze_chatgpt_browser)
        browser_buttons.addStretch()
        self.chatgpt_prompt_box = QTextEdit()
        self.chatgpt_prompt_box.setPlaceholderText("ChatGPT prompt will appear here.")
        self.chatgpt_prompt_box.setMaximumHeight(120)
        self.chatgpt_result_box = QTextEdit()
        self.chatgpt_result_box.setPlaceholderText("Paste ChatGPT JSON result here, then click Apply Result & Continue.")
        self.chatgpt_result_box.setMaximumHeight(120)
        browser_layout.addLayout(browser_buttons)
        browser_layout.addWidget(self.chatgpt_prompt_box)
        browser_layout.addWidget(self.chatgpt_result_box)
        layout.addWidget(browser_group)

        candidates_group = QGroupBox("Clip candidates")
        candidates_layout = QVBoxLayout(candidates_group)
        self.candidates_table = QTableWidget(0, 7)
        self.candidates_table.setHorizontalHeaderLabels(["Render", "Start", "End", "Duration", "Score", "Title", "Reason"])
        self.candidates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.candidates_table.verticalHeader().setVisible(False)
        candidates_layout.addWidget(self.candidates_table)
        layout.addWidget(candidates_group, 1)

        logs_group = QGroupBox("Logs")
        logs_layout = QVBoxLayout(logs_group)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        logs_layout.addWidget(self.log_box)
        layout.addWidget(logs_group, 1)

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Output root", self.output_input.text())
        if folder:
            self.output_input.setText(folder)

    def on_step_changed(self, step):
        if self._syncing_checks:
            return
        self._syncing_checks = True
        try:
            check = self.step_checks[step]
            if check.isChecked():
                self._select_requirements(step)
            else:
                self._unselect_dependents(step)
        finally:
            self._syncing_checks = False

    def _select_requirements(self, step):
        for required in REQUIRES.get(step, []):
            self.step_checks[required].setChecked(True)
            self._select_requirements(required)

    def _unselect_dependents(self, step):
        for dependent, requirements in REQUIRES.items():
            if step in requirements and self.step_checks[dependent].isChecked():
                self.step_checks[dependent].setChecked(False)
                self._unselect_dependents(dependent)

    def selected_steps(self):
        return [step for step, check in self.step_checks.items() if check.isChecked()]

    def selected_clip_nos(self):
        selected = []
        for row in range(self.candidates_table.rowCount()):
            item = self.candidates_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                selected.append(int(item.data(Qt.UserRole)))
        return selected

    def set_project_dir(self, project_dir):
        self.current_project_dir = project_dir
        self.refresh_chatgpt_browser_assist_enabled()

    def _source_dir(self):
        if not self.current_project_dir:
            return None
        source = Path(self.current_project_dir) / "source"
        return source if source.exists() else None

    def _analysis_dir(self):
        if not self.current_project_dir:
            return None
        return Path(self.current_project_dir) / "analysis"

    def _transcript_json_path(self):
        source = self._source_dir()
        if not source:
            return None
        english_json = source / "transcript_clean_en.json"
        if english_json.exists():
            return english_json
        clean_json = source / "transcript_clean.json"
        return clean_json if clean_json.exists() else None

    def _build_chatgpt_prompt_from_current_project(self):
        source = self._source_dir()
        transcript_path = self._transcript_json_path()
        if not source:
            raise RuntimeError("Project/source folder is not ready yet.")
        if not transcript_path:
            raise RuntimeError("transcript_clean.json not found. Run transcript clean first.")
        items = json.loads(transcript_path.read_text(encoding="utf-8", errors="replace"))
        info_path = source / "video_info.json"
        video_info = {}
        if info_path.exists():
            video_info = json.loads(info_path.read_text(encoding="utf-8", errors="replace"))
        return build_chatgpt_studio_prompt(
            items,
            shorts_count=int(self.count_combo.currentText()),
            max_duration=int(self.duration_combo.currentText()),
            video_info=video_info,
            search_ranges=self.search_ranges_text(),
        )

    def refresh_chatgpt_browser_assist_enabled(self):
        if not hasattr(self, "btn_analyze_chatgpt_browser"):
            return
        ready = bool(self._transcript_json_path()) and not self.is_chatgpt_job_running() and not self.is_job_running()
        self.btn_analyze_chatgpt_browser.setEnabled(ready)
        self.btn_analyze_chatgpt_browser.setToolTip("" if ready else "Transcript required")

    def prepare_chatgpt_prompt(self):
        source = self._source_dir()
        if not source:
            self.append_log("ERROR: Project/source folder is not ready yet.")
            return
        try:
            prompt = self._build_chatgpt_prompt_from_current_project()
            prompt_path = source / "chatgpt_studio_prompt.txt"
            prompt_path.write_text(prompt, encoding="utf-8")
            self.chatgpt_prompt_box.setPlainText(prompt)
            self.append_log(f"ChatGPT prompt prepared: {prompt_path}")
        except Exception as exc:
            self.append_log(f"ERROR preparing ChatGPT prompt: {exc}")

    def copy_prompt_to_clipboard(self):
        if not self.chatgpt_prompt_box.toPlainText().strip():
            self.prepare_chatgpt_prompt()
        prompt = self.chatgpt_prompt_box.toPlainText().strip()
        if not prompt:
            return
        QApplication.clipboard().setText(prompt)
        self.append_log("Prompt copied to clipboard.")

    def apply_chatgpt_result(self):
        source = self._source_dir()
        if not source:
            self.append_log("ERROR: Project/source folder is not ready yet.")
            return
        result_text = self.chatgpt_result_box.toPlainText().strip()
        if not result_text:
            self.append_log("ERROR: Paste ChatGPT result first.")
            return
        try:
            analysis = Path(self.current_project_dir) / "analysis"
            parsed, clips = apply_chatgpt_studio_response(
                source,
                analysis,
                result_text,
                shorts_count=int(self.count_combo.currentText()),
                max_duration=int(self.duration_combo.currentText()),
                search_ranges=self.search_ranges_text(),
            )
            self.update_step_status(STEP_BROWSER, "success", f"Applied {len(parsed)} transcript rows and {len(clips)} clips.")
            self.populate_candidates(clips, self.current_project_dir)
            self.append_log(f"ChatGPT result applied ({len(parsed)} transcript rows, {len(clips)} clips).")
            self.continue_after_chatgpt_result()
        except Exception as exc:
            self.append_log(f"ERROR applying ChatGPT result: {exc}")

    def is_job_running(self):
        return bool(self.worker and self.worker.isRunning())

    def is_chatgpt_job_running(self):
        return bool(self.chatgpt_worker and self.chatgpt_worker.isRunning())

    def analyze_with_chatgpt_browser(self):
        if self.is_chatgpt_job_running():
            return
        source = self._source_dir()
        analysis = self._analysis_dir()
        if not source or not analysis:
            self.append_log("ERROR: Project/source folder is not ready yet.")
            return
        if not self._transcript_json_path():
            self.append_log("ERROR: Transcript required.")
            self.refresh_chatgpt_browser_assist_enabled()
            return
        try:
            prompt = self._build_chatgpt_prompt_from_current_project()
            (analysis / "chatgpt_prompt.txt").parent.mkdir(parents=True, exist_ok=True)
            (analysis / "chatgpt_prompt.txt").write_text(prompt, encoding="utf-8")
            self.chatgpt_prompt_box.setPlainText(prompt)
        except Exception as exc:
            self.append_log(f"ERROR preparing ChatGPT prompt: {exc}")
            return

        self.update_step_status(STEP_BROWSER, "running", "ChatGPT Browser Assist is running.")
        self.append_log("Starting ChatGPT Browser Assist...")
        self.chatgpt_worker = ChatGptBrowserAssistWorker(
            source,
            analysis,
            prompt,
            int(self.count_combo.currentText()),
            int(self.duration_combo.currentText()),
            self.search_ranges_text(),
            self,
        )
        self.chatgpt_worker.log.connect(self.append_log)
        self.chatgpt_worker.login_required.connect(self.on_chatgpt_browser_login_required)
        self.chatgpt_worker.finished_ok.connect(self.on_chatgpt_browser_finished)
        self.chatgpt_worker.parse_failed.connect(self.on_chatgpt_browser_parse_failed)
        self.chatgpt_worker.failed.connect(self.on_chatgpt_browser_failed)
        self.chatgpt_worker.finished.connect(self.on_chatgpt_browser_worker_done)
        self.set_chatgpt_browser_controls_enabled(False)
        self.chatgpt_worker.start()

    def set_chatgpt_browser_controls_enabled(self, enabled):
        for widget in [
            self.btn_prepare_chatgpt,
            self.btn_copy_chatgpt,
            self.btn_apply_chatgpt,
            self.btn_analyze_chatgpt_browser,
        ]:
            widget.setEnabled(enabled)
        if enabled:
            self.refresh_chatgpt_browser_assist_enabled()

    def on_chatgpt_browser_login_required(self, message):
        QMessageBox.information(self, "ChatGPT Login", message)
        if self.chatgpt_worker:
            self.chatgpt_worker.continue_after_login()

    def on_chatgpt_browser_finished(self, clips, parsed_count, analysis_dir):
        self.update_step_status(STEP_BROWSER, "success", f"Applied {parsed_count} transcript rows and {len(clips)} clips.")
        self.populate_candidates(clips, self.current_project_dir)
        self.append_log(f"ChatGPT Browser Assist completed. Files saved in {analysis_dir}")
        self.continue_after_chatgpt_result()

    def on_chatgpt_browser_parse_failed(self, raw_response, error_message):
        self.chatgpt_result_box.setPlainText(raw_response)
        self.update_step_status(STEP_BROWSER, "error", "ChatGPT JSON parse failed.")
        self.append_log(f"ERROR parsing ChatGPT response: {error_message}")
        self.append_log("Raw response was copied into the manual result box for correction.")

    def on_chatgpt_browser_failed(self, message):
        self.update_step_status(STEP_BROWSER, "error", message)
        self.append_log(f"ERROR running ChatGPT Browser Assist: {message}")

    def on_chatgpt_browser_worker_done(self):
        self.set_chatgpt_browser_controls_enabled(not self.is_job_running())
        self.refresh_run_enabled()

    def refresh_run_enabled(self, *_args):
        if not hasattr(self, "btn_run"):
            return
        ready = bool(self.url_input.text().strip()) and bool(self.selected_steps()) and not self.is_job_running() and not self.is_chatgpt_job_running()
        self.btn_run.setEnabled(ready)
        self.refresh_chatgpt_browser_assist_enabled()

    def set_controls_enabled(self, enabled):
        for widget in [
            self.url_input,
            self.output_input,
            self.btn_browse,
            self.count_combo,
            self.duration_combo,
            self.model_input,
            self.range_enabled_check,
            self.range_input,
        ]:
            widget.setEnabled(enabled)
        for step, check in self.step_checks.items():
            check.setEnabled(enabled)
        if hasattr(self, "btn_prepare_chatgpt"):
            self.btn_prepare_chatgpt.setEnabled(enabled)
            self.btn_copy_chatgpt.setEnabled(enabled)
            self.btn_apply_chatgpt.setEnabled(enabled)
            if enabled:
                self.refresh_chatgpt_browser_assist_enabled()
            else:
                self.btn_analyze_chatgpt_browser.setEnabled(False)

    def run_selected_steps(self):
        if self.is_job_running():
            return
        url = self.url_input.text().strip()
        steps = self.selected_steps()
        if not url:
            self.append_log("ERROR: YouTube URL is required.")
            return
        if not steps:
            self.append_log("ERROR: Select at least one step.")
            return
        if steps == [STEP_BROWSER]:
            self.pending_post_browser_request = None
            self.prepare_chatgpt_prompt()
            return

        browser_selected = STEP_BROWSER in steps
        if browser_selected:
            pipeline_steps = [step for step in steps if step != STEP_BROWSER and step not in POST_BROWSER_STEPS]
            post_browser_steps = [step for step in steps if step in POST_BROWSER_STEPS]
        else:
            pipeline_steps = [step for step in steps if step != STEP_BROWSER]
            post_browser_steps = []

        existing_project_dir = None
        if self.current_project_dir and self.current_url == url:
            existing_project_dir = self.current_project_dir

        request = {
            "url": url,
            "output_root": self.output_input.text().strip() or str(self.default_output_root),
            "shorts_count": int(self.count_combo.currentText()),
            "max_duration": int(self.duration_combo.currentText()),
            "model_name": self.model_input.text().strip() or self.default_model,
            "selected_steps": pipeline_steps,
            "selected_clip_nos": self.selected_clip_nos(),
            "existing_project_dir": existing_project_dir,
            "translate_english_with_local_ai": not browser_selected,
        }
        self.pending_post_browser_request = None
        if browser_selected and post_browser_steps:
            self.pending_post_browser_request = dict(request)
            self.pending_post_browser_request["selected_steps"] = post_browser_steps
            self.pending_post_browser_request["translate_english_with_local_ai"] = False

        self.current_url = url
        self._reset_step_statuses()
        self.completed_steps = set()
        self.total_selected_steps = len(pipeline_steps) + len(post_browser_steps) + (1 if browser_selected else 0)
        self.global_progress.setValue(0)
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Running...")
        self.btn_cancel.setEnabled(True)
        self.set_controls_enabled(False)
        self.current_worker_phase = "pre_browser" if browser_selected else "normal"
        self.worker = ShortsWorker(request, self.model_session_manager, self)
        self.worker.log.connect(self.append_log)
        self.worker.step_status.connect(self.update_step_status)
        self.worker.step_progress.connect(self.update_step_progress)
        self.worker.candidates_ready.connect(self.populate_candidates)
        self.worker.project_ready.connect(self.set_project_dir)
        self.worker.finished_ok.connect(self.on_worker_finished)
        self.worker.failed.connect(self.on_worker_failed)
        self.worker.start()

    def continue_after_chatgpt_result(self):
        if not self.pending_post_browser_request:
            post_steps = [step for step in self.selected_steps() if step in POST_BROWSER_STEPS]
            if post_steps:
                self.pending_post_browser_request = {
                    "url": self.url_input.text().strip(),
                    "output_root": self.output_input.text().strip() or str(self.default_output_root),
                    "shorts_count": int(self.count_combo.currentText()),
                    "max_duration": int(self.duration_combo.currentText()),
                    "model_name": self.model_input.text().strip() or self.default_model,
                    "selected_steps": post_steps,
                    "selected_clip_nos": self.selected_clip_nos(),
                    "existing_project_dir": self.current_project_dir,
                    "translate_english_with_local_ai": False,
                }
                return self.continue_after_chatgpt_result()
            self.set_controls_enabled(True)
            self.global_progress.setValue(100)
            self.btn_run.setText("Run Selected Steps")
            self.btn_cancel.setEnabled(False)
            self.refresh_run_enabled()
            return
        request = dict(self.pending_post_browser_request)
        request["existing_project_dir"] = self.current_project_dir
        request["selected_clip_nos"] = self.selected_clip_nos()
        self.pending_post_browser_request = None
        self.append_log("Continuing selected post-ChatGPT steps...")
        self.current_worker_phase = "post_browser"
        self.set_controls_enabled(False)
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Running...")
        self.btn_cancel.setEnabled(True)
        self.worker = ShortsWorker(request, self.model_session_manager, self)
        self.worker.log.connect(self.append_log)
        self.worker.step_status.connect(self.update_step_status)
        self.worker.step_progress.connect(self.update_step_progress)
        self.worker.candidates_ready.connect(self.populate_candidates)
        self.worker.project_ready.connect(self.set_project_dir)
        self.worker.finished_ok.connect(self.on_worker_finished)
        self.worker.failed.connect(self.on_worker_failed)
        self.worker.start()

    def cancel_job(self):
        if self.worker and self.worker.isRunning():
            self.append_log("Cancelling job...")
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)

    def search_ranges_text(self):
        if not self.range_enabled_check.isChecked():
            return ""
        return self.range_input.toPlainText().strip()

    def append_log(self, message):
        self.log_box.append(str(message).replace("\n", "<br>"))
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def update_step_status(self, step, status, message=""):
        label = self.step_status_labels.get(step)
        if label:
            label.setText(f"{STATUS_ICON.get(status, '?')} {status}")
            if status == "running":
                label.setStyleSheet("color: #F9E2AF; font-weight: bold;")
            elif status == "success":
                label.setStyleSheet("color: #A6E3A1; font-weight: bold;")
            elif status == "warning":
                label.setStyleSheet("color: #F9E2AF; font-weight: bold;")
            elif status == "error":
                label.setStyleSheet("color: #F38BA8; font-weight: bold;")
            else:
                label.setStyleSheet("color: #A6ADC8;")
        progress = self.step_progress_bars.get(step)
        if progress:
            if status == "queued":
                progress.setValue(0)
            elif status in ["success", "warning"]:
                progress.setValue(100)
            elif status in ["error", "skipped", "cancelled"]:
                progress.setValue(progress.value())
        message_label = self.step_message_labels.get(step)
        if message_label:
            message_label.setText(message or "")
        if status in ["success", "warning", "error", "skipped", "cancelled"]:
            self.completed_steps.add(step)
            self._update_global_progress()
        if message and status not in ["skipped"]:
            self.append_log(f"{STEP_LABELS.get(step, step)}: {status} - {message}")

    def update_step_progress(self, step, percent, message=""):
        progress = self.step_progress_bars.get(step)
        if progress:
            progress.setValue(max(0, min(100, int(percent))))
        message_label = self.step_message_labels.get(step)
        if message_label and message:
            message_label.setText(message)
        self._update_global_progress()

    def _update_global_progress(self):
        if self.total_selected_steps <= 0:
            self.global_progress.setValue(0)
            return
        completed = len([s for s in self.completed_steps if s in self.selected_steps()])
        partial = 0
        for step in self.selected_steps():
            if step not in self.completed_steps:
                partial += self.step_progress_bars.get(step).value() if step in self.step_progress_bars else 0
        value = int(((completed * 100) + partial) / max(1, self.total_selected_steps))
        self.global_progress.setValue(max(0, min(100, value)))

    def populate_candidates(self, clips, project_dir):
        self.candidates = clips
        self.current_project_dir = project_dir
        self.refresh_chatgpt_browser_assist_enabled()
        self.candidates_table.setRowCount(0)
        for row, clip in enumerate(clips):
            self.candidates_table.insertRow(row)
            render_item = QTableWidgetItem("")
            render_item.setFlags(render_item.flags() | Qt.ItemIsUserCheckable)
            render_item.setCheckState(Qt.Checked)
            render_item.setData(Qt.UserRole, int(clip.get("clip_no") or row + 1))
            self.candidates_table.setItem(row, 0, render_item)
            values = [
                clip.get("start", ""),
                clip.get("end", ""),
                clip.get("duration_seconds", ""),
                clip.get("score", ""),
                clip.get("title", ""),
                clip.get("reason", ""),
            ]
            for col, value in enumerate(values, start=1):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.candidates_table.setItem(row, col, item)
        self.append_log(f"Clip candidates loaded from {project_dir}")

    def on_worker_finished(self, project_dir):
        self.current_project_dir = project_dir
        self.set_controls_enabled(True)
        self.refresh_run_enabled()
        self.btn_run.setText("Run Selected Steps")
        self.btn_cancel.setEnabled(False)
        self.append_log(f"DONE: {project_dir}")
        phase = self.current_worker_phase
        self.current_worker_phase = None
        if phase == "pre_browser":
            self.prepare_chatgpt_prompt()
            self.update_step_status(STEP_BROWSER, "running", "Paste prompt into ChatGPT, then apply the result.")
            self.btn_run.setText("Run Selected Steps")
            self.btn_cancel.setEnabled(False)
            self.refresh_run_enabled()
            self.refresh_chatgpt_browser_assist_enabled()
        else:
            self.global_progress.setValue(100)

    def on_worker_failed(self, message):
        if "cancelled" in message.lower():
            for step in self.selected_steps():
                label = self.step_status_labels.get(step)
                if label and ("queued" in label.text() or "running" in label.text()):
                    self.update_step_status(step, "cancelled", "cancelled")
        self.set_controls_enabled(True)
        self.refresh_run_enabled()
        self.btn_run.setText("Run Selected Steps")
        self.btn_cancel.setEnabled(False)
        self.append_log(f"ERROR: {message}")
        self.refresh_chatgpt_browser_assist_enabled()

    def _reset_step_statuses(self):
        for step, label in self.step_status_labels.items():
            status = "skipped" if step == STEP_BROWSER else "idle"
            label.setText(f"{STATUS_ICON[status]} {status}")
            label.setStyleSheet("color: #A6ADC8;")
            if step in self.step_progress_bars:
                self.step_progress_bars[step].setValue(0)
            if step in self.step_message_labels:
                self.step_message_labels[step].setText("use panel below" if step == STEP_BROWSER else "")
        if hasattr(self, "global_progress"):
            self.global_progress.setValue(0)
