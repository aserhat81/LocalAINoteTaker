import requests
from PySide6.QtCore import QThread, Signal


class LlmAnalyzerThread(QThread):
    analysis_ready = Signal(str, str)  # title, markdown_summary
    analysis_error = Signal(str)

    # Desteklenen dil konfigürasyonları
    LANG_CONFIG = {
        "tr": {
            "system": "Sen profesyonel bir yönetici asistanı ve toplantı analiz uzmanısın. Tüm yanıtlarını TÜRKÇE ver.",
            "heading": "BAŞLIK",
            "default_title": "Genel Toplantı Özeti",
            "instructions": (
                "Aşağıdaki toplantı transkriptini incele ve TÜRKÇE olarak yanıt ver:\n"
                "1) Toplantının ana konusunu 'BAŞLIK: [Konu]' formatıyla en başa yaz.\n"
                "2) Profesyonel, formatlı bir yönetici özeti çıkart.\n"
                "3) Alınan kararları veya yapılacak işleri (Eylem Maddeleri) listele.\n"
                "4) Katılımcı isimlerini ayrıştır ve mümkünse kimin ne söylediğini belirt."
            )
        },
        "en": {
            "system": "You are a professional executive assistant and meeting analysis expert. Always respond in ENGLISH.",
            "heading": "TITLE",
            "default_title": "General Meeting Summary",
            "instructions": (
                "Analyze the following meeting transcript and respond in ENGLISH:\n"
                "1) Write the main topic as 'TITLE: [Topic]' at the very top.\n"
                "2) Write a professional, formatted executive summary.\n"
                "3) List decisions made or action items.\n"
                "4) Identify participant names and attribute statements where possible."
            )
        }
    }

    def __init__(self, transcript, language="tr"):
        super().__init__()
        self.transcript = transcript
        self.language = language if language in self.LANG_CONFIG else "tr"
        self.api_url = "http://127.0.0.1:52625/v1/chat/completions"

    def run(self):
        cfg = self.LANG_CONFIG[self.language]
        prompt = f"{cfg['instructions']}\n\nToplantı Transkripti:\n{self.transcript}"

        try:
            data = {
                "model": "gemma3:4b",
                "messages": [
                    {"role": "system", "content": cfg["system"]},
                    {"role": "user",   "content": prompt}
                ],
                "temperature": 0.3
            }
            response = requests.post(self.api_url, json=data, timeout=180)
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']

                title = cfg["default_title"]
                lines = content.split('\n')

                heading_key = cfg["heading"] + ":"
                for i, line in enumerate(lines):
                    if heading_key in line.upper():
                        title = line.split(":", 1)[1].strip()
                        lines.pop(i)
                        break

                summary_body = '\n'.join(lines).strip()
                self.analysis_ready.emit(title, summary_body)
            else:
                self.analysis_error.emit(f"LLM API Hatası: {response.text}")
        except Exception as e:
            self.analysis_error.emit(f"Analiz Hatası: {str(e)}")
