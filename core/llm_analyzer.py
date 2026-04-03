import re

import requests
from PySide6.QtCore import QThread, Signal


class LlmAnalyzerThread(QThread):
    analysis_ready = Signal(str, str, str)  # title, participants, markdown_notes
    analysis_error = Signal(str)
    analysis_progress = Signal(str)

    MODEL_NAME = "qwen3.5:4b"

    # qwen3.5:4b icin daha genis baglam kullan; erken sikistirmayi azalt.
    MAX_DIRECT_TRANSCRIPT_CHARS = 18000
    MAX_CHARS_PER_CHUNK = 14000
    MAX_MERGE_INPUT_CHARS = 24000

    MAP_OUTPUT_TOKENS = 1400
    MERGE_OUTPUT_TOKENS = 1800
    FINAL_OUTPUT_TOKENS = 2400
    API_TIMEOUT_SECONDS = 18000

    LANG_CONFIG = {
        "tr": {
            "title_key": "BAŞLIK",
            "participants_key": "KATILIMCILAR",
            "default_title": "Genel Toplanti Notu",
            "system": (
                "Sen kurumsal bir toplanti notu ve karar kaydi uzmansin. "
                "Yalnizca verilen transkripte dayanarak yaz. "
                "Transkriptte olmayan hicbir bilgiyi ekleme, tahmin etme, tamamlama veya dis bilgi kullanma. "
                "Whisper kaynakli bozuk cumleleri ancak transkriptin kendi baglami acikca destekliyorsa toparla. "
                "Bilgi belirsizse 'transkriptte net degil', hic yoksa 'belirtilmedi' yaz. "
                "Tekrarlari temizle, daginik konusmalari toparla, ama anlami degistirme. "
                "Cikti dili profesyonel, kurumsal ve acik Turkce olsun."
            ),
            "map_system": (
                "Sen uzun toplanti transkriptlerinin her parcasindan kayipsiz, kanit-odakli notlar cikaran bir asistansin. "
                "Yalnizca verilen parca icindeki bilgileri kullan."
            ),
            "merge_system": (
                "Sen parcalardan gelen yapi-landirilmis toplanti notlarini birlestiren bir asistansin. "
                "Hicbir benzersiz maddeyi kaybetme, tekrar edenleri birlestir, belirsizlikleri koru."
            ),
            "map_prompt": (
                "Asagida uzun bir toplantinin {current}/{total}. parcasi var.\n"
                "Bu parca icin YALNIZCA transkriptte gecen bilgileri cikart.\n"
                "Kurallar:\n"
                "- Uydurma yapma.\n"
                "- Emin degilsen 'transkriptte net degil' yaz.\n"
                "- Bilgi hic yoksa 'belirtilmedi' yaz.\n"
                "- Kisa ama kayipsiz ol.\n"
                "- Aksiyon, sorumlu, termin, tarih, risk, blokaj ve acik kalan maddeleri ozellikle ayikla.\n"
                "- Her maddede mumkun oldugunca hangi konudan geldigi anlasilsin.\n\n"
                "Su yapiyi kullan:\n"
                "BASLIK_ADAYLARI:\n"
                "- ...\n"
                "KATILIMCI_ADAYLARI:\n"
                "- ...\n"
                "TOPLANTININ_AMACI:\n"
                "- ...\n"
                "KISA_OZET:\n"
                "- ...\n"
                "ELE_ALINAN_KONULAR:\n"
                "- ...\n"
                "ALINAN_KARARLAR:\n"
                "- ...\n"
                "AKSIYON_MADDELERI:\n"
                "- Aksiyon: ... | Sorumlu: ... | Termin: ...\n"
                "SORUMLULAR:\n"
                "- Kisi: ... | Sorumluluk: ...\n"
                "TERMIN_TARIH_BILGILERI:\n"
                "- ...\n"
                "ACIK_KALAN_KONULAR:\n"
                "- ...\n"
                "RISKLER_BLOKAJLAR:\n"
                "- ...\n"
                "BELIRSIZ_NOKTALAR:\n"
                "- ...\n\n"
                "Transkript Parcasi:\n{transcript}"
            ),
            "merge_prompt": (
                "Asagida farkli transkript parcaciklarindan cikartilmis yapi-landirilmis notlar var.\n"
                "Bunlari TEK bir yapiya birlestir.\n"
                "Kurallar:\n"
                "- Hicbir benzersiz konuyu, karari, aksiyonu, tarihi, sorumluyu, riski veya acik konuyu dusurme.\n"
                "- Tekrarlari birlestir ama bilgi kaybetme.\n"
                "- Supheli yerlerde 'transkriptte net degil' ifadesini koru.\n"
                "- Yeni bilgi uydurma.\n"
                "- Yine ayni basliklarla yaz.\n\n"
                "Birlesecek Notlar:\n{material}"
            ),
            "final_from_transcript": (
                "Asagidaki ham toplanti transkriptinden gercek toplanti notu uret.\n"
                "Yalnizca transkripte dayan.\n\n"
                "Zorunlu kurallar:\n"
                "- Ilk iki satir ASAGIDAKI GIBI olsun:\n"
                "BAŞLIK: [kisa ve acik toplanti basligi]\n"
                "KATILIMCILAR: [yalnizca transkriptte acikca gecen gercek kisi adlari; yoksa bos birak]\n"
                "- Sonrasinda tam olarak su bolumleri yaz:\n"
                "## Toplantı Başlığı\n"
                "## Toplantının Amacı\n"
                "## Kısa Yönetici Özeti\n"
                "## Ele Alınan Konular\n"
                "## Alınan Kararlar\n"
                "## Aksiyon Maddeleri\n"
                "## Sorumlular\n"
                "## Termin / Tarih Bilgileri\n"
                "## Açık Kalan Konular\n"
                "## Riskler / Blokajlar\n"
                "- Transkriptte olmayan bilgi ekleme.\n"
                "- Belirsizse 'transkriptte net degil', yoksa 'belirtilmedi' yaz.\n"
                "- Gereksiz tekrar temizlensin.\n"
                "- Aksiyonlari ve sahiplerini mumkun oldugunca yakala.\n"
                "- Tarih, saat, teslim tarihi ve yapilacaklari ozellikle ayikla.\n"
                "- Kurumsal, profesyonel Turkce kullan.\n\n"
                "Ham Transkript:\n{transcript}"
            ),
            "final_from_notes": (
                "Asagidaki yapi-landirilmis, transkripte dayali parcali notlari kullanarak tek bir nihai toplanti notu uret.\n"
                "Sadece bu malzemede bulunan bilgileri kullan; yeni bilgi ekleme.\n\n"
                "Zorunlu kurallar:\n"
                "- Ilk iki satir ASAGIDAKI GIBI olsun:\n"
                "BAŞLIK: [kisa ve acik toplanti basligi]\n"
                "KATILIMCILAR: [yalnizca acikca gecen gercek kisi adlari; yoksa bos birak]\n"
                "- Sonrasinda tam olarak su bolumleri yaz:\n"
                "## Toplantı Başlığı\n"
                "## Toplantının Amacı\n"
                "## Kısa Yönetici Özeti\n"
                "## Ele Alınan Konular\n"
                "## Alınan Kararlar\n"
                "## Aksiyon Maddeleri\n"
                "## Sorumlular\n"
                "## Termin / Tarih Bilgileri\n"
                "## Açık Kalan Konular\n"
                "## Riskler / Blokajlar\n"
                "- Cikti kayipsiz olsun; tum benzersiz maddeleri koru.\n"
                "- Belirsizse 'transkriptte net degil', yoksa 'belirtilmedi' yaz.\n"
                "- Tekrarlari temizle, anlami bozma.\n"
                "- Kurumsal, profesyonel Turkce kullan.\n\n"
                "Birlestirilmis Not Malzemesi:\n{material}"
            ),
            "final_progress": "Nihai toplanti notu olusturuluyor...",
            "long_progress": "Uzun toplanti tespit edildi. Parca bazli toplanti notlari cikartilip birlestiriliyor...",
            "chunk_progress": "Parca {current}/{total} isleniyor...",
            "merge_progress": "Parcali notlar birlestiriliyor: {current}/{total}...",
            "error_prefix": "Analiz Hatasi",
        },
        "en": {
            "title_key": "TITLE",
            "participants_key": "PARTICIPANTS",
            "default_title": "General Meeting Notes",
            "system": (
                "You are a corporate meeting notes and decision-record specialist. "
                "Use only the provided transcript. "
                "Do not add, infer, complete, or assume facts that are not supported by the transcript. "
                "Only repair Whisper errors when the transcript context clearly supports the repair. "
                "If something is unclear, write 'not clear from transcript'. If absent, write 'not specified'. "
                "Clean repetition and organize messy discussion without changing meaning. "
                "Use professional, corporate English."
            ),
            "map_system": (
                "You extract loss-minimized, evidence-based meeting notes from one transcript chunk at a time. "
                "Use only the provided chunk."
            ),
            "merge_system": (
                "You merge structured notes coming from multiple transcript chunks. "
                "Do not lose unique facts, and preserve uncertainty."
            ),
            "map_prompt": (
                "Below is chunk {current}/{total} from a long meeting transcript.\n"
                "Extract ONLY what is explicitly supported by this chunk.\n"
                "Rules:\n"
                "- Do not hallucinate.\n"
                "- If uncertain, write 'not clear from transcript'.\n"
                "- If absent, write 'not specified'.\n"
                "- Keep it concise but loss-minimized.\n"
                "- Pay special attention to actions, owners, deadlines, dates, risks, blockers, and open items.\n\n"
                "Use this structure:\n"
                "TITLE_CANDIDATES:\n"
                "- ...\n"
                "PARTICIPANT_CANDIDATES:\n"
                "- ...\n"
                "MEETING_PURPOSE:\n"
                "- ...\n"
                "SHORT_SUMMARY:\n"
                "- ...\n"
                "TOPICS_DISCUSSED:\n"
                "- ...\n"
                "DECISIONS_MADE:\n"
                "- ...\n"
                "ACTION_ITEMS:\n"
                "- Action: ... | Owner: ... | Deadline: ...\n"
                "RESPONSIBILITIES:\n"
                "- Person: ... | Responsibility: ...\n"
                "DATES_AND_TIMELINES:\n"
                "- ...\n"
                "OPEN_ITEMS:\n"
                "- ...\n"
                "RISKS_AND_BLOCKERS:\n"
                "- ...\n"
                "UNCERTAIN_POINTS:\n"
                "- ...\n\n"
                "Transcript Chunk:\n{transcript}"
            ),
            "merge_prompt": (
                "Below are structured notes extracted from several transcript chunks.\n"
                "Merge them into a single structured note set.\n"
                "Rules:\n"
                "- Do not drop any unique topic, decision, action, date, owner, risk, or open issue.\n"
                "- Merge duplicates without losing detail.\n"
                "- Preserve uncertainty labels.\n"
                "- Do not invent new facts.\n"
                "- Keep the same section headings.\n\n"
                "Notes To Merge:\n{material}"
            ),
            "final_from_transcript": (
                "Create real meeting notes from the raw transcript below.\n"
                "Use only the transcript.\n\n"
                "Required rules:\n"
                "- The first two lines must be exactly:\n"
                "TITLE: [short descriptive meeting title]\n"
                "PARTICIPANTS: [real human names only if clearly mentioned; otherwise leave blank]\n"
                "- Then write exactly these sections:\n"
                "## Meeting Title\n"
                "## Meeting Purpose\n"
                "## Executive Summary\n"
                "## Topics Discussed\n"
                "## Decisions Made\n"
                "## Action Items\n"
                "## Owners\n"
                "## Dates / Deadlines\n"
                "## Open Issues\n"
                "## Risks / Blockers\n"
                "- Do not add unsupported information.\n"
                "- If unclear, write 'not clear from transcript'; if absent, write 'not specified'.\n"
                "- Remove unnecessary repetition.\n"
                "- Capture actions, owners, dates, times, and deadlines as much as possible.\n"
                "- Use professional corporate English.\n\n"
                "Raw Transcript:\n{transcript}"
            ),
            "final_from_notes": (
                "Using the structured transcript-based notes below, create one final set of meeting notes.\n"
                "Use only the information in this material.\n\n"
                "Required rules:\n"
                "- The first two lines must be exactly:\n"
                "TITLE: [short descriptive meeting title]\n"
                "PARTICIPANTS: [real human names only if clearly mentioned; otherwise leave blank]\n"
                "- Then write exactly these sections:\n"
                "## Meeting Title\n"
                "## Meeting Purpose\n"
                "## Executive Summary\n"
                "## Topics Discussed\n"
                "## Decisions Made\n"
                "## Action Items\n"
                "## Owners\n"
                "## Dates / Deadlines\n"
                "## Open Issues\n"
                "## Risks / Blockers\n"
                "- Keep all unique facts.\n"
                "- If unclear, write 'not clear from transcript'; if absent, write 'not specified'.\n"
                "- Remove repetition without changing meaning.\n"
                "- Use professional corporate English.\n\n"
                "Structured Notes:\n{material}"
            ),
            "final_progress": "Generating final meeting notes...",
            "long_progress": "Long meeting detected. Extracting and merging chunk-based meeting notes...",
            "chunk_progress": "Processing chunk {current}/{total}...",
            "merge_progress": "Merging chunk notes: {current}/{total}...",
            "error_prefix": "Analysis Error",
        },
    }

    def __init__(self, transcript, language="tr"):
        super().__init__()
        self.language = language if language in self.LANG_CONFIG else "tr"
        self.transcript = self._normalize_transcript(transcript)
        self.api_url = "http://127.0.0.1:52625/v1/chat/completions"

    def run(self):
        cfg = self.LANG_CONFIG[self.language]

        try:
            if len(self.transcript) <= self.MAX_DIRECT_TRANSCRIPT_CHARS:
                source_material = self.transcript
                use_structured_merge = False
            else:
                self.analysis_progress.emit(cfg["long_progress"])
                source_material = self._build_structured_context(cfg)
                use_structured_merge = True

            self.analysis_progress.emit(cfg["final_progress"])
            content = self._generate_final_report(source_material, cfg, use_structured_merge)
            self._parse_and_emit(content, cfg)
        except Exception as e:
            self.analysis_error.emit(f"{cfg['error_prefix']}: {str(e)}")

    def _build_structured_context(self, cfg):
        chunks = self._split_transcript(self.transcript, self.MAX_CHARS_PER_CHUNK)
        total_chunks = len(chunks)
        extracted_notes = []

        for i, chunk in enumerate(chunks):
            self.analysis_progress.emit(
                cfg["chunk_progress"].format(current=i + 1, total=total_chunks)
            )
            prompt = cfg["map_prompt"].format(
                current=i + 1,
                total=total_chunks,
                transcript=chunk,
            )
            note = self._call_llm(
                system_prompt=cfg["map_system"],
                user_prompt=prompt,
                max_tokens=self.MAP_OUTPUT_TOKENS,
            )
            extracted_notes.append(
                f"=== CHUNK {i + 1}/{total_chunks} ===\n{note.strip()}\n"
            )

        return self._merge_structured_notes(extracted_notes, cfg)

    def _merge_structured_notes(self, note_groups, cfg):
        combined = "\n\n".join(note_groups).strip()
        if len(combined) <= self.MAX_MERGE_INPUT_CHARS:
            return combined

        grouped_materials = self._split_transcript(combined, self.MAX_MERGE_INPUT_CHARS)
        merged_groups = []
        total_groups = len(grouped_materials)

        for i, material in enumerate(grouped_materials):
            self.analysis_progress.emit(
                cfg["merge_progress"].format(current=i + 1, total=total_groups)
            )
            merged = self._call_llm(
                system_prompt=cfg["merge_system"],
                user_prompt=cfg["merge_prompt"].format(material=material),
                max_tokens=self.MERGE_OUTPUT_TOKENS,
            )
            merged_groups.append(
                f"=== MERGED GROUP {i + 1}/{total_groups} ===\n{merged.strip()}\n"
            )

        return self._merge_structured_notes(merged_groups, cfg)

    def _generate_final_report(self, source_material, cfg, use_structured_merge):
        if use_structured_merge:
            prompt = cfg["final_from_notes"].format(material=source_material)
        else:
            prompt = cfg["final_from_transcript"].format(transcript=source_material)

        return self._call_llm(
            system_prompt=cfg["system"],
            user_prompt=prompt,
            max_tokens=self.FINAL_OUTPUT_TOKENS,
        )

    def _normalize_transcript(self, text):
        text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _split_transcript(self, text, max_len):
        lines = text.split("\n")
        chunks = []
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_len:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = line + "\n"
                else:
                    chunks.append(line[:max_len])
                    current_chunk = line[max_len:] + "\n"
            else:
                current_chunk += line + "\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _call_llm(self, system_prompt, user_prompt, max_tokens):
        data = {
            "model": self.MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "repeat_penalty": 1.1,
            "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        response = requests.post(self.api_url, json=data, timeout=self.API_TIMEOUT_SECONDS)
        response_text = response.text

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {self._shorten_error_text(response_text)}")

        try:
            result = response.json()
        except Exception:
            raise Exception(f"Gecersiz JSON yaniti: {self._shorten_error_text(response_text)}")

        content = self._extract_content_from_response(result)
        if content is not None:
            return content

        error_text = self._extract_error_from_response(result)
        if error_text:
            raise Exception(error_text)

        raise Exception(
            "Model gecerli bir chat yaniti donmedi. "
            f"Gelen alanlar: {', '.join(sorted(result.keys())) or 'yok'}"
        )

    def _extract_content_from_response(self, result):
        try:
            choices = result.get("choices")
            if isinstance(choices, list) and choices:
                first_choice = choices[0] or {}
                message = first_choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content
                text = first_choice.get("text")
                if isinstance(text, str) and text.strip():
                    return text
        except Exception:
            pass

        # Bazi servisler fallback olarak dogrudan text/content donebiliyor.
        direct_content = result.get("content")
        if isinstance(direct_content, str) and direct_content.strip():
            return direct_content

        direct_text = result.get("text")
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text

        return None

    def _extract_error_from_response(self, result):
        candidates = [
            result.get("error"),
            result.get("message"),
            result.get("detail"),
        ]

        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return self._shorten_error_text(candidate)
            if isinstance(candidate, dict):
                nested = candidate.get("message") or candidate.get("detail") or candidate.get("error")
                if isinstance(nested, str) and nested.strip():
                    return self._shorten_error_text(nested)

        return None

    def _shorten_error_text(self, text, limit=500):
        compact = " ".join((text or "").split())
        if len(compact) <= limit:
            return compact
        return compact[:limit] + "..."

    def _parse_and_emit(self, content, cfg):
        title = cfg["default_title"]
        participants_str = ""
        lines = content.split("\n")

        heading_keys = [cfg["title_key"], "TITLE", "BASLIK", "BAŞLIK"]
        part_keys = [cfg["participants_key"], "PARTICIPANTS", "KATILIMCILAR"]

        found_title = False
        found_participants = False
        final_lines = []

        for line in lines:
            stripped = line.strip()
            clean_line = re.sub(r"[*#_`]", "", stripped).strip()
            clean_upper = clean_line.upper()
            matched = False

            if not found_title:
                for key in heading_keys:
                    if re.match(rf"^{re.escape(key)}\s*:", clean_upper):
                        extracted = re.split(r":\s*", clean_line, maxsplit=1)
                        if len(extracted) > 1 and extracted[1].strip():
                            title = extracted[1].strip()
                            found_title = True
                        matched = True
                        break

            if not matched and not found_participants:
                for key in part_keys:
                    if re.match(rf"^{re.escape(key)}\s*:", clean_upper):
                        extracted = re.split(r":\s*", clean_line, maxsplit=1)
                        if len(extracted) > 1 and extracted[1].strip():
                            participants_str = extracted[1].strip()
                            found_participants = True
                        matched = True
                        break

            if not matched:
                final_lines.append(line)

        if not found_title or not found_participants:
            first_block = "\n".join(lines[:30])
            if not found_title:
                for key in heading_keys:
                    match = re.search(
                        rf"^[*#\s]*{re.escape(key)}[*#\s]*:\s*(.+)$",
                        first_block,
                        re.MULTILINE | re.IGNORECASE,
                    )
                    if match and match.group(1).strip():
                        title = match.group(1).strip().replace("**", "").replace("*", "").strip()
                        found_title = True
                        break
            if not found_participants:
                for key in part_keys:
                    match = re.search(
                        rf"^[*#\s]*{re.escape(key)}[*#\s]*:\s*(.+)$",
                        first_block,
                        re.MULTILINE | re.IGNORECASE,
                    )
                    if match and match.group(1).strip():
                        participants_str = (
                            match.group(1).strip().replace("**", "").replace("*", "").strip()
                        )
                        found_participants = True
                        break

        summary_body = "\n".join(final_lines).strip()
        self.analysis_ready.emit(title, participants_str, summary_body)
