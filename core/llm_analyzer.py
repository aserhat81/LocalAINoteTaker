import requests
from PySide6.QtCore import QThread, Signal


class LlmAnalyzerThread(QThread):
    analysis_ready = Signal(str, str, str)  # title, participants, markdown_summary
    analysis_error = Signal(str)
    analysis_progress = Signal(str)

    MODEL_NAME = "qwen3:8b"  # Aktif model — buradan değiştirince her yerde güncellenir
    LANG_CONFIG = {
        "tr": {
            "system": (
                "Sen profesyonel bir toplantı analiz uzmanı ve yönetici asistanısın. "
                "Görevin transkriptteki TÜM konuları eksiksiz yakalamak ve yapılandırılmış bir rapor üretmektir. "
                "Transkriptte Whisper kaynaklı fonetik hatalar veya yarım kalmış cümleler olabilir; "
                "bunları toplantı bağlamından yola çıkarak düzelterek genel anlamı doğru tahmin et. "
                "Tüm yanıtlarını TÜRKÇE ver."
            ),
            "heading": "BAŞLIK",
            "default_title": "Genel Toplantı Özeti",
            "instructions": (
                "Aşağıdaki toplantı transkriptini dikkatle oku. Whisper kaynaklı bozuk veya eksik cümleleri "
                "bağlamı kullanarak düzelt, sonra aşağıdaki yapıya göre TÜRKÇE analiz yap.\n\n"
                "BAŞLIK: [Kısa ve açıklayıcı başlık]\n"
                "KATILIMCILAR: İsim1, İsim2  "
                "(Sadece gerçek insan isimleri. Ürün, şirket, teknoloji ismi KESİNLİKLE dahil etme. "
                "Emin değilsen boş bırak.)\n\n"
                "## Yönetici Özeti\n"
                "Toplantının ana amacını, en kritik karar ve çıktıları kısaca (3-6 cümle) anlat.\n\n"
                "## Toplantı Özeti\n"
                "Toplantıda konuşulan tüm konuları daha geniş biçimde ve kimin ne söylediği dahil detaylı anlat. "
                "Hiçbir konuyu atlamadan kapsamlı bir şekilde yaz.\n\n"
                "## Alınan Kararlar\n"
                "Toplantıda kesinleştirilen kararları madde madde listele. "
                "Karar yoksa 'Bu toplantıda kesinleştirilmiş bir karar bulunmamaktadır.' yaz.\n\n"
                "## Toplantı Kısa Notları (Meeting Minutes)\n"
                "Kronolojik sırayla toplantının akışını, kimin ne zaman ne söylediğini ve varsa eylem maddelerini yaz. "
                "Eylem maddelerini '- **[Kim]:** [Yapılacak iş]' formatıyla listele.\n\n"
                "UYARI: Yukarıdaki 4 bölümü mutlaka doldur. "
                "Transkriptteki her konuyu 'Toplantı Özeti' ve 'Toplantı Kısa Notları' bölümlerine yansıt."
            ),
            "intermediate": (
                "Aşağıda bir uzun toplantının BİR KISMINA ait transkript var. "
                "Whisper kaynaklı fonetik hataları bağlamdan düzelterek, "
                "bu kısımdaki konuşmaları kayıpsız biçimde maddeler halinde özetle:\n"
                "- Konuşan kişilerin isimleri/etiketleri\n"
                "- Konuşulan tüm detaylı konular ve tartışmalar\n"
                "- Varsa alınan kararlar veya eylem maddeleri\n\n"
                "Transkript Kısmı:\n"
            )
        },
        "en": {
            "system": (
                "You are a professional meeting analyst and executive assistant. "
                "Your job is to capture ALL topics from the transcript without exception and produce a structured report. "
                "The transcript may contain Whisper-induced phonetic errors or incomplete sentences; "
                "use meeting context to correct these and infer the intended meaning before analyzing. "
                "Always respond in ENGLISH."
            ),
            "heading": "TITLE",
            "default_title": "General Meeting Summary",
            "instructions": (
                "Read the following meeting transcript carefully. Correct any Whisper-induced phonetic errors or "
                "incomplete sentences using context, then produce an ENGLISH analysis with the structure below.\n\n"
                "TITLE: [Short descriptive title]\n"
                "PARTICIPANTS: Name1, Name2  "
                "(Real human names ONLY. No products, companies, or technologies. If unsure, leave blank.)\n\n"
                "## Executive Summary\n"
                "Describe the main purpose of the meeting and the most critical decisions/outcomes in 3-6 sentences.\n\n"
                "## Meeting Overview\n"
                "Cover ALL topics discussed in detail, including who said what. Be comprehensive — miss nothing.\n\n"
                "## Decisions Made\n"
                "List every decision that was finalized. If none, write 'No decisions were finalized in this meeting.'\n\n"
                "## Meeting Minutes\n"
                "In chronological order, note who said what and any action items. "
                "Format action items as: '- **[Person]:** [Task]'\n\n"
                "WARNING: All 4 sections above must be filled in. "
                "Every topic in the transcript MUST appear in 'Meeting Overview' and 'Meeting Minutes'."
            ),
            "intermediate": (
                "Below is a PART of a long meeting transcript. "
                "Correct any Whisper-induced phonetic errors using context, then "
                "summarize this section in detail without losing information, using bullet points:\n"
                "- Participant names/labels\n"
                "- All detailed topics and discussions\n"
                "- Any decisions or action items\n\n"
                "Transcript Part:\n"
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
        
        # Eğer çok uzunsa (yaklaşık 3000 token / 12000 karaktere denk), parçalara böl (Map-Reduce)
        MAX_CHARS = 12000
        
        try:
            if len(self.transcript) <= MAX_CHARS:
                # Kısa/Orta toplantı - Tek seferde analiz (Eski Yöntem)
                final_text = self.transcript
            else:
                # Uzun Toplantı - Parçalara bölerek analiz
                self.analysis_progress.emit("Uzun toplantı tespit edildi. Metin parçalara bölünerek analiz ediliyor (bu işlem normalden uzun sürecektir)...")
                
                chunks = self._split_transcript(self.transcript, MAX_CHARS)
                intermediate_summaries = []
                
                for i, chunk in enumerate(chunks):
                    # Ara özet çıkart
                    self.analysis_progress.emit(f"Parça {i+1}/{len(chunks)} özetleniyor...")
                    intermediate_prompt = cfg["intermediate"] + chunk
                    chunk_summary = self._call_llm(
                        system_prompt="Sen parçalı transkriptleri analiz eden bir asistansın. Her detayı koru." if self.language == "tr" else "You are an assistant that analyzes transcript parts. Keep every detail.", 
                        user_prompt=intermediate_prompt,
                        max_tokens=2048
                    )
                    intermediate_summaries.append(f"--- BÖLÜM {i+1} ÖZETİ ---\n{chunk_summary}\n")
                
                # Birleştirilmiş metni final prompt'a sokmak üzere hazırla
                final_text = "DİKKAT: Aşağıdaki metin doğrudan transkript değil, transkriptin farklı bölümlerinden çıkarılmış detaylı ara özetlerin birleşimidir.\n\n" + "\n".join(intermediate_summaries)
                self.analysis_progress.emit("Ara özetler birleştiriliyor. Final tablo hazırlanıyor...")

            # Final Analizi yap (İster doğrudan transkript, ister birleştirilmiş ara özetler)
            prompt = f"{cfg['instructions']}\n\nToplantı Verisi:\n{final_text}"
            content = self._call_llm(cfg["system"], prompt, max_tokens=3072)

            self._parse_and_emit(content, cfg)

        except Exception as e:
            self.analysis_error.emit(f"Analiz Hatası: {str(e)}")

    def _split_transcript(self, text, max_len):
        """Metni max_len karakteri aşmayacak şekilde satır bazlı veya kırparak böler."""
        lines = text.split('\n')
        chunks = []
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_len:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = line + "\n"
                else: # Tek bir satır bile çok uzunsa
                    chunks.append(line[:max_len])
                    current_chunk = line[max_len:] + "\n"
            else:
                current_chunk += line + "\n"
                
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        return chunks

    def _call_llm(self, system_prompt, user_prompt, max_tokens):
        """API çağrısını yapar ve sadece yanıt stringini döner."""
        data = {
            "model": self.MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            "temperature": 0.2,
            "repeat_penalty": 1.15,
            "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False}
        }
        response = requests.post(self.api_url, json=data, timeout=18000)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

    def _parse_and_emit(self, content, cfg):
        # Başlığı ve Katılımcıları ayıkla
        title = cfg["default_title"]
        participants_str = ""
        lines = content.split('\n')
        heading_key = cfg["heading"] + ":"
        participants_key = "KATILIMCILAR:" if self.language == "tr" else "PARTICIPANTS:"
        
        final_lines = []
        for line in lines:
            stripped = line.strip()
            # Markdown kalın tag'lerini (**) ve heading tag'lerini (###) görmezden gelmek için temizle
            clean_line = stripped.replace("**", "").replace("*", "").replace("#", "").strip()
            
            if clean_line.upper().startswith(heading_key):
                extracted = clean_line.split(":", 1)[1].strip()
                if extracted:
                    title = extracted
            elif clean_line.upper().startswith(participants_key):
                extracted = clean_line.split(":", 1)[1].strip()
                if extracted:
                    participants_str = extracted
            else:
                final_lines.append(line)

        summary_body = '\n'.join(final_lines).strip()
        self.analysis_ready.emit(title, participants_str, summary_body)
