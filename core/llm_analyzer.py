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
                "Görevin transkriptteki TÜM konuları eksiksiz yakalamaktır. "
                "Hiçbir konuyu, ne kadar kısa süre konuşulmuş olursa olsun atlama. "
                "Tüm yanıtlarını TÜRKÇE ver."
            ),
            "heading": "BAŞLIK",
            "default_title": "Genel Toplantı Özeti",
            "instructions": (
                "Aşağıdaki toplantı transkriptini satır satır dikkatle oku ve TÜRKÇE olarak yanıt ver.\n\n"
                "1) Toplantının genel konusunu 'BAŞLIK: [Başlık]' formatıyla EN BAŞA yaz. "
                "Kısa ve açıklayıcı olsun.\n\n"
                "2) Toplantıya katılan HAKİKİ KİŞİLERİN (insanların) isimlerini 'KATILIMCILAR: İsim 1, İsim 2' "
                "formatıyla hemen başlığın altına TEK SATIRDA, aralarına SADECE VİRGÜL koyarak yaz. "
                "Ürün, teknoloji veya şirket isimlerini (örn: Genesys, Cloud, AWS vb.) kesinlikle katılımcı olarak yazma. "
                "İsimlerin yanına unvan veya açıklama (örn: Ana konuşmacı, Çalışan) EKLEME. "
                "Katılımcıları özette metin içinde ayrıca LİSTELEME.\n\n"
                "3) ## Yönetici Özeti\n"
                "   Toplantıda ne konuşulduğunu, kimin ne söylediğini ve alınan kararları "
                "kısa ama kapsamlı şekilde anlat. Sadece en çok konuşulan konuya odaklanma; "
                "kısa süre konuşulan ya da geçici söz edilen konuları da mutlaka dahil et.\n\n"
                "4) ## Gündem Maddeleri\n"
                "   Transkriptte geçen HER konuyu ayrı madde olarak listele.\n"
                "   Önemli/az önemli ayrımı yapma — geçen her konuyu yaz.\n"
                "   Format: - **Konu Başlığı**: kısa açıklama (karar/eylem varsa belirt)\n\n"
                "5) ## Eylem Maddeleri\n"
                "   Toplantıdan çıkan yapılacaklar listesini yaz. Hiç yapılacak maddesi yoksa "
                "'Bu toplantıda belirlenmiş eylem maddesi yoktur.' yaz.\n\n"
                "UYARI: Transkripte hiç bakmadan özet sıkıştırma! "
                "Transkriptteki her konuyu mutlaka Madde 3 ve Madde 4'e yansıt."
            ),
            "intermediate": (
                "Aşağıda bir uzun toplantının BİR KISMINA ait transkript vardır.\n"
                "Lütfen sadece bu kısımdaki konuşmaları kayıpsız bir şekilde maddeler halinde özetle:\n"
                "- Katılımcı isimleri/etiketleri\n"
                "- Konuşulan tüm detaylı konular ve tartışmalar\n"
                "- Varsa alınan kararlar veya eylem maddeleri\n\n"
                "Transkript Kısmı:\n"
            )
        },
        "en": {
            "system": (
                "You are a professional meeting analyst and executive assistant. "
                "Your job is to capture ALL topics from the transcript without exception. "
                "Never skip any topic, no matter how briefly it was discussed. "
                "Always respond in ENGLISH."
            ),
            "heading": "TITLE",
            "default_title": "General Meeting Summary",
            "instructions": (
                "Read the following meeting transcript carefully line by line and respond in ENGLISH.\n\n"
                "1) Write the overall meeting topic as 'TITLE: [Title]' at the very top. Keep it short.\n\n"
                "2) Extract the names of REAL PEOPLE (human participants) and write them right below the title "
                "using the format 'PARTICIPANTS: Name 1, Name 2' on a SINGLE LINE separated ONLY by commas. "
                "Do NOT include products, technologies, or company names (e.g. Genesys, Cloud, AWS). "
                "Do NOT add titles or explanations next to names (like 'Main speaker', 'Worker'). "
                "Do NOT list participants as bullet points in the summary text.\n\n"
                "3) ## Executive Summary\n"
                "   Describe what was discussed, who said what, and what decisions were made — "
                "briefly but comprehensively. Do NOT focus only on the dominant topic; "
                "include every topic mentioned, even briefly.\n\n"
                "4) ## Agenda Items\n"
                "   List EVERY topic that appears in the transcript as a separate bullet.\n"
                "   Do not filter by importance — all topics must appear.\n"
                "   Format: - **Topic Title**: short explanation (note any decision/action)\n\n"
                "5) ## Action Items\n"
                "   List all to-do items from the meeting. If none exist, write "
                "'No action items were identified in this meeting.'\n\n"
                "WARNING: Do not compress the summary by ignoring topics. "
                "Every topic in the transcript MUST appear in sections 3 and 4."
            ),
            "intermediate": (
                "Below is a PART of a long meeting transcript.\n"
                "Please summarize this section in detail, without losing information, using bullet points:\n"
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
