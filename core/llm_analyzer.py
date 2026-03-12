import requests
import re
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
                "YANITINİN İLK İKİ SATIRI AŞAĞIDAKI FORMAT ŞEKLİNDE OLMALIDIR "
                "(Markdown bölümlerinden ÖNCE yaz):\n"
                "BAŞLIK: [Toplantı bağlamından çıkarılan kısa ve açıklayıcı konu başlığı]\n"
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
                "IMPORTANT: The FIRST TWO LINES of your response must be (before any markdown sections):\n"
                "TITLE: [Short descriptive title inferred from the meeting context]\n"
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

        # Her bir LLM çağrısı için max output token (model güvenli sınır)
        MAX_OUTPUT_TOKENS = 2048
        # Her chunk için max karakter (~3000 token)
        MAX_CHARS = 12000

        try:
            if len(self.transcript) <= MAX_CHARS:
                # Kısa/Orta toplantı — tek seferde direkt analiz
                final_text = self.transcript
            else:
                # ── MAP AŞAMASI ────────────────────────────────────────────
                # Uzun transkripti parçalara böl, her birini özetle
                self.analysis_progress.emit(
                    "Uzun toplantı tespit edildi. Metin parçalara bölünerek analiz ediliyor "
                    "(bu işlem normalden uzun sürecektir)..."
                )
                chunks = self._split_transcript(self.transcript, MAX_CHARS)
                total_chunks = len(chunks)
                raw_summaries = []

                for i, chunk in enumerate(chunks):
                    self.analysis_progress.emit(f"Bölüm {i+1}/{total_chunks} özetleniyor...")
                    intermediate_prompt = cfg["intermediate"] + chunk
                    sys_prompt = (
                        "Sen parçalı transkriptleri analiz eden bir asistansın. Her detayı koru."
                        if self.language == "tr"
                        else "You are an assistant that analyzes transcript parts. Keep every detail."
                    )
                    chunk_summary = self._call_llm(
                        system_prompt=sys_prompt,
                        user_prompt=intermediate_prompt,
                        max_tokens=MAX_OUTPUT_TOKENS
                    )
                    raw_summaries.append(
                        f"========================================\n"
                        f"[BÖLÜM {i+1}/{total_chunks} - "
                        f"{'TOPLANTININ BAŞI' if i == 0 else ('TOPLANTININ SONU' if i == total_chunks - 1 else f'ORTA KISIM {i+1}')}]\n"
                        f"========================================\n"
                        f"{chunk_summary}\n"
                        f"[/BÖLÜM {i+1}]\n"
                    )

                # ── REDUCE AŞAMASI ─────────────────────────────────────────
                # Eğer ara özetlerin toplamı hâlâ büyükse, onları da chunk'layarak özetle
                # (hiçbir zaman MAX_CHARS'ı geçmeyene kadar)
                final_text = self._reduce_summaries(raw_summaries, cfg, MAX_CHARS, MAX_OUTPUT_TOKENS)

            # ── FINAL ANALİZ ───────────────────────────────────────────────
            # Artık final_text her zaman 12 000 karakterin altında → model rahat çalışır
            self.analysis_progress.emit("Final rapor oluşturuluyor...")
            prompt = f"{cfg['instructions']}\n\nToplantı Verisi:\n{final_text}"
            content = self._call_llm(cfg["system"], prompt, max_tokens=MAX_OUTPUT_TOKENS)

            self._parse_and_emit(content, cfg)

        except Exception as e:
            self.analysis_error.emit(f"Analiz Hatası: {str(e)}")

    def _reduce_summaries(self, summaries, cfg, max_chars, max_tokens):
        """Ara özetleri tekrar tekrar birleştirip sığana kadar özet üretir (recursive reduce)."""
        combined = "\n".join(summaries)
        if len(combined) <= max_chars:
            # Tüm özetler tek chunk'a sığıyor — birleştir ve döndür
            total = len(summaries)
            header = (
                f"DİKKAT: Aşağıdaki {total} BÖLÜMDEN oluşan ara özetler, "
                f"tek bir toplantının başından sonuna ait bilgileri içerir.\n"
                f"BÖLÜM 1'DEN BÖLÜM {total}'E KADAR tüm konuları eşit ağırlıkla kapsayan "
                f"kapsamlı bir özet oluştur. Sadece son bölüme odaklanma.\n\n"
                if self.language == "tr"
                else
                f"NOTE: The following {total} SECTION summaries cover a single meeting from start to finish.\n"
                f"Cover ALL SECTIONS from SECTION 1 to SECTION {total} with equal weight. "
                f"Do NOT focus only on the last section.\n\n"
            )
            return header + combined

        # Hâlâ büyük → yeni bir map-reduce turu
        chunks = self._split_transcript(combined, max_chars)
        total_chunks = len(chunks)
        new_summaries = []
        sys_prompt = (
            "Sen parçalı transkriptleri analiz eden bir asistansın. Her detayı koru."
            if self.language == "tr"
            else "You are an assistant that analyzes transcript parts. Keep every detail."
        )
        for i, chunk in enumerate(chunks):
            self.analysis_progress.emit(
                f"Özetler yeniden birleştiriliyor: {i+1}/{total_chunks}..."
            )
            chunk_summary = self._call_llm(
                system_prompt=sys_prompt,
                user_prompt=(cfg["intermediate"] + chunk),
                max_tokens=max_tokens
            )
            new_summaries.append(
                f"[ÖZET GRUBU {i+1}/{total_chunks}]\n{chunk_summary}\n[/ÖZET GRUBU {i+1}]\n"
            )
        return self._reduce_summaries(new_summaries, cfg, max_chars, max_tokens)

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
        """Başlığı ve katılımcıları LLM çıktısından ayıkla.
        
        LLM farklı formatlarda yazabilir:
          BAŞLIK: Satış Toplantısı
          **BAŞLIK:** Satış Toplantısı
          Başlık: Satış Toplantısı
        Bu nedenle hem satır bazlı hem regex tabanlı arama yap.
        """
        title = cfg["default_title"]
        participants_str = ""
        lines = content.split('\n')
        
        # Türkçe/İngilizce anahtar kelimeler (büyük harf)
        if self.language == "tr":
            heading_keys = ["BAŞLIK", "BASLIK", "TITLE"]
            part_keys = ["KATILIMCILAR", "PARTICIPANTS"]
        else:
            heading_keys = ["TITLE", "BAŞLIK"]
            part_keys = ["PARTICIPANTS", "KATILIMCILAR"]
        
        found_title = False
        found_participants = False
        final_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Markdown süslemelerini temizle: **, *, #, ---, ===
            clean_line = re.sub(r'[*#_`]', '', stripped).strip()
            clean_upper = clean_line.upper()
            
            matched = False
            
            # Başlık satırı kontrolü
            if not found_title:
                for key in heading_keys:
                    # "BAŞLIK:" veya "BAŞLIK :" formatlerini yakala
                    if re.match(rf'^{re.escape(key)}\s*:', clean_upper):
                        extracted = re.split(r':\s*', clean_line, maxsplit=1)
                        if len(extracted) > 1 and extracted[1].strip():
                            title = extracted[1].strip()
                            found_title = True
                        matched = True
                        break
            
            # Katılımcı satırı kontrolü
            if not matched and not found_participants:
                for key in part_keys:
                    if re.match(rf'^{re.escape(key)}\s*:', clean_upper):
                        extracted = re.split(r':\s*', clean_line, maxsplit=1)
                        if len(extracted) > 1 and extracted[1].strip():
                            participants_str = extracted[1].strip()
                            found_participants = True
                        matched = True
                        break
            
            if not matched:
                final_lines.append(line)
        
        # Regex fallback: İlk 30 satırda başlık veya katılımcı bulunamadıysa tüm metni tara
        if not found_title or not found_participants:
            first_block = '\n'.join(lines[:30])
            if not found_title:
                for key in heading_keys:
                    m = re.search(rf'^[*#\s]*{re.escape(key)}[*#\s]*:\s*(.+)$',
                                  first_block, re.MULTILINE | re.IGNORECASE)
                    if m and m.group(1).strip():
                        title = m.group(1).strip().replace('**', '').replace('*', '').strip()
                        found_title = True
                        break
            if not found_participants:
                for key in part_keys:
                    m = re.search(rf'^[*#\s]*{re.escape(key)}[*#\s]*:\s*(.+)$',
                                  first_block, re.MULTILINE | re.IGNORECASE)
                    if m and m.group(1).strip():
                        participants_str = m.group(1).strip().replace('**', '').replace('*', '').strip()
                        found_participants = True
                        break
        
        summary_body = '\n'.join(final_lines).strip()
        self.analysis_ready.emit(title, participants_str, summary_body)
