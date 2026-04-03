import unicodedata

import requests
from PySide6.QtCore import QThread, Signal


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

    def __init__(self, wav_bytes, source_label, language="tr"):
        super().__init__()
        self.wav_bytes = wav_bytes
        self.source_label = source_label
        self.language = language
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
            if normalized == hallucination.casefold():
                return True

        return False

    def run(self):
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
