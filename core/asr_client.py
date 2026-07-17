import gc
import os
import tempfile
import threading
import unicodedata
import wave

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

    @classmethod
    def is_loaded(cls, model_name):
        model_name = (model_name or "small").strip() or "small"
        with cls._lock:
            return model_name in cls._models

    @classmethod
    def unload_model(cls, model_name=None):
        """Release cached Whisper model objects and their accelerator memory."""
        with cls._lock:
            if model_name:
                normalized_name = model_name.strip() or "small"
                models = [cls._models.pop(normalized_name, None)]
            else:
                models = list(cls._models.values())
                cls._models.clear()

            released = 0
            for model in models:
                if model is None:
                    continue
                backend = getattr(model, "model", None)
                unload = getattr(backend, "unload_model", None)
                if callable(unload):
                    try:
                        unload()
                    except Exception:
                        # Dropping the final Python reference still releases the model.
                        pass
                released += 1
            unload = None
            backend = None
            model = None
            models.clear()

        gc.collect()
        return released


class WhisperModelLifecycleThread(QThread):
    """Load or unload a faster-whisper model without blocking the UI thread."""

    def __init__(self, action, model_name, parent=None):
        super().__init__(parent)
        self.action = action
        self.model_name = (model_name or "small").strip() or "small"
        self.success = False
        self.error_message = ""

    def run(self):
        try:
            if self.action == "load":
                FasterWhisperModelCache.get_model(self.model_name)
            elif self.action == "unload":
                FasterWhisperModelCache.unload_model(self.model_name)
            else:
                raise ValueError(f"Unknown Whisper lifecycle action: {self.action}")
            self.success = True
        except Exception as exc:
            self.error_message = str(exc)


class PyannotePipelineCache:
    """Load the local pyannote pipeline once and serialize inference calls."""

    MODEL_ID = "pyannote/speaker-diarization-community-1"
    _lock = threading.RLock()
    _pipeline = None

    @classmethod
    def get_pipeline(cls):
        with cls._lock:
            if cls._pipeline is not None:
                return cls._pipeline

            try:
                import torch
                from pyannote.audio import Pipeline
            except ImportError as exc:
                raise RuntimeError(
                    "pyannote.audio is not installed. Install the optional diarization dependencies."
                ) from exc

            token = (
                os.environ.get("HF_TOKEN")
                or os.environ.get("HUGGINGFACE_ACCESS_TOKEN")
                or None
            )
            try:
                pipeline = Pipeline.from_pretrained(cls.MODEL_ID, token=token)
            except Exception as exc:
                raise RuntimeError(
                    "Pyannote modeli yuklenemedi. Hugging Face uzerinde "
                    "pyannote/speaker-diarization-community-1 kosullarini kabul edin ve "
                    "HF_TOKEN ortam degiskenini ayarlayin (veya `hf auth login` calistirin)."
                ) from exc

            if torch.cuda.is_available():
                pipeline.to(torch.device("cuda"))

            cls._pipeline = pipeline
            return pipeline


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
        if self.provider in ("faster_whisper", "whisper_v3"):
            if self.provider == "whisper_v3":
                self.whisper_model = "large-v3"
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


