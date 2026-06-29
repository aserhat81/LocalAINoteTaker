import json
import re
import shutil
import subprocess
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import requests


STEP_VIDEO = "download_video"
STEP_AUDIO = "download_audio"
STEP_TRANSCRIPT = "download_transcript"
STEP_CLEAN = "clean_transcript"
STEP_AI = "ai_candidates"
STEP_RENDER = "render_shorts"
STEP_SUBTITLES = "burn_subtitles"
STEP_METADATA = "metadata"
STEP_BROWSER = "browser_assist"


class ShortsPipeline:
    def __init__(
        self,
        url,
        output_root,
        shorts_count,
        max_duration,
        model_name,
        selected_steps,
        selected_clip_nos=None,
        existing_project_dir=None,
        model_session_manager=None,
        translate_english_with_local_ai=True,
        log=None,
        progress=None,
    ):
        self.url = (url or "").strip()
        self.output_root = Path(output_root or "output")
        self.shorts_count = int(shorts_count or 3)
        self.max_duration = int(max_duration or 60)
        self.model_name = (model_name or "qwen3.5:4b").strip() or "qwen3.5:4b"
        self.selected_steps = set(selected_steps or [])
        self.selected_clip_nos = set(selected_clip_nos or [])
        self.existing_project_dir = Path(existing_project_dir) if existing_project_dir else None
        self.model_session_manager = model_session_manager
        self.translate_english_with_local_ai = translate_english_with_local_ai
        self.log = log or (lambda message: None)
        self.progress = progress or (lambda step, percent, message="": None)

        self.root_dir = Path(__file__).resolve().parents[1]
        self.project_dir = None
        self.source_dir = None
        self.analysis_dir = None
        self.shorts_dir = None
        self.video_info = {}
        self.source_title = ""
        self.transcript_language = None
        self.cancelled = False
        self.current_process = None
        self.step_results = {}

    def cancel(self):
        self.cancelled = True
        proc = self.current_process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    def _check_cancelled(self):
        if self.cancelled:
            raise RuntimeError("Job cancelled.")

    def run(self, step_started=None, step_finished=None, candidates_ready=None, project_ready=None):
        if not self.url:
            raise ValueError("YouTube URL is required.")

        step_started = step_started or (lambda step: None)
        step_finished = step_finished or (lambda step, status, message="": None)
        candidates_ready = candidates_ready or (lambda clips, project_dir: None)
        project_ready = project_ready or (lambda project_dir: None)

        for step in self.selected_steps:
            step_finished(step, "queued", "waiting")

        self._prepare_project()
        project_ready(str(self.project_dir))

        for step in [
            STEP_VIDEO,
            STEP_AUDIO,
            STEP_TRANSCRIPT,
            STEP_CLEAN,
            STEP_AI,
            STEP_RENDER,
            STEP_SUBTITLES,
            STEP_METADATA,
            STEP_BROWSER,
        ]:
            self._check_cancelled()
            if step not in self.selected_steps:
                step_finished(step, "skipped", "Not selected.")
                continue

            if step == STEP_SUBTITLES and STEP_RENDER in self.selected_steps:
                continue
            if step == STEP_BROWSER:
                step_finished(step, "skipped", "ChatGPT Browser Assist is disabled for now.")
                continue
            if self._should_skip_for_failed_dependency(step):
                message = self._dependency_skip_message(step)
                self.step_results[step] = "skipped"
                step_finished(step, "skipped", message)
                continue

            step_started(step)
            try:
                if step == STEP_VIDEO:
                    self._download_video()
                elif step == STEP_AUDIO:
                    self._download_audio()
                elif step == STEP_TRANSCRIPT:
                    self._download_transcript()
                elif step == STEP_CLEAN:
                    self._clean_transcript()
                elif step == STEP_AI:
                    clips = self._find_clip_candidates()
                    candidates_ready(clips, str(self.project_dir))
                elif step == STEP_RENDER:
                    self._render_selected_shorts()
                    if STEP_SUBTITLES in self.selected_steps:
                        step_finished(STEP_SUBTITLES, "success", "Subtitles embedded during render.")
                elif step == STEP_METADATA:
                    self._write_metadata_for_selected()
                if self.step_results.get(step) == "warning":
                    step_finished(step, "warning", "Completed with warning.")
                else:
                    self.step_results[step] = "success"
                    step_finished(step, "success", "Done.")
            except Exception as exc:
                if str(exc) == "Job cancelled.":
                    self.step_results[step] = "cancelled"
                    step_finished(step, "cancelled", "cancelled")
                    raise
                step_finished(step, "error", str(exc))
                self.step_results[step] = "error"
                raise

        return {
            "project_dir": str(self.project_dir),
            "video_info": self.video_info,
        }

    def _should_skip_for_failed_dependency(self, step):
        if step in [STEP_CLEAN, STEP_AI, STEP_RENDER, STEP_METADATA]:
            if STEP_TRANSCRIPT in self.step_results and self.step_results[STEP_TRANSCRIPT] in ["error", "skipped"]:
                return True
        if step in [STEP_AI, STEP_RENDER, STEP_METADATA]:
            if STEP_CLEAN in self.step_results and self.step_results[STEP_CLEAN] in ["error", "skipped"]:
                return True
        if step == STEP_RENDER:
            if STEP_VIDEO in self.step_results and self.step_results[STEP_VIDEO] in ["error", "skipped"]:
                return True
            if STEP_AI in self.step_results and self.step_results[STEP_AI] in ["error", "skipped"]:
                return True
        return False

    def _dependency_skip_message(self, step):
        if step in [STEP_CLEAN, STEP_AI, STEP_RENDER, STEP_METADATA]:
            if STEP_TRANSCRIPT in self.step_results and self.step_results[STEP_TRANSCRIPT] in ["error", "skipped"]:
                return "Skipped because transcript is unavailable."
        if step in [STEP_AI, STEP_RENDER, STEP_METADATA]:
            if STEP_CLEAN in self.step_results and self.step_results[STEP_CLEAN] in ["error", "skipped"]:
                return "Skipped because clean transcript is unavailable."
        if step == STEP_RENDER:
            if STEP_VIDEO in self.step_results and self.step_results[STEP_VIDEO] in ["error", "skipped"]:
                return "Skipped because source video is unavailable."
            if STEP_AI in self.step_results and self.step_results[STEP_AI] in ["error", "skipped"]:
                return "Skipped because clip candidates are unavailable."
        return "Skipped because a required previous step failed."

    def _prepare_project(self):
        self.progress("video_info", 10, "Reading video info")
        self.output_root.mkdir(parents=True, exist_ok=True)
        if self.existing_project_dir and self.existing_project_dir.exists():
            self.project_dir = self.existing_project_dir
            info_path = self.project_dir / "source" / "video_info.json"
            if info_path.exists():
                self.video_info = self._read_json(info_path, {})
                self.source_title = self.video_info.get("title") or self.project_dir.name
            lang_path = self.project_dir / "source" / "transcript_language.txt"
            if lang_path.exists():
                self.transcript_language = lang_path.read_text(encoding="utf-8", errors="replace").strip() or None
        else:
            self.video_info = self._fetch_video_info()
            self.progress("video_info", 90, "Video info parsed")
            self.source_title = self.video_info.get("title") or "youtube-video"
            self.project_dir = self._unique_project_dir(slugify(self.source_title), self.output_root)

        self.source_dir = self.project_dir / "source"
        self.analysis_dir = self.project_dir / "analysis"
        self.shorts_dir = self.project_dir / "shorts"
        for folder in [self.source_dir, self.analysis_dir, self.shorts_dir]:
            folder.mkdir(parents=True, exist_ok=True)

        if self.video_info:
            self._write_json(self.source_dir / "video_info.json", self.video_info)

        self.progress("video_info", 100, "Project folder ready")
        self._log_video_summary()

    def _fetch_video_info(self):
        yt_dlp = self._find_tool("yt-dlp.exe", "yt-dlp")
        self.log("Reading YouTube video info...")
        self.progress("video_info", 50, "yt-dlp is reading metadata")
        output = self._run_command([yt_dlp, "--dump-json", "--skip-download", self.url], quiet_json=True)
        try:
            return extract_json_object(output)
        except Exception:
            return {"title": "youtube-video", "webpage_url": self.url}

    def _log_video_summary(self):
        title = self.video_info.get("title") or self.source_title or "Unknown"
        duration = self.video_info.get("duration_string") or self.video_info.get("duration") or "Unknown"
        channel = self.video_info.get("channel") or self.video_info.get("uploader") or "Unknown"
        fmt = self.video_info.get("format") or self.video_info.get("format_id") or "best"
        self.log(f"Video title: {title}")
        self.log(f"Duration: {duration}")
        self.log(f"Channel: {channel}")
        self.log(f"Selected format: {fmt}")
        self.log(f"Project folder: {self.project_dir}")

    def _download_video(self):
        yt_dlp = self._find_tool("yt-dlp.exe", "yt-dlp")
        self.log("Downloading source video...")
        target = self.source_dir / "source_video.%(ext)s"
        self.progress(STEP_VIDEO, 5, "Starting video download")
        self._run_command([
            yt_dlp,
            "-f",
            "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
            "--merge-output-format",
            "mp4",
            "-o",
            str(target),
            self.url,
        ], step=STEP_VIDEO)
        self._normalize_output_file("source_video", ".mp4")
        self.progress(STEP_VIDEO, 100, "source_video.mp4 saved")

    def _download_audio(self):
        yt_dlp = self._find_tool("yt-dlp.exe", "yt-dlp")
        self.log("Downloading source audio...")
        target = self.source_dir / "source_audio.%(ext)s"
        self.progress(STEP_AUDIO, 5, "Starting audio download")
        self._run_command([
            yt_dlp,
            "-x",
            "--audio-format",
            "mp3",
            "-o",
            str(target),
            self.url,
        ], step=STEP_AUDIO)
        self._normalize_output_file("source_audio", ".mp3")
        self.progress(STEP_AUDIO, 100, "source_audio.mp3 saved")

    def _download_transcript(self):
        yt_dlp = self._find_tool("yt-dlp.exe", "yt-dlp")
        self.log("Downloading subtitles/transcript...")
        self.progress(STEP_TRANSCRIPT, 10, "Checking available subtitles")
        self._remove_matching("transcript_raw*")
        languages = self._subtitle_language_candidates()
        attempts = []

        for mode, flag in [("manual", "--write-subs"), ("auto", "--write-auto-subs")]:
            for index, lang in enumerate(languages):
                self._check_cancelled()
                self.log(f"Trying {mode} subtitle: {lang}")
                self.progress(STEP_TRANSCRIPT, min(85, 20 + index * 8), f"Trying {mode}: {lang}")
                self._remove_matching("transcript_raw*")
                base = self.source_dir / "transcript_raw.%(language)s.%(ext)s"
                cmd = [
                    yt_dlp,
                    "--skip-download",
                    flag,
                    "--sub-langs",
                    lang,
                    "--convert-subs",
                    "srt",
                    "-o",
                    str(base),
                    self.url,
                ]
                output = self._run_command(cmd, allow_failure=True, step=STEP_TRANSCRIPT)
                attempts.append(output)
                transcript_path = self._first_matching_transcript()
                if transcript_path:
                    self.transcript_language = lang
                    self._promote_transcript_file(transcript_path)
                    self.progress(STEP_TRANSCRIPT, 100, f"Transcript saved from {mode} subtitle: {lang}")
                    self.log(f"Transcript saved from {mode} subtitle: {lang}")
                    return
                if "429" in output or "Too Many Requests" in output:
                    self.log(f"WARNING: {mode} subtitle {lang} hit HTTP 429; trying next language.")
                else:
                    self.log(f"No {mode} subtitle found for {lang}")

        self.log("WARNING: Subtitle download failed, falling back to Whisper.")
        self.progress(STEP_TRANSCRIPT, 88, "Subtitle failed, falling back to Whisper")
        try:
            self._whisper_fallback_transcript()
            self.step_results[STEP_TRANSCRIPT] = "success"
            self.progress(STEP_TRANSCRIPT, 100, "Transcript generated with Whisper fallback")
            self.log("Transcript generated with Whisper fallback")
        except Exception as exc:
            self.step_results[STEP_TRANSCRIPT] = "error"
            raise RuntimeError(f"Subtitle download failed and Whisper fallback failed: {exc}")

    def _subtitle_language_candidates(self):
        available = set()
        for key in ["subtitles", "automatic_captions"]:
            data = self.video_info.get(key) or {}
            if isinstance(data, dict):
                available.update(data.keys())

        # Keep the workflow bounded: Turkish first, English second. YouTube may
        # expose hundreds of auto-translation languages; trying them all looks
        # like an endless loop and can trigger rate limits.
        turkish = self._choose_available_language(["tr", "tr-TR"], available) or "tr"
        english = self._choose_available_language(["en", "en-US", "en-GB"], available) or "en"
        return [lang for lang in [turkish, english] if lang]

    def _choose_available_language(self, preferred, available):
        for lang in preferred:
            if lang in available:
                return lang
        for candidate in sorted(available):
            if any(candidate.casefold().startswith(lang.casefold()) for lang in preferred):
                return candidate
        return None

    def _promote_transcript_file(self, path):
        ext = path.suffix.lower()
        if ext == ".srt":
            final_path = self.source_dir / "transcript_raw.srt"
        elif ext == ".vtt":
            final_path = self.source_dir / "transcript_raw.vtt"
        else:
            final_path = self.source_dir / f"transcript_raw{ext}"
        if path.resolve() != final_path.resolve():
            shutil.copyfile(path, final_path)
        if self.transcript_language:
            (self.source_dir / "transcript_language.txt").write_text(self.transcript_language, encoding="utf-8")

    def _whisper_fallback_transcript(self):
        self._ensure_asr_ready_for_whisper()
        media_path = self.source_dir / "source_audio.mp3"
        if not media_path.exists():
            video_path = self.source_dir / "source_video.mp4"
            if video_path.exists():
                ffmpeg = self._find_tool("ffmpeg.exe", "ffmpeg")
                media_path = self.source_dir / "source_audio.mp3"
                self._run_command([
                    ffmpeg,
                    "-y",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-acodec",
                    "libmp3lame",
                    str(media_path),
                ], allow_failure=False)
            else:
                raise RuntimeError("Subtitle indirilemedi. Whisper fallback için video veya ses dosyası gerekir.")

        chunks_dir = self.source_dir / "whisper_chunks"
        if chunks_dir.exists():
            shutil.rmtree(chunks_dir)
        chunks_dir.mkdir(parents=True, exist_ok=True)
        ffmpeg = self._find_tool("ffmpeg.exe", "ffmpeg")
        chunk_pattern = chunks_dir / "chunk_%03d.wav"
        self._run_command([
            ffmpeg,
            "-y",
            "-i",
            str(media_path),
            "-f",
            "segment",
            "-segment_time",
            "60",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(chunk_pattern),
        ], allow_failure=False)

        chunk_paths = sorted(chunks_dir.glob("chunk_*.wav"))
        if not chunk_paths:
            raise RuntimeError("Whisper fallback could not create audio chunks.")

        entries = []
        for index, chunk_path in enumerate(chunk_paths):
            self._check_cancelled()
            start = index * 60
            end = start + 60
            self.progress(STEP_TRANSCRIPT, min(99, 88 + int(((index + 1) / len(chunk_paths)) * 10)), f"Whisper chunk {index + 1}/{len(chunk_paths)}")
            text = self._transcribe_audio_file(chunk_path)
            if text:
                entries.append({
                    "index": len(entries) + 1,
                    "start": seconds_to_hms(start),
                    "end": seconds_to_hms(end),
                    "text": text,
                })

        if not entries:
            raise RuntimeError("Whisper fallback returned no transcript text.")

        srt_text = "\n\n".join(
            f"{item['index']}\n{item['start']},000 --> {item['end']},000\n{item['text']}"
            for item in entries
        )
        (self.source_dir / "transcript_raw_whisper.srt").write_text(srt_text, encoding="utf-8")
        self._write_json(self.source_dir / "transcript_raw_whisper.json", entries)
        shutil.copyfile(self.source_dir / "transcript_raw_whisper.srt", self.source_dir / "transcript_raw.srt")
        self.transcript_language = "tr"
        (self.source_dir / "transcript_language.txt").write_text(self.transcript_language, encoding="utf-8")

    def _transcribe_audio_file(self, audio_path):
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/wav")}
            data = {"model": "whisper-v3:turbo", "response_format": "json", "language": "tr"}
        response = requests.post("http://127.0.0.1:52625/v1/audio/transcriptions", files=files, data=data, timeout=18000)
        if response.status_code != 200:
            raise RuntimeError(f"Whisper HTTP {response.status_code}: {response.text[:300]}")
        result = response.json()
        return clean_text(result.get("text", ""))

    def _ensure_asr_ready_for_whisper(self):
        try:
            resp = requests.get("http://127.0.0.1:52625/v1/models", timeout=2)
            if resp.status_code == 200:
                return
        except Exception:
            pass

        flm_manager = getattr(self.model_session_manager, "flm_manager", None)
        if not flm_manager:
            raise RuntimeError("Local Whisper service is not running.")
        if getattr(self.model_session_manager, "note_taker_busy", lambda: False)():
            raise RuntimeError("Note Taker is currently using the local AI service.")

        if flm_manager.is_running:
            flm_manager.stop_service(emit_status=False)
        flm_manager.start_service(self.model_name)
        deadline = time.time() + 180
        while time.time() < deadline:
            self._check_cancelled()
            try:
                resp = requests.get("http://127.0.0.1:52625/v1/models", timeout=2)
                if resp.status_code == 200:
                    return
            except Exception:
                pass
            time.sleep(2)
        raise RuntimeError("Local Whisper service did not become ready.")

    def _clean_transcript(self):
        srt_path = self.source_dir / "transcript_raw.srt"
        vtt_path = self.source_dir / "transcript_raw.vtt"
        if srt_path.exists():
            entries = parse_srt(srt_path.read_text(encoding="utf-8", errors="replace"))
        elif vtt_path.exists():
            entries = parse_vtt(vtt_path.read_text(encoding="utf-8", errors="replace"))
        else:
            raise RuntimeError("transcript_raw.srt or transcript_raw.vtt not found.")
        if not entries:
            raise RuntimeError("Transcript is empty.")

        txt_lines = []
        json_items = []
        for item in entries:
            text = clean_text(item["text"])
            if not text:
                continue
            txt_lines.append(f"[{item['start']} - {item['end']}] {text}")
            json_items.append({"start": item["start"], "end": item["end"], "text": text})

        (self.source_dir / "transcript_clean.txt").write_text("\n".join(txt_lines), encoding="utf-8")
        self._write_json(self.source_dir / "transcript_clean.json", json_items)
        if self._should_translate_transcript_to_turkish():
            if self.translate_english_with_local_ai:
                self._translate_clean_transcript_to_turkish(json_items)
            else:
                self._prepare_chatgpt_translation_files(json_items)
        self.log("Transcript cleaned.")
        self.progress(STEP_CLEAN, 100, "Transcript cleaned")

    def _should_translate_transcript_to_turkish(self):
        lang = (self.transcript_language or "").casefold()
        return lang.startswith("en")

    def _translate_clean_transcript_to_turkish(self, json_items):
        if not json_items:
            return
        self.log("English transcript found. Translating transcript to Turkish with Local AI...")
        self.progress(STEP_CLEAN, 70, "Translating English transcript to Turkish")
        original_txt = self.source_dir / "transcript_clean_en.txt"
        original_json = self.source_dir / "transcript_clean_en.json"
        shutil.copyfile(self.source_dir / "transcript_clean.txt", original_txt)
        shutil.copyfile(self.source_dir / "transcript_clean.json", original_json)
        self._write_chatgpt_translation_prompt(json_items)
        owner = "shorts_studio_translate"
        acquired = False
        try:
            if self.model_session_manager:
                self.model_session_manager.acquire(self.model_name, owner)
                acquired = True
            translated_items = []
            chunks = [json_items[i:i + 40] for i in range(0, len(json_items), 40)]
            for index, chunk in enumerate(chunks):
                self._check_cancelled()
                self.progress(STEP_CLEAN, 70 + int(((index + 1) / len(chunks)) * 25), f"Translating chunk {index + 1}/{len(chunks)}")
                translated_items.extend(self._translate_transcript_chunk(chunk, index + 1))

            if not translated_items:
                raise RuntimeError("Local AI returned no translated transcript.")

            txt_lines = [f"[{item['start']} - {item['end']}] {clean_text(item.get('text', ''))}" for item in translated_items if clean_text(item.get("text", ""))]
            (self.source_dir / "transcript_clean.txt").write_text("\n".join(txt_lines), encoding="utf-8")
            self._write_json(self.source_dir / "transcript_clean.json", translated_items)
            self._write_json(self.source_dir / "transcript_translation_tr.json", translated_items)
            self.log("Transcript translated to Turkish.")
        finally:
            if acquired:
                self.model_session_manager.release(self.model_name, owner)

    def _prepare_chatgpt_translation_files(self, json_items):
        self.log("English transcript found. ChatGPT Browser Assist selected; local translation skipped.")
        original_txt = self.source_dir / "transcript_clean_en.txt"
        original_json = self.source_dir / "transcript_clean_en.json"
        shutil.copyfile(self.source_dir / "transcript_clean.txt", original_txt)
        shutil.copyfile(self.source_dir / "transcript_clean.json", original_json)
        self._write_chatgpt_translation_prompt(json_items)

    def _write_chatgpt_translation_prompt(self, json_items):
        prompt_path = self.source_dir / "chatgpt_translation_prompt.txt"
        prompt_path.write_text(build_chatgpt_translation_prompt(json_items), encoding="utf-8")
        self.log(f"ChatGPT translation prompt saved: {prompt_path}")

    def _translate_transcript_chunk(self, chunk, chunk_no):
        prompt = (
            "Translate the following timestamped transcript entries from English to Turkish.\n"
            "Keep start/end timestamps exactly the same. Preserve meaning, names and technical terms.\n"
            "Return only valid JSON as an array of objects with start, end and text fields.\n"
            "Do not use trailing commas before } or ].\n\n"
            f"{json.dumps(chunk, ensure_ascii=False, indent=2)}"
        )
        content = self._call_translation_ai(prompt)
        (self.source_dir / f"translation_chunk_{chunk_no:03d}_raw.txt").write_text(content, encoding="utf-8")
        try:
            data = extract_json_array(content)
            if isinstance(data, dict):
                data = data.get("items") or data.get("entries") or data.get("transcript") or data.get("translations")
            if not isinstance(data, list):
                raise RuntimeError("Translation response was not a JSON array.")
        except Exception as exc:
            self.log(f"WARNING: Translation JSON parse failed on chunk {chunk_no}; retrying as TSV. {exc}")
            return self._translate_transcript_chunk_tsv(chunk, chunk_no)

        normalized = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            source = chunk[min(index, len(chunk) - 1)]
            normalized.append({
                "start": item.get("start") or source.get("start"),
                "end": item.get("end") or source.get("end"),
                "text": clean_text(item.get("text", "")),
            })
        return normalized

    def _translate_transcript_chunk_tsv(self, chunk, chunk_no):
        lines = []
        for index, item in enumerate(chunk, start=1):
            text = clean_text(item.get("text", ""))
            lines.append(f"{index}\t{item.get('start', '')}\t{item.get('end', '')}\t{text}")
        prompt = (
            "Translate these subtitle rows from English to Turkish.\n"
            "Return plain TSV only. No JSON. No markdown. No explanations.\n"
            "Each output row must be: row_number<TAB>start<TAB>end<TAB>turkish_text\n"
            "Keep row_number, start and end exactly the same.\n\n"
            + "\n".join(lines)
        )
        content = self._call_translation_ai(
            prompt,
            system_prompt="You translate subtitle rows from English to Turkish and return plain TSV only.",
        )
        (self.source_dir / f"translation_chunk_{chunk_no:03d}_raw.tsv").write_text(content, encoding="utf-8")
        parsed = self._parse_translation_tsv(content, chunk)
        if parsed:
            return parsed

        self.log(f"WARNING: Translation TSV parse failed on chunk {chunk_no}; retrying line by line.")
        return self._translate_transcript_chunk_line_by_line(chunk)

    def _parse_translation_tsv(self, content, chunk):
        rows = []
        for line in (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = line.strip().strip("|")
            if not line or line.startswith("```"):
                continue
            if "\t" in line:
                parts = line.split("\t", 3)
            else:
                parts = [part.strip() for part in line.split("|", 3)]
            if len(parts) < 4:
                continue
            try:
                row_index = int(re.sub(r"\D", "", parts[0]) or "0") - 1
            except Exception:
                row_index = len(rows)
            if row_index < 0 or row_index >= len(chunk):
                row_index = len(rows)
            if row_index >= len(chunk):
                continue
            source = chunk[row_index]
            rows.append({
                "start": parts[1].strip() or source.get("start"),
                "end": parts[2].strip() or source.get("end"),
                "text": clean_text(parts[3]),
            })
        return rows if len(rows) >= max(1, len(chunk) // 2) else []

    def _translate_transcript_chunk_line_by_line(self, chunk):
        translated = []
        for item in chunk:
            self._check_cancelled()
            text = clean_text(item.get("text", ""))
            if not text:
                continue
            prompt = (
                "Translate this subtitle text from English to Turkish.\n"
                "Return only the Turkish translation, no quotes, no markdown:\n\n"
                f"{text}"
            )
            translated_text = self._call_translation_ai(
                prompt,
                system_prompt="You translate one subtitle line from English to Turkish. Return plain text only.",
                max_tokens=300,
            )
            translated.append({
                "start": item.get("start"),
                "end": item.get("end"),
                "text": clean_text(translated_text),
            })
        return translated

    def _call_translation_ai(self, prompt, system_prompt=None, max_tokens=3000):
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a precise EN-to-TR subtitle translator. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "repeat_penalty": 1.05,
            "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        response = requests.post("http://127.0.0.1:52625/v1/chat/completions", json=data, timeout=18000)
        if response.status_code != 200:
            raise RuntimeError(f"Translation AI HTTP {response.status_code}: {response.text[:500]}")
        result = response.json()
        choices = result.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content") or choices[0].get("text")
            if content:
                return content.strip()
        raise RuntimeError("Translation AI returned an empty response.")

    def _find_clip_candidates(self):
        clean_txt = self.source_dir / "transcript_clean.txt"
        if not clean_txt.exists():
            raise RuntimeError("transcript_clean.txt not found.")
        transcript = clean_txt.read_text(encoding="utf-8", errors="replace")
        prompt = self._build_ai_prompt(transcript)
        (self.analysis_dir / "local_ai_prompt.txt").write_text(prompt, encoding="utf-8")

        owner = "shorts_studio"
        acquired = False
        try:
            if self.model_session_manager:
                self.model_session_manager.acquire(self.model_name, owner)
                acquired = True
            content = self._call_local_ai(prompt)
            (self.analysis_dir / "local_ai_result.json").write_text(content, encoding="utf-8")
            result = extract_json_object(content)
            clips = result.get("clips", [])
            if not isinstance(clips, list) or not clips:
                raise RuntimeError("Local AI returned no clip candidates.")
            clips = normalize_clips(clips, self.shorts_count, self.max_duration)
            self._write_json(self.analysis_dir / "clip_candidates.json", {"clips": clips})
            self.log(f"Local AI found {len(clips)} clip candidate(s).")
            return clips
        finally:
            if acquired:
                self.model_session_manager.release(self.model_name, owner)

    def _call_local_ai(self, prompt):
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "Return only valid JSON. Do not use markdown."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "repeat_penalty": 1.1,
            "max_tokens": 2500,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        response = requests.post("http://127.0.0.1:52625/v1/chat/completions", json=data, timeout=18000)
        if response.status_code != 200:
            raise RuntimeError(f"Local AI HTTP {response.status_code}: {response.text[:500]}")
        result = response.json()
        choices = result.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content") or choices[0].get("text")
            if content:
                return content.strip()
        raise RuntimeError("Local AI returned an empty response.")

    def _build_ai_prompt(self, transcript):
        schema = {
            "clips": [
                {
                    "clip_no": 1,
                    "start": "00:00:00",
                    "end": "00:00:00",
                    "duration_seconds": 0,
                    "score": 0,
                    "title": "",
                    "description": "",
                    "hashtags": ["", "", ""],
                    "reason": "",
                    "subtitles": [{"start": "00:00:00", "end": "00:00:00", "text": ""}],
                }
            ]
        }
        return (
            f"Find {self.shorts_count} short-form video candidates from this timestamped transcript.\n"
            f"Each clip must be at most {self.max_duration} seconds.\n"
            "Rules:\n"
            "- Each clip must make sense by itself.\n"
            "- The first 3 seconds should contain a hook or curiosity element.\n"
            "- Do not start or end in the middle of a sentence.\n"
            "- Generate Turkish title, description and hashtags.\n"
            "- If the transcript was translated from English, still write natural Turkish output.\n"
            "- Hashtags must not include the # sign.\n"
            "- Subtitles must be short, readable, and split into 1-2 line chunks.\n"
            "- Return only valid JSON matching this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
            f"Transcript:\n{transcript}"
        )

    def _render_selected_shorts(self):
        ffmpeg = self._find_tool("ffmpeg.exe", "ffmpeg")
        ffprobe = self._find_tool("ffprobe.exe", "ffprobe")
        video_path = self.source_dir / "source_video.mp4"
        if not video_path.exists():
            raise RuntimeError("source_video.mp4 not found.")
        clips = self._load_candidates()
        selected = self._select_clips(clips)
        if not selected:
            raise RuntimeError("No clip candidates selected.")
        errors = []

        for index, clip in enumerate(selected, start=1):
            self._check_cancelled()
            short_no = int(clip.get("clip_no") or index)
            short_dir = self.shorts_dir / f"short_{short_no:02d}"
            short_dir.mkdir(parents=True, exist_ok=True)
            video_out = short_dir / f"short_{short_no:02d}.mp4"
            ass_path = short_dir / f"short_{short_no:02d}.ass"
            render_log = short_dir / f"short_{short_no:02d}_render_log.txt"
            plan_path = short_dir / f"short_{short_no:02d}_clip_plan.json"
            self._write_json(plan_path, clip)

            vf_parts = [
                "scale=1080:1920:force_original_aspect_ratio=increase",
                "crop=1080:1920",
                "setsar=1",
            ]
            if STEP_SUBTITLES in self.selected_steps:
                create_ass_file(ass_path, clip)
                vf_parts.append(f"ass={ffmpeg_filter_path(ass_path)}")
            vf_parts.append("format=yuv420p")
            vf = ",".join(vf_parts)

            cmd = [
                ffmpeg,
                "-y",
                "-ss",
                str(clip.get("start", "00:00:00")),
                "-to",
                str(clip.get("end", "00:00:00")),
                "-i",
                str(video_path),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-profile:v",
                "high",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(video_out),
            ]
            try:
                output = self._run_command(cmd, allow_failure=True, step=STEP_RENDER)
                render_log.write_text(output, encoding="utf-8")
                if not video_out.exists():
                    raise RuntimeError(f"FFmpeg render failed for short_{short_no:02d}. See render log.")
                self._verify_rendered_short(video_out, ffprobe)
                self.log(f"Rendered: {video_out}")
            except Exception as exc:
                errors.append(f"short_{short_no:02d}: {exc}")
                if not render_log.exists() or not render_log.read_text(encoding="utf-8", errors="replace").strip():
                    render_log.write_text(str(exc), encoding="utf-8")
                self.log(f"ERROR rendering short_{short_no:02d}: {exc}")
                continue

        if errors and len(errors) == len(selected):
            raise RuntimeError("All renders failed: " + "; ".join(errors))
        if errors:
            self.step_results[STEP_RENDER] = "warning"
            self.log("WARNING: Some shorts failed to render: " + "; ".join(errors))

    def _verify_rendered_short(self, video_path, ffprobe):
        output = self._run_command([
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-print_format",
            "json",
            str(video_path),
        ], quiet_json=True)
        try:
            probe = json.loads(output)
        except Exception as exc:
            raise RuntimeError(f"Rendered file is not probeable: {video_path.name}") from exc

        streams = probe.get("streams") or []
        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
        audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
        if not video_stream:
            raise RuntimeError(f"Rendered file has no video stream: {video_path.name}")
        if video_stream.get("codec_name") != "h264":
            raise RuntimeError(f"Rendered video codec is not H.264: {video_stream.get('codec_name')}")
        if video_stream.get("pix_fmt") != "yuv420p":
            raise RuntimeError(f"Rendered video is not Windows-compatible 8-bit yuv420p: {video_stream.get('pix_fmt')}")
        if audio_stream and audio_stream.get("codec_name") != "aac":
            raise RuntimeError(f"Rendered audio codec is not AAC: {audio_stream.get('codec_name')}")

    def _write_metadata_for_selected(self):
        clips = self._load_candidates()
        selected = self._select_clips(clips)
        for index, clip in enumerate(selected, start=1):
            short_no = int(clip.get("clip_no") or index)
            short_dir = self.shorts_dir / f"short_{short_no:02d}"
            short_dir.mkdir(parents=True, exist_ok=True)
            metadata_path = short_dir / f"short_{short_no:02d}_metadata.txt"
            output_file = short_dir / f"short_{short_no:02d}.mp4"
            metadata_path.write_text(self._format_metadata(clip, output_file), encoding="utf-8")
            self.log(f"Metadata saved: {metadata_path}")

    def _format_metadata(self, clip, output_file):
        metadata_text = str(clip.get("metadata_text") or "").strip()
        if metadata_text:
            return (
                metadata_text
                + "\n\n"
                + f"Source URL: {self.url}\n"
                + f"Source video title: {self.source_title}\n"
                + f"Output file path: {output_file}\n"
                + f"Created date: {datetime.now().isoformat(timespec='seconds')}\n"
            )
        hashtags = clip.get("hashtags") or []
        if isinstance(hashtags, list):
            hashtags = ", ".join(str(x).lstrip("#") for x in hashtags)
        return (
            f"Title: {clip.get('title', '')}\n"
            f"Description: {clip.get('description', '')}\n"
            f"Hashtags: {hashtags}\n"
            f"Start: {clip.get('start', '')}\n"
            f"End: {clip.get('end', '')}\n"
            f"Duration: {clip.get('duration_seconds', '')}\n"
            f"Score: {clip.get('score', '')}\n"
            f"Reason: {clip.get('reason', '')}\n"
            f"Source URL: {self.url}\n"
            f"Source video title: {self.source_title}\n"
            f"Created date: {datetime.now().isoformat(timespec='seconds')}\n"
            f"Output file path: {output_file}\n"
        )

    def _load_candidates(self):
        data = self._read_json(self.analysis_dir / "clip_candidates.json", {})
        clips = data.get("clips", [])
        if not clips:
            raise RuntimeError("clip_candidates.json not found or empty.")
        return clips

    def _select_clips(self, clips):
        if self.selected_clip_nos:
            selected = [c for c in clips if int(c.get("clip_no", 0) or 0) in self.selected_clip_nos]
        else:
            selected = sorted(clips, key=lambda c: float(c.get("score", 0) or 0), reverse=True)[: self.shorts_count]
        return selected

    def _find_tool(self, bundled_name, path_name):
        bundled = self.root_dir / "tools" / bundled_name
        if bundled.exists():
            return str(bundled)
        found = shutil.which(path_name)
        if found:
            return found
        raise RuntimeError(f"{path_name} not found. Put {bundled_name} in tools/ or add it to PATH.")

    def _run_command(self, cmd, allow_failure=False, step=None, quiet_json=False):
        self.log("Running: " + " ".join(str(part) for part in cmd))
        self._check_cancelled()
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
            for line in proc.stdout:
                self._check_cancelled()
                line = line.rstrip()
                if not line:
                    continue
                lines.append(line)
                percent = parse_percent(line)
                if percent is not None and step:
                    self.progress(step, percent, compact_progress_line(line))
                if not quiet_json:
                    safe = sanitize_log_line(line)
                    if safe:
                        self.log(safe)
            proc.wait()
        finally:
            self.current_process = None

        output = "\n".join(lines).strip()
        if proc.returncode != 0 and not allow_failure:
            raise RuntimeError(summarize_command_error(output) or f"Command failed with exit code {proc.returncode}")
        return output

    def _normalize_output_file(self, stem, extension):
        wanted = self.source_dir / f"{stem}{extension}"
        if wanted.exists():
            return wanted
        matches = sorted(self.source_dir.glob(f"{stem}.*"))
        if matches:
            matches[0].replace(wanted)
            return wanted
        raise RuntimeError(f"{wanted.name} was not created.")

    def _remove_matching(self, pattern):
        for path in self.source_dir.glob(pattern):
            if path.is_file():
                path.unlink()

    def _first_matching_transcript(self):
        matches = sorted(self.source_dir.glob("transcript_raw*.srt"))
        if not matches:
            matches = sorted(self.source_dir.glob("transcript_raw*.vtt"))
        return matches[0] if matches else None

    def _unique_project_dir(self, slug, output_root):
        candidate = output_root / slug
        if not candidate.exists():
            return candidate
        i = 2
        while True:
            candidate = output_root / f"{slug}-{i}"
            if not candidate.exists():
                return candidate
            i += 1

    def _write_json(self, path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_json(self, path, default):
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return default


def slugify(text):
    normalized = unicodedata.normalize("NFKD", text or "youtube-video")
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    ascii_text = ascii_text.casefold()
    replacements = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}
    for old, new in replacements.items():
        ascii_text = ascii_text.replace(old, new)
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    ascii_text = ascii_text.strip("-")
    return ascii_text[:80] or "youtube-video"


def clean_text(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_chatgpt_translation_prompt(json_items):
    rows = []
    for index, item in enumerate(json_items, start=1):
        text = clean_text(item.get("text", ""))
        rows.append(f"{index}\t{item.get('start', '')}\t{item.get('end', '')}\t{text}")
    return (
        "Aşağıdaki İngilizce altyazı satırlarını Türkçe'ye çevir.\n"
        "Zaman kodlarını ve satır numaralarını aynen koru.\n"
        "Sadece TSV döndür, açıklama veya markdown yazma.\n"
        "Her satır formatı şu olsun:\n"
        "satir_no<TAB>start<TAB>end<TAB>turkce_metin\n\n"
        + "\n".join(rows)
    )


def apply_chatgpt_translation_response(source_dir, response_text):
    source_dir = Path(source_dir)
    english_json = source_dir / "transcript_clean_en.json"
    if not english_json.exists():
        english_json = source_dir / "transcript_clean.json"
    source_items = json.loads(english_json.read_text(encoding="utf-8", errors="replace"))
    parsed = parse_translation_response(response_text, source_items)
    if not parsed:
        raise RuntimeError("ChatGPT translation response could not be parsed.")

    txt_lines = [
        f"[{item['start']} - {item['end']}] {clean_text(item.get('text', ''))}"
        for item in parsed
        if clean_text(item.get("text", ""))
    ]
    (source_dir / "transcript_clean.txt").write_text("\n".join(txt_lines), encoding="utf-8")
    (source_dir / "transcript_clean.json").write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (source_dir / "transcript_translation_tr_chatgpt.json").write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return parsed


def build_chatgpt_studio_prompt(json_items, shorts_count=3, max_duration=60, video_info=None, search_ranges=None):
    video_info = video_info or {}
    ranges = parse_time_ranges(search_ranges)
    rows = []
    for index, item in enumerate(json_items, start=1):
        text = clean_text(item.get("text", ""))
        rows.append(f"{index}\t{item.get('start', '')}\t{item.get('end', '')}\t{text}")
    schema = {
        "transcript": [{"start": "00:00:00", "end": "00:00:00", "text": "Turkce altyazi satiri"}],
        "clips": [
            {
                "clip_no": 1,
                "start": "00:00:00",
                "end": "00:00:00",
                "duration_seconds": 0,
                "score": 0,
                "title": "Turkce baslik",
                "description": "Turkce aciklama",
                "hashtags": ["etiket1", "etiket2", "etiket3"],
                "reason": "Neden iyi bir shorts adayi oldugu",
                "metadata_text": "Title: ...\nDescription: ...\nHashtags: ...\nPinned comment: ...",
                "subtitles": [{"start": "00:00:00", "end": "00:00:00", "text": "Turkce kisa altyazi"}],
            }
        ],
    }
    range_text = ""
    if ranges:
        readable_ranges = ", ".join(f"{seconds_to_hms(start)} - {seconds_to_hms(end)}" for start, end in ranges)
        range_text = (
            f"\nZaman araligi kisiti aktif. Shorts adaylarini sadece su araliklarin icinden sec: {readable_ranges}.\n"
            "Klip start/end degerleri bu araliklarin disina tasmasin.\n"
        )
    return (
        "Asagidaki YouTube transcript satirlarini kullanarak iki isi birlikte yap:\n"
        "1. Transcript Ingilizce ise Turkce'ye cevir. Turkce ise metni dogal Turkce olarak temizle.\n"
        f"2. Bu transcript icinden {shorts_count} adet shorts adayi sec. Her klip en fazla {max_duration} saniye olsun.\n"
        "3. Her clip icin YouTube Shorts'a uygun metadata_text alanini tamamen sen uret.\n\n"
        + range_text
        + "Kurallar:\n"
        "- start/end zaman kodlarini HH:MM:SS formatinda koru.\n"
        "- Klipler kendi basina anlamli olsun, ilk 3 saniyede merak uyandirsin.\n"
        "- Cumlenin ortasinda baslatma veya bitirme.\n"
        "- title, description, reason, subtitles ve hashtags Turkce olsun.\n"
        "- hashtags icinde # isareti kullanma.\n"
        "- metadata_text yayinlamaya hazir TXT olsun; Title, Description, Hashtags, Pinned comment, Start, End alanlarini icersin.\n"
        "- Sadece gecerli JSON dondur. Markdown, aciklama, code fence yazma.\n"
        "- JSON semasi tam olarak su yapida olsun:\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        f"Video title: {video_info.get('title', '')}\n"
        f"Video URL: {video_info.get('webpage_url', '')}\n\n"
        "Transcript satirlari TSV formatinda:\n"
        "satir_no<TAB>start<TAB>end<TAB>metin\n"
        + "\n".join(rows)
    )


def apply_chatgpt_studio_response(source_dir, analysis_dir, response_text, shorts_count=3, max_duration=60, search_ranges=None):
    source_dir = Path(source_dir)
    analysis_dir = Path(analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    english_json = source_dir / "transcript_clean_en.json"
    if not english_json.exists():
        english_json = source_dir / "transcript_clean.json"
    source_items = json.loads(english_json.read_text(encoding="utf-8", errors="replace"))
    data = extract_json_object(response_text)

    transcript_data = data.get("transcript") or data.get("translations") or data.get("items") or data.get("entries")
    if not isinstance(transcript_data, list):
        raise RuntimeError("ChatGPT JSON must include a transcript array.")
    translated_items = normalize_transcript_items(transcript_data, source_items)
    if not translated_items:
        raise RuntimeError("ChatGPT transcript array could not be parsed.")

    clips = data.get("clips") or data.get("shorts") or data.get("candidates")
    if not isinstance(clips, list) or not clips:
        raise RuntimeError("ChatGPT JSON must include a non-empty clips array.")
    clips = normalize_clips(clips, int(shorts_count or 3), int(max_duration or 60), search_ranges=parse_time_ranges(search_ranges))
    if not clips:
        raise RuntimeError("ChatGPT clips array could not be normalized or clips are outside selected time ranges.")

    txt_lines = [
        f"[{item['start']} - {item['end']}] {clean_text(item.get('text', ''))}"
        for item in translated_items
        if clean_text(item.get("text", ""))
    ]
    (source_dir / "transcript_clean.txt").write_text("\n".join(txt_lines), encoding="utf-8")
    (source_dir / "transcript_clean.json").write_text(
        json.dumps(translated_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (source_dir / "transcript_translation_tr_chatgpt.json").write_text(
        json.dumps(translated_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (analysis_dir / "chatgpt_studio_result.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (analysis_dir / "clip_candidates.json").write_text(
        json.dumps({"clips": clips}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return translated_items, clips


def normalize_transcript_items(items, source_items):
    normalized = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        source = source_items[min(index, len(source_items) - 1)]
        text = clean_text(item.get("text", ""))
        if not text:
            continue
        normalized.append({
            "start": item.get("start") or source.get("start"),
            "end": item.get("end") or source.get("end"),
            "text": text,
        })
    return normalized


def parse_translation_response(content, source_items):
    try:
        data = extract_json_array(content)
        if isinstance(data, dict):
            data = data.get("items") or data.get("entries") or data.get("transcript") or data.get("translations")
        if isinstance(data, list):
            parsed = []
            for index, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                source = source_items[min(index, len(source_items) - 1)]
                parsed.append({
                    "start": item.get("start") or source.get("start"),
                    "end": item.get("end") or source.get("end"),
                    "text": clean_text(item.get("text", "")),
                })
            if parsed:
                return parsed
    except Exception:
        pass

    rows = []
    for line in (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip().strip("|")
        if not line or line.startswith("```"):
            continue
        if "\t" in line:
            parts = line.split("\t", 3)
        else:
            parts = [part.strip() for part in line.split("|", 3)]
        if len(parts) < 4:
            continue
        try:
            row_index = int(re.sub(r"\D", "", parts[0]) or "0") - 1
        except Exception:
            row_index = len(rows)
        if row_index < 0 or row_index >= len(source_items):
            row_index = len(rows)
        if row_index >= len(source_items):
            continue
        source = source_items[row_index]
        rows.append({
            "start": parts[1].strip() or source.get("start"),
            "end": parts[2].strip() or source.get("end"),
            "text": clean_text(parts[3]),
        })
    return rows


def parse_srt(content):
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").replace("\r", "\n"))
    entries = []
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 2:
            continue
        time_line = next((line for line in lines if "-->" in line), "")
        if not time_line:
            continue
        start, end = [part.strip().split(",")[0] for part in time_line.split("-->", 1)]
        text_lines = lines[lines.index(time_line) + 1 :]
        text = clean_text(" ".join(text_lines))
        if text:
            entries.append({"start": start, "end": end, "text": text})
    return entries


def parse_vtt(content):
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"^WEBVTT.*?\n\n", "", text, flags=re.DOTALL)
    blocks = re.split(r"\n\s*\n", text)
    entries = []
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        time_line = next((line for line in lines if "-->" in line), "")
        if not time_line:
            continue
        start, end = [part.strip().split(".")[0] for part in time_line.split("-->", 1)]
        text_lines = lines[lines.index(time_line) + 1 :]
        caption = clean_text(" ".join(text_lines))
        if caption:
            entries.append({"start": start, "end": end, "text": caption})
    return entries


def extract_json_object(content):
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return tolerant_json_loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return tolerant_json_loads(text[start : end + 1])
        raise


def extract_json_array(content):
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return tolerant_json_loads(text)
    except Exception:
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            return tolerant_json_loads(text[start : end + 1])
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return tolerant_json_loads(text[start : end + 1])
        raise


def tolerant_json_loads(text):
    try:
        return json.loads(text)
    except Exception:
        cleaned = re.sub(r",\s*([}\]])", r"\1", text)
        return json.loads(cleaned)


def normalize_clips(clips, count, max_duration, search_ranges=None):
    search_ranges = search_ranges or []
    normalized = []
    for index, clip in enumerate(clips[: max(count, len(clips))], start=1):
        if not isinstance(clip, dict):
            continue
        item = dict(clip)
        item["clip_no"] = int(item.get("clip_no") or index)
        item["duration_seconds"] = int(float(item.get("duration_seconds") or duration_between(item.get("start"), item.get("end")) or 0))
        if item["duration_seconds"] > max_duration:
            item["duration_seconds"] = max_duration
            item["end"] = seconds_to_hms(hms_to_seconds(item.get("start")) + max_duration)
        if item.get("metadata_text") is not None:
            item["metadata_text"] = str(item.get("metadata_text")).strip()
        item.setdefault("subtitles", [])
        if search_ranges and not clip_in_ranges(item, search_ranges):
            continue
        normalized.append(item)
    return normalized[:count]


def clip_in_ranges(clip, ranges):
    try:
        start = hms_to_seconds(clip.get("start"))
        end = hms_to_seconds(clip.get("end"))
    except Exception:
        return False
    return any(start >= range_start and end <= range_end for range_start, range_end in ranges)


def parse_time_ranges(text):
    ranges = []
    if not text:
        return ranges
    for raw_line in str(text).replace(",", "\n").replace(";", "\n").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = re.findall(r"\d{1,2}(?::\d{1,2}){1,2}", line)
        if len(parts) < 2:
            continue
        start = hms_to_seconds(parts[0])
        end = hms_to_seconds(parts[1])
        if end > start:
            ranges.append((start, end))
    return ranges


def duration_between(start, end):
    try:
        return max(0, hms_to_seconds(end) - hms_to_seconds(start))
    except Exception:
        return 0


def hms_to_seconds(value):
    parts = str(value or "0:0:0").split(":")
    parts = [float(part) for part in parts]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return int(parts[-3] * 3600 + parts[-2] * 60 + parts[-1])


def ffmpeg_filter_path(path):
    text = Path(path).resolve().as_posix()
    escaped = text.replace(":", "\\:").replace("'", "\\'")
    return f"'{escaped}'"


def create_ass_file(path, clip):
    subtitles = clip.get("subtitles") or []
    if not subtitles:
        subtitles = [{"start": "00:00:00", "end": str(clip.get("duration_seconds", 5)), "text": clip.get("title", "")}]
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H0000FFFF,&H0000FFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,5,0,2,80,80,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    clip_start_seconds = hms_to_seconds(clip.get("start", "00:00:00"))
    for subtitle in subtitles:
        start = max(0, hms_to_seconds(subtitle.get("start", "00:00:00")) - clip_start_seconds)
        end = max(start + 1, hms_to_seconds(subtitle.get("end", "00:00:02")) - clip_start_seconds)
        text = clean_text(str(subtitle.get("text", ""))).replace("\n", "\\N")
        lines.append(f"Dialogue: 0,{seconds_to_ass(start)},{seconds_to_ass(end)},Default,,0,0,0,,{text}\n")
    Path(path).write_text("".join(lines), encoding="utf-8")


def seconds_to_ass(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}.00"


def seconds_to_hms(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_percent(line):
    match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line or "")
    if not match:
        match = re.search(r"(\d+(?:\.\d+)?)%", line or "")
    if not match:
        return None
    try:
        return max(0, min(100, int(float(match.group(1)))))
    except Exception:
        return None


def compact_progress_line(line):
    line = sanitize_log_line(line)
    return line[:120] if line else ""


def sanitize_log_line(line):
    text = line or ""
    if text.lstrip().startswith("{") or '"formats"' in text or '"url"' in text:
        return ""
    text = re.sub(r"https?://\S+", "[url-hidden]", text)
    text = re.sub(r"([?&](?:sig|signature|token|expire|n|ei|ip|id)=[^&\s]+)", r"\1[hidden]", text, flags=re.I)
    if len(text) > 500:
        text = text[:500] + "..."
    return text


def summarize_command_error(output):
    lines = [sanitize_log_line(line) for line in (output or "").splitlines()]
    lines = [line for line in lines if line]
    important = [line for line in lines if "ERROR" in line.upper() or "WARNING" in line.upper() or "429" in line]
    selected = important[-5:] if important else lines[-5:]
    return "\n".join(selected)
