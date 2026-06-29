import os
import tempfile
import threading
import unicodedata

import requests
from PySide6.QtCore import QThread, Signal


class FasterWhisperModelCache:
    _lock = threading.RLock()
    _models = {}

    @classmethod
    def get_model(cls, model_name):
        model_name = (model_name or "small").strip() or "small"
        with cls._lock:
            if model_name in cls._models:
                return cls._models[model_name]

            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "faster-whisper is not installed. Run setup again or install faster-whisper."
                ) from exc

            try:
                model = WhisperModel(model_name, device="auto", compute_type="default")
            except Exception:
                model = WhisperModel(model_name, device="cpu", compute_type="int8")

            cls._models[model_name] = model
            return model


class AsrClientThread(QThread):
    transcription_ready = Signal(str, str)  # text, source_label
    transcription_error = Signal(str)

    HALLUCINATIONS = [
        "...",
        "Altyazi",
        "Amara.org",
        "by Amara.org",
        "E ai",
        "E ai.",
        "Subtitles by",
        "Translated by",
        "www.subtitle-tools.com",
    ]

    def __init__(
        self,
        wav_bytes,
        source_label,
        language="tr",
        provider="flm",
        whisper_model="small",
    ):
        super().__init__()
        self.wav_bytes = wav_bytes
        self.source_label = source_label
        self.language = language
        self.provider = (provider or "flm").strip().lower()
        self.whisper_model = (whisper_model or "small").strip() or "small"
        self.api_url = "http://127.0.0.1:52625/v1/audio/transcriptions"

    def _normalize_text(self, text):
        return "".join(
            c for c in unicodedata.normalize("NFKD", text.casefold())
            if not unicodedata.combining(c)
        )

    def is_hallucination(self, text):
        t = text.strip()
        clean = t.replace(".", "").replace(" ", "").replace("\n", "")
        if not clean:
            return True

        if any("\u0400" <= c <= "\u04FF" for c in t):
            return True

        normalized = self._normalize_text(t)
        if normalized.startswith("e ai") or normalized.count("e ai") >= 2:
            return True

        words = [self._normalize_text(w.strip(".,!?")) for w in t.split() if w.strip(".,!?")]
        if len(words) >= 3 and len(set(words)) == 1 and words[0] in ["okay", "ok", "tamam"]:
            return True

        for hallucination in self.HALLUCINATIONS:
            if normalized == self._normalize_text(hallucination):
                return True

        return False

    def run(self):
        if self.provider == "faster_whisper":
            self._run_faster_whisper()
            return

        self._run_flm()

    def _run_flm(self):
        try:
            files = {
                "file": ("chunk.wav", self.wav_bytes, "audio/wav")
            }
            data = {
                "model": "whisper-v3:turbo",
                "response_format": "json",
                "language": self.language,
            }

            response = requests.post(self.api_url, files=files, data=data, timeout=18000)
            if response.status_code == 200:
                result = response.json()
                text = result.get("text", "").strip()
                if text and not self.is_hallucination(text):
                    self.transcription_ready.emit(text, self.source_label)
            else:
                self.transcription_error.emit(f"FLM API Hatasi: {response.status_code}")

        except requests.exceptions.Timeout:
            self.transcription_error.emit("FLM ASR zaman asimi! NPU cok yogun olabilir.")
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            self.transcription_error.emit(f"ASR Hatasi: {str(e)}")

    def _run_faster_whisper(self):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(self.wav_bytes)
                temp_path = tmp.name

            model = FasterWhisperModelCache.get_model(self.whisper_model)
            segments, _ = model.transcribe(
                temp_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            if text and not self.is_hallucination(text):
                self.transcription_ready.emit(text, self.source_label)

        except Exception as e:
            self.transcription_error.emit(f"Whisper ASR Hatasi: {str(e)}")
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
