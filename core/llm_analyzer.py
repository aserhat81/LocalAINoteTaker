import re

import requests
from PySide6.QtCore import QThread, Signal


class LlmAnalyzerThread(QThread):
    analysis_ready = Signal(str, str, str)  # title, participants, markdown_notes
    analysis_error = Signal(str)
    analysis_progress = Signal(str)

    MODEL_NAME = "qwen3.5:4b"

    # qwen3.5:4b icin daha genis baglam kullan; erken sikistirmayi azalt.
    MAX_DIRECT_TRANSCRIPT_CHARS = 6000
    MAX_CHARS_PER_CHUNK = 10000
    MAX_MERGE_INPUT_CHARS = 22000
    MAX_REVIEW_INPUT_CHARS = 28000

    MAP_OUTPUT_TOKENS = 3000
    MERGE_OUTPUT_TOKENS = 3600
    FINAL_OUTPUT_TOKENS = 4800
    REVIEW_OUTPUT_TOKENS = 4800
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
                "- Her benzersiz konuyu ayri bir madde olarak yaz; az bahsedilen konulari da atlama.\n"
                "- Maddeleri transkriptteki gorusme sirasina yakin tut.\n"
                "- Detayli gorusme notlarinda konu bazli ara detaylari, gerekceleri, ornekleri ve baglami koru.\n"
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
                "DETAYLI_GORUSME_NOTLARI:\n"
                "- Konu: ... | Detaylar: ... | Gerekce/Ornek: ... | Sonuc/Durum: ...\n"
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
                "- Bir parçada yalnızca bir kez gecen kucuk/yan konulari da koru.\n"
                "- Detayli gorusme notlarindaki ara gerekceleri, ornekleri, sayisal bilgileri ve konu baglamlarini koru.\n"
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
                "## Detaylı Görüşme Notları\n"
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
                "- Detaylı Görüşme Notları bolumunde konu bazli ara detaylari, gerekceleri, ornekleri, sayisal bilgileri ve kimin neyi neden soyledigini kayipsiz aktar.\n"
                "- Aksiyonlari ve sahiplerini mumkun oldugunca yakala.\n"
                "- Tarih, saat, teslim tarihi ve yapilacaklari ozellikle ayikla.\n"
                "- Transkriptteki HER benzersiz konu Detaylı Görüşme Notları veya ilgili özel bölümde görünmeli.\n"
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
                "## Detaylı Görüşme Notları\n"
                "## Ele Alınan Konular\n"
                "## Alınan Kararlar\n"
                "## Aksiyon Maddeleri\n"
                "## Sorumlular\n"
                "## Termin / Tarih Bilgileri\n"
                "## Açık Kalan Konular\n"
                "## Riskler / Blokajlar\n"
                "- Cikti kayipsiz olsun; tum benzersiz maddeleri koru.\n"
                "- Detaylı Görüşme Notları bolumunde parcalardan gelen konu bazli detaylari, gerekceleri, ornekleri ve sayisal bilgileri ozellikle koru.\n"
                "- Belirsizse 'transkriptte net degil', yoksa 'belirtilmedi' yaz.\n"
                "- Tekrarlari temizle, anlami bozma.\n"
                "- Kaynaktaki HER benzersiz konu nihai notta en az bir kez görünmeli; az bahsedilen yan konuları atlama.\n"
                "- Kurumsal, profesyonel Turkce kullan.\n\n"
                "Birlestirilmis Not Malzemesi:\n{material}"
            ),
            "review_system": (
                "Sen bir toplanti notu kapsam denetcisisin. Taslagi kaynak malzemeyle karsilastirir, "
                "eksik kalan tum destekli konulari ekleyerek eksiksiz nihai notu yeniden yazarsin. "
                "Kaynakta olmayan bilgi eklemezsin."
            ),
            "review_prompt": (
                "Asagida kaynak malzeme ve bu malzemeden uretilmis bir taslak var.\n"
                "Taslagi bastan sona denetle ve TAMAMLANMIS NIHAYI NOTU yeniden yaz.\n"
                "Kurallar:\n"
                "- Kaynaktaki her benzersiz konu, karar, gerekce, ornek, sayi, tarih, aksiyon, sorumlu, risk ve acik madde taslakta var mi kontrol et.\n"
                "- Eksik veya fazla sikistirilmis noktalarin tamamini uygun bolume ekle.\n"
                "- Taslaktaki destekli bilgileri kaybetme; yalnizca tekrarlari birlestir.\n"
                "- Ilk iki satir BAŞLIK: ve KATILIMCILAR: biciminde kalsin; mevcut bolum yapisini koru.\n"
                "- Kaynakta olmayan bilgi ekleme.\n\n"
                "KAYNAK MALZEME:\n{material}\n\n"
                "DENETLENECEK TASLAK:\n{draft}"
            ),
            "final_progress": "Nihai toplanti notu olusturuluyor...",
            "review_progress": "Konu atlanmadigini doğrulamak icin kapsam denetimi yapiliyor...",
            "review_fallback": "Kapsam denetimi tamamlanamadi; ilk ayrintili taslak korunuyor.",
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
                "- Write every distinct topic as a separate item, including briefly mentioned side topics.\n"
                "- Keep items close to transcript order.\n"
                "- Preserve topic-level discussion details, rationale, examples, numbers, and context in Detailed Discussion Notes.\n"
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
                "DETAILED_DISCUSSION_NOTES:\n"
                "- Topic: ... | Details: ... | Rationale/Example: ... | Outcome/Status: ...\n"
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
                "- Preserve small side topics even when they occur in only one chunk.\n"
                "- Preserve detailed discussion notes, including rationale, examples, numbers, and context.\n"
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
                "## Detailed Discussion Notes\n"
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
                "- In Detailed Discussion Notes, keep topic-level details, rationale, examples, numbers, and who said what/why when supported by the transcript.\n"
                "- Capture actions, owners, dates, times, and deadlines as much as possible.\n"
                "- EVERY distinct transcript topic must appear in Detailed Discussion Notes or its relevant dedicated section.\n"
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
                "## Detailed Discussion Notes\n"
                "## Topics Discussed\n"
                "## Decisions Made\n"
                "## Action Items\n"
                "## Owners\n"
                "## Dates / Deadlines\n"
                "## Open Issues\n"
                "## Risks / Blockers\n"
                "- Keep all unique facts.\n"
                "- In Detailed Discussion Notes, preserve detailed topic context, rationale, examples, and numbers from the structured notes.\n"
                "- If unclear, write 'not clear from transcript'; if absent, write 'not specified'.\n"
                "- Remove repetition without changing meaning.\n"
                "- Every distinct source topic must appear at least once; do not omit briefly discussed side topics.\n"
                "- Use professional corporate English.\n\n"
                "Structured Notes:\n{material}"
            ),
            "review_system": (
                "You are a meeting-notes coverage auditor. Compare a draft against its source material "
                "and rewrite the complete final notes with every supported omission restored. "
                "Never add unsupported information."
            ),
            "review_prompt": (
                "Below are source material and a draft produced from it.\n"
                "Audit the whole draft and rewrite the COMPLETE FINAL NOTES.\n"
                "Rules:\n"
                "- Check every unique topic, decision, rationale, example, number, date, action, owner, risk, and open item from the source.\n"
                "- Restore every missing or over-compressed point in the appropriate section.\n"
                "- Keep all supported draft information; merge only genuine repetition.\n"
                "- Keep the first two TITLE: and PARTICIPANTS: lines and the existing section structure.\n"
                "- Do not add unsupported information.\n\n"
                "SOURCE MATERIAL:\n{material}\n\n"
                "DRAFT TO AUDIT:\n{draft}"
            ),
            "final_progress": "Generating final meeting notes...",
            "review_progress": "Running a coverage audit to verify no topics were omitted...",
            "review_fallback": "Coverage audit could not finish; keeping the first detailed draft.",
            "long_progress": "Long meeting detected. Extracting and merging chunk-based meeting notes...",
            "chunk_progress": "Processing chunk {current}/{total}...",
            "merge_progress": "Merging chunk notes: {current}/{total}...",
            "error_prefix": "Analysis Error",
        },
    }

    PROVIDER_DEFAULTS = {
        "flm": {
            "base_url": "http://127.0.0.1:52625/v1",
            "model": MODEL_NAME,
        },
        "ollama": {
            "base_url": "http://127.0.0.1:11434/v1",
            "model": "qwen3:4b",
        },
        "lm_studio": {
            "base_url": "http://127.0.0.1:1234/v1",
            "model": "local-model",
        },
    }

    def __init__(
        self,
        transcript,
        language="tr",
        model_name=None,
        provider="flm",
        base_url=None,
    ):
        super().__init__()
        self.language = language if language in self.LANG_CONFIG else "tr"
        self.transcript = self._normalize_transcript(transcript)
        self.provider = (provider or "flm").strip().lower()
        if self.provider not in self.PROVIDER_DEFAULTS:
            self.provider = "flm"
        defaults = self.PROVIDER_DEFAULTS[self.provider]
        self.base_url = self._normalize_base_url(base_url or defaults["base_url"])
        self.api_url = f"{self.base_url}/chat/completions"
        self.model_name = (model_name or defaults["model"]).strip() or defaults["model"]

    def _normalize_base_url(self, base_url):
        base_url = (base_url or "").strip().rstrip("/")
        if not base_url:
            base_url = self.PROVIDER_DEFAULTS[self.provider]["base_url"]
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")].rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = base_url + "/v1"
        return base_url

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
            if len(source_material) + len(content) <= self.MAX_REVIEW_INPUT_CHARS:
                self.analysis_progress.emit(cfg["review_progress"])
                try:
                    reviewed_content = self._call_llm(
                        system_prompt=cfg["review_system"],
                        user_prompt=cfg["review_prompt"].format(
                            material=source_material,
                            draft=content,
                        ),
                        max_tokens=self.REVIEW_OUTPUT_TOKENS,
                    )
                    if reviewed_content.strip():
                        content = reviewed_content
                except Exception:
                    self.analysis_progress.emit(cfg["review_fallback"])
            self._parse_and_emit(content, cfg)
        except Exception as e:
            self.analysis_error.emit(f"{cfg['error_prefix']}: {str(e)}")

    def _build_structured_context(self, cfg):
        chunks = self._split_transcript(
            self.transcript,
            self.MAX_CHARS_PER_CHUNK,
            overlap_lines=2,
        )
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

    def _split_transcript(self, text, max_len, overlap_lines=0):
        chunks = []
        current_lines = []

        for line in text.split("\n"):
            line_parts = [line[i:i + max_len] for i in range(0, len(line), max_len)] or [""]
            for part in line_parts:
                candidate = "\n".join(current_lines + [part])
                if current_lines and len(candidate) > max_len:
                    chunks.append("\n".join(current_lines).strip())
                    overlap = current_lines[-overlap_lines:] if overlap_lines else []
                    while overlap and len("\n".join(overlap + [part])) > max_len:
                        overlap.pop(0)
                    current_lines = overlap
                current_lines.append(part)

        final_chunk = "\n".join(current_lines).strip()
        if final_chunk:
            chunks.append(final_chunk)

        return chunks

    def _call_llm(self, system_prompt, user_prompt, max_tokens):
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "stream": False,
        }

        if self.provider == "flm":
            data["repeat_penalty"] = 1.1
            data["chat_template_kwargs"] = {"enable_thinking": False}

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
