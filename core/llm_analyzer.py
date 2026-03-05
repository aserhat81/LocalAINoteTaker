import requests
from PySide6.QtCore import QThread, Signal


class LlmAnalyzerThread(QThread):
    analysis_ready = Signal(str, str)  # title, markdown_summary
    analysis_error = Signal(str)

    LANG_CONFIG = {
        "tr": {
            "system": "Sen profesyonel bir yönetici asistanı ve toplantı analiz uzmanısın. Tüm yanıtlarını TÜRKÇE ver.",
            "heading": "BAŞLIK",
            "default_title": "Genel Toplantı Özeti",
            "instructions": (
                "Aşağıdaki toplantı transkriptini incele ve TÜRKÇE olarak yanıt ver:\n\n"
                "1) Toplantının ana konusunu (örn: 'Q1 Satış Planlaması', 'Ürün Geliştirme Toplantısı') "
                "'BAŞLIK: [Konu]' formatıyla EN BAŞA yaz. Başlık kısa ve açıklayıcı olmalı.\n\n"
                "2) ## Özet\n"
                "   Profesyonel bir yönetici özeti yaz. Kimin ne söylediğini ve alınan kararları belirt.\n\n"
                "3) ## Gündem Maddeleri (Meeting Minutes)\n"
                "   Toplantıda ele alınan ana konuları madde madde listele (çok detaylı olmadan):\n"
                "   - Her madde bir konu başlığı olsun\n"
                "   - Varsa alınan karar veya eylem maddesi belirt\n"
                "   - Sorumlu kişi varsa ekle\n\n"
                "4) ## Eylem Maddeleri\n"
                "   Toplantıdan çıkan yapılacaklar listesini yaz."
            )
        },
        "en": {
            "system": "You are a professional executive assistant and meeting analysis expert. Always respond in ENGLISH.",
            "heading": "TITLE",
            "default_title": "General Meeting Summary",
            "instructions": (
                "Analyze the following meeting transcript and respond in ENGLISH:\n\n"
                "1) Write the main topic (e.g. 'Q1 Sales Planning', 'Product Dev Review') "
                "as 'TITLE: [Topic]' at the very top. Keep it short and descriptive.\n\n"
                "2) ## Summary\n"
                "   Write a professional executive summary. Note who said what and decisions made.\n\n"
                "3) ## Meeting Minutes\n"
                "   List the main topics discussed as bullet points (not overly detailed):\n"
                "   - Each item should be a topic header\n"
                "   - Include any decisions or action items if applicable\n"
                "   - Include responsible person if mentioned\n\n"
                "4) ## Action Items\n"
                "   List the to-do items that came out of the meeting."
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

                # Başlığı ayıkla
                title = cfg["default_title"]
                lines = content.split('\n')
                heading_key = cfg["heading"] + ":"
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.upper().startswith(heading_key):
                        extracted = stripped.split(":", 1)[1].strip()
                        if extracted:  # Gerçekten bir başlık bulunduysa kullan
                            title = extracted
                        lines.pop(i)
                        break

                summary_body = '\n'.join(lines).strip()
                self.analysis_ready.emit(title, summary_body)
            else:
                self.analysis_error.emit(f"LLM API Hatası: {response.text}")
        except Exception as e:
            self.analysis_error.emit(f"Analiz Hatası: {str(e)}")