class DiarizedTranscriptionThread(QThread):
    """Re-transcribe all meeting chunks and align words with pyannote speakers."""

    transcription_ready = Signal(str)
    transcription_error = Signal(str)
    progress = Signal(str)

    TARGET_SAMPLE_RATE = 16000
    CHUNK_GAP_SECONDS = 0.25

    def __init__(self, audio_chunks, language="tr", whisper_model="large-v3"):
        super().__init__()
        self.audio_chunks = list(audio_chunks or [])
        self.language = language
        self.whisper_model = (whisper_model or "large-v3").strip() or "large-v3"

    def run(self):
        temp_path = None
        try:
            if not self.audio_chunks:
                raise RuntimeError("Diarization icin ses parcasi bulunamadi.")

            self.progress.emit("Ses parcalari diarization icin birlestiriliyor...")
            temp_path, source_intervals = self._write_combined_audio(self.audio_chunks)

            self.progress.emit("Pyannote konusmacilari ayiriyor...")
            pipeline = PyannotePipelineCache.get_pipeline()
            with PyannotePipelineCache._lock:
                output = pipeline(temp_path)
            speaker_turns = self._extract_speaker_turns(output)

            self.progress.emit(
                f"Whisper ({self.whisper_model}) konusmayi zaman damgalariyla yaziyor..."
            )
            model = FasterWhisperModelCache.get_model(self.whisper_model)
            segments, _ = model.transcribe(
                temp_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,
                word_timestamps=True,
                condition_on_previous_text=True,
            )
            transcript = self._align_transcript(segments, speaker_turns, source_intervals)
            if not transcript.strip():
                raise RuntimeError("Whisper diarization sonrasi metin uretemedi.")
            self.transcription_ready.emit(transcript)
        except Exception as exc:
            self.transcription_error.emit(f"Pyannote diarization hatasi: {exc}")
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    @classmethod
    def _write_combined_audio(cls, audio_chunks):
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("Diarization icin numpy kurulu olmali.") from exc

        combined = []
        source_intervals = []
        cursor_seconds = 0.0
        gap = np.zeros(int(cls.TARGET_SAMPLE_RATE * cls.CHUNK_GAP_SECONDS), dtype=np.int16)

        for wav_bytes, source_label in audio_chunks:
            samples, sample_rate = cls._read_wav_mono(wav_bytes, np)
            if samples.size == 0:
                continue
            if sample_rate != cls.TARGET_SAMPLE_RATE:
                target_length = max(1, round(samples.size * cls.TARGET_SAMPLE_RATE / sample_rate))
                old_axis = np.linspace(0.0, 1.0, num=samples.size, endpoint=False)
                new_axis = np.linspace(0.0, 1.0, num=target_length, endpoint=False)
                samples = np.interp(new_axis, old_axis, samples).astype(np.int16)

            start = cursor_seconds
            end = start + (samples.size / cls.TARGET_SAMPLE_RATE)
            combined.append(samples)
            source_intervals.append((start, end, source_label))
            combined.append(gap)
            cursor_seconds = end + cls.CHUNK_GAP_SECONDS

        if not combined:
            raise RuntimeError("Birlestirilebilecek gecerli bir ses parcasi bulunamadi.")

        audio = np.concatenate(combined)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_path = temp_file.name
        temp_file.close()
        with wave.open(temp_path, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(cls.TARGET_SAMPLE_RATE)
            output.writeframes(audio.astype("<i2", copy=False).tobytes())
        return temp_path, source_intervals

    @staticmethod
    def _read_wav_mono(wav_bytes, np):
        import io

        with wave.open(io.BytesIO(wav_bytes), "rb") as source:
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frames = source.readframes(source.getnframes())

        if sample_width != 2:
            raise RuntimeError("Yalnizca 16-bit PCM WAV sesleri destekleniyor.")
        samples = np.frombuffer(frames, dtype="<i2")
        if channels > 1:
            usable = samples[: samples.size - (samples.size % channels)]
            samples = usable.reshape(-1, channels).astype(np.int32).mean(axis=1).astype(np.int16)
        return samples, sample_rate

    @staticmethod
    def _extract_speaker_turns(output):
        diarization = getattr(output, "exclusive_speaker_diarization", None)
        if diarization is None:
            diarization = getattr(output, "speaker_diarization", None)
        if diarization is None:
            diarization = output
        turns = []
        if hasattr(diarization, "itertracks"):
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                turns.append((float(turn.start), float(turn.end), str(speaker)))
        else:
            for item in diarization:
                if len(item) == 2:
                    turn, speaker = item
                elif len(item) == 3:
                    turn, _, speaker = item
                else:
                    continue
                turns.append((float(turn.start), float(turn.end), str(speaker)))
        return turns

    @classmethod
    def _align_transcript(cls, segments, speaker_turns, source_intervals):
        lines = []
        current_speaker = None
        current_words = []

        def flush():
            if current_words:
                text = " ".join(current_words).strip()
                if text:
                    lines.append(f"[{current_speaker}]: {text}")

        for segment in segments:
            words = list(getattr(segment, "words", None) or [])
            if not words:
                words = [segment]
            for word in words:
                text = str(getattr(word, "word", None) or getattr(word, "text", "")).strip()
                if not text:
                    continue
                start = float(getattr(word, "start", getattr(segment, "start", 0.0)) or 0.0)
                end = float(getattr(word, "end", getattr(segment, "end", start)) or start)
                speaker = cls._speaker_for_interval(start, end, speaker_turns, source_intervals)
                if speaker != current_speaker:
                    flush()
                    current_words = []
                    current_speaker = speaker
                current_words.append(text)
        flush()
        return "\n".join(lines).strip()

    @staticmethod
    def _speaker_for_interval(start, end, speaker_turns, source_intervals):
        midpoint = (start + end) / 2.0
        for source_start, source_end, source_label in source_intervals:
            if source_start <= midpoint <= source_end and source_label == "BEN":
                return "BEN"

        best_speaker = "SPEAKER_UNKNOWN"
        best_overlap = 0.0
        for turn_start, turn_end, speaker in speaker_turns:
            overlap = max(0.0, min(end, turn_end) - max(start, turn_start))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = speaker
        if best_overlap > 0:
            return best_speaker

        nearest = min(
            speaker_turns,
            key=lambda turn: min(abs(midpoint - turn[0]), abs(midpoint - turn[1])),
            default=None,
        )
        return nearest[2] if nearest else best_speaker
