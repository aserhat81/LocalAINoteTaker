import requests
from PySide6.QtCore import QThread, Signal

class AsrClientThread(QThread):
    transcription_ready = Signal(str, str) # text, source_label ("BEN" or "DİĞER")
    transcription_error = Signal(str)

    # Whisper boşluk/sessizlik halüsinasyonları — genişletildi
    HALLUCINATIONS = [
        "...", "Thank you", "Okay", "Okay.", "ok.", "Teşekkürler", "Altyazı",
        "Amara.org", "by Amara.org", "Thank you.", "Thanks.", "You're welcome.",
        "Sağ olun.", "Görüşmek üzere.", "E aí", "E aí.", "Продолжение следует",
        "Subtitrare realizată de", "Vă mulțumesc", "продолжение следует",
        "www.subtitle-tools.com", "Subtitles by", "Translated by",
    ]

    def __init__(self, wav_bytes, source_label, language="tr"):
        super().__init__()
        self.wav_bytes = wav_bytes
        self.source_label = source_label
        self.language = language
        self.api_url = "http://127.0.0.1:52625/v1/audio/transcriptions"

    def is_hallucination(self, text):
        t = text.strip()
        clean = t.replace(".", "").replace(" ", "").replace("\n", "")
        if not clean:
            return True
        # Kiril alfabesi içeriyorsa (Rusça halüsinasyon) filtrele
        if any('\u0400' <= c <= '\u04FF' for c in t):
            return True
        # Portekizce "E aí" tekrarı
        if t.startswith("E aí") or t.count("E aí") >= 2:
            return True
        # Tek kelime tekrarı
        words = set(w.strip(".,!?").lower() for w in t.split())
        if len(words) == 1 and list(words)[0] in ["okay", "ok", "thank", "thanks"]:
            return True
        for h in self.HALLUCINATIONS:
            if t == h or t == h + ".":
                return True
        return False

    def run(self):
        try:
            files = {
                'file': ('chunk.wav', self.wav_bytes, 'audio/wav')
            }
            data = {
                'model': 'whisper-v3:turbo',  # FLM model adı (whisper-large-v3-turbo)
                'response_format': 'json',
                'language': self.language,
            }
            
            response = requests.post(self.api_url, files=files, data=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                text = result.get('text', '').strip()
                if text and not self.is_hallucination(text): 
                    self.transcription_ready.emit(text, self.source_label)
            else:
                self.transcription_error.emit(f"FLM API Hatası: {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.transcription_error.emit("FLM ASR Zaman Aşımı! NPU çok yoğun olabilir.")
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            self.transcription_error.emit(f"ASR Hatası: {str(e)}")
