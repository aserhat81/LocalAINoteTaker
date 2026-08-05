# Local AI Suite

### Note Taker + Chatbot-RAG + Voice Assistant + Shorts Studio

#### FastFlowLM · Standard Whisper · Ollama · LM Studio

🌍 **[Türkçe versiyon için aşağı kaydırın](#-türkçe)**

Local AI Suite is a local-first Windows desktop application for meeting capture, transcription and summaries, document-grounded Chatbot-RAG agents, voice conversations, safe computer controls, local web chat widgets, and short-form video workflows.

The app was originally designed around **AMD NPU + FastFlowLM**, but it now also supports standard local alternatives. AMD NPU users get **FastFlowLM as the default experience**, while users without AMD NPU can still use **Standard Whisper**, **Ollama**, or **LM Studio** depending on their hardware and preference.

## 💬 Core Chatbot-RAG Workflow

Chatbot-RAG is a primary part of the application, not an add-on. Its normal local workflow is:

1. Select the shared local **LLM**, **embedding**, **STT**, and **TTS** configuration once at the top of the module.
2. Create one or more named chat agents and give each agent its own system prompt.
3. Chat locally with the selected agent. Conversations and messages are retained per agent in SQLite, and the LLM remains available between questions until **End Chat** is pressed.
4. Optionally upload PDF, DOCX, TXT, or Markdown documents to that agent. Upload only stages the files; **Index** and **Reindex** are explicit, separate operations.
5. When RAG is enabled, the agent retrieves relevant chunks from its own persistent local Chroma collection and uses them as document context for the answer.
6. Optionally enable voice mode to ask questions through the selected microphone and hear local TTS replies through the selected speaker.

The agent can work as a normal system-prompt chatbot without documents, or as a RAG agent with document context. Models are not started with the application: the required runtime starts on first use, stays loaded for the active chat or voice session, and is released when that session is ended. Model files, imported documents, vector data, chat history, STT, and TTS all run from or remain in the local application environment unless the user explicitly selects an external endpoint or browser-based integration.

---

## ⚡ Installation

### Requirements

| Requirement        | Status                                       |
| ------------------ | -------------------------------------------- |
| Windows 10/11      | Required                                     |
| Python 3.11+       | Required                                     |
| AMD Ryzen AI / NPU | Optional, recommended for FastFlowLM         |
| FastFlowLM         | Default provider on AMD NPU systems          |
| faster-whisper     | Installed automatically for Standard Whisper |
| pyannote.audio     | Optional; installed when diarization is enabled |
| Ollama             | Optional local LLM provider                  |
| LM Studio          | Optional local LLM provider                  |
| FFmpeg / yt-dlp    | Used by Shorts Studio workflows              |
| Chroma             | Persistent local vector database for RAG     |
| Coqui TTS          | Lightweight local Turkish speech synthesis   |
| FastAPI / Uvicorn  | Loopback-only local chatbot widget service   |

---

## 🚀 Setup

```bash
git clone https://github.com/aserhat81/LocalAISuite.git
cd LocalAISuite
setup.bat
```

The setup process:

* Installs Python dependencies from `requirements.txt`
* Checks AMD NPU availability
* Checks FastFlowLM availability
* Keeps FastFlowLM as default when AMD NPU is available
* Does not block installation if AMD NPU is missing
* Installs `faster-whisper` for Standard Whisper transcription
* Offers optional Ollama / LM Studio setup depending on detected hardware
* Creates a desktop shortcut named **Local AI Suite**

---

## ▶️ Start the Application

You can start the app in one of three ways:

```bash
python main.py
```

or double-click:

```text
run.bat
```

or use the desktop shortcut:

```text
Local AI Suite
```

---

## 🎯 Main Features

| Feature                          | Description                                                                        |
| -------------------------------- | ---------------------------------------------------------------------------------- |
| 💬 Local Chat                    | Chat locally with persistent per-agent conversations and message history           |
| 🤖 Agent Creation                | Create, rename, and delete agents with individual names and system prompts          |
| 📚 Agent-Specific Local RAG      | Add PDF, DOCX, TXT, or MD documents and index them in isolated local Chroma stores  |
| 🗣️ Local Voice Chat              | Ask through a selected microphone and hear local STT/TTS replies on a selected speaker |
| 🎤 System + Microphone Recording | Capture both system audio and microphone audio for online meetings                 |
| 🎙️ Microphone Only Mode         | Record physical meetings, dictation, or voice notes                                |
| 📝 Live Transcription            | Use FastFlowLM ASR or Standard Whisper                                             |
| 🤖 AI Meeting Analysis           | Generate titles, summaries, action items, and participant notes                    |
| 🧠 Multiple Local LLM Providers  | FastFlowLM, Ollama, and LM Studio support                                          |
| 📂 Local Meeting Archive         | Store meeting records in a local SQLite database                                   |
| 📧 Email Sharing                 | Send meeting notes via email                                                       |
| 🎬 Shorts Studio                 | Download, transcribe, and process video content for short-form workflows           |
| 🖥️ Safe Computer Controls       | Run allow-listed Windows actions with validation and confirmation where required    |
| 🌐 Local Web Widget             | Embed the selected agent on local HTML pages through a 127.0.0.1-only service       |
| 🌍 Turkish / English UI         | Select the interface language globally; defaults from the Windows display language  |
| 🔒 Local-First Design            | Meeting data stays on your computer unless you explicitly configure external tools |

---

## 🧩 Complete Module Reference

### 1. Note Taker

* Records **system audio + microphone** for online meetings or **microphone only** for in-room meetings, voice notes, and dictation.
* Lists Windows microphone and loopback speaker devices, supports manual device selection, and shows a live input-level meter.
* Uses voice activity detection to split speech into transcription chunks and includes a configurable prolonged-silence reminder. The reminder asks before ending a meeting; it never ends one automatically.
* Supports **FLM ASR**, **Standard Whisper**, and fixed **Whisper large-v3** transcription modes.
* Optionally performs full-meeting speaker diarization with `pyannote.audio`. In online mode the local microphone remains `BEN`; remote speakers are separated when possible.
* Supports FLM, Ollama, and LM Studio for meeting analysis. Long transcripts are processed with map/merge-style prompts instead of being silently truncated.
* Produces a meeting title, detected participants, purpose, short summary, detailed notes, decisions, risks, and action items.
* Finishing a meeting frees the recorder immediately. Remaining ASR, optional diarization, and summarization continue in a meeting-aware background queue.
* Stores pending and completed meetings in SQLite so processing state survives normal UI navigation.
* Includes a searchable/date-filtered meeting archive with separate summary and transcript tabs.
* Meeting title, participants, summary, and transcript can be edited and saved. The rich-text editor supports bold, italic, underline, font size, color, find, replace, case sensitivity, and replace-all.
* Existing transcripts can be reanalyzed with the currently selected LLM.
* Meeting notes can be opened in the default mail client through a `mailto:` draft.
* Reads Outlook through Windows COM when available or an Outlook/ICS export URL. It lists today's meetings, tracks the next meeting, and can display a foreground notification near meeting time.
* Continues in the Windows system tray and shuts down app-owned services and model processes on explicit exit.

### 2. Chatbot-RAG

* Creates, renames, and deletes multiple agents. Each agent stores its own name, system prompt, RAG toggle, computer-control permission, conversations, messages, documents, and renewable embed token.
* Agents do not pin their own model. All agents use the shared LLM, embedding, STT, speech-language, and TTS settings shown at the top of the module.
* LLM providers: **FastFlowLM**, **Ollama**, and **LM Studio**, with editable model names and endpoints. Known local defaults are FLM `52625`, Ollama `11434`, and LM Studio `1234`.
* Embedding providers: local Hugging Face **SentenceTransformers** or **FastFlowLM embeddings**. The default local model is `intfloat/multilingual-e5-small`; any compatible model ID can be entered. E5 `query:` and `passage:` prefixes are applied automatically.
* STT providers: **FLM Whisper / ASR** and **faster-whisper**. Speech language can be automatic, Turkish, or English. The configured FLM Whisper model defaults to `whisper-v3:turbo`.
* TTS defaults to the lightweight Turkish Coqui model `tts_models/tr/common-voice/glow-tts`. Microphone and output speaker are independently selectable.
* Chat responses show an animated thinking state and a fast typing effect. Ending the chat explicitly releases the held Chatbot-RAG runtime.
* Persistent conversations and messages are stored per agent in SQLite.

#### RAG document workflow

1. Upload PDF, DOCX, TXT, or Markdown files to stage them under `chatbot_rag_data/documents/<agent-id>/`.
2. Press **Index** for newly staged documents. Uploading does not trigger indexing automatically.
3. Press **Reindex** when existing documents must be rebuilt with the selected embedding configuration.
4. Documents are deduplicated per agent by SHA-256.
5. Text is split into roughly 350-word chunks with 50-word overlap. PDF page, DOCX paragraph, and text position metadata are retained.
6. Vectors are written to a persistent, telemetry-disabled Chroma database under `chatbot_rag_data/vector_db/` and isolated by agent ID.
7. Retrieval returns up to eight nearest chunks. Structured citation metadata is retained for API consumers but is not spoken by desktop TTS.
8. Scanned PDFs without a text layer are reported as unsupported; OCR is not performed.
9. Embedding-model-specific collections allow a new index to be built without deleting a different model's collection first.

#### Voice conversation lifecycle

* Voice mode starts the selected STT and TTS path only when enabled; the application does not start them at launch.
* FLM can run the selected LLM, embedding model, and ASR together on port `52625` using the appropriate `--embed 1` and `--asr 1` flags.
* The microphone detects speech and completes the utterance after approximately 1.6 seconds of silence.
* The microphone is stopped during transcription and TTS playback so the assistant does not hear its own answer.
* The first Coqui use validates compatible dependencies, downloads the model once into the application model folder, and keeps the model cached while voice mode remains active.
* TTS removes citation markers, source sections, and Markdown formatting before speech playback.

### 3. Safe Computer Control

Computer control is **off by default for every agent** and is enforced twice: at routing time and immediately before execution. The LLM can select only a strict action ID and validated JSON arguments; it cannot supply executable paths, shell text, PowerShell, arbitrary URLs, or code.

Read-only actions without confirmation:

* Next meeting and up to ten upcoming meetings from the next 30 days through Outlook/ICS.
* Visible applications, foreground window, CPU, RAM, disk, battery, local IP addresses, Windows information, and master-volume/mute state.
* Installation/availability checks for allow-listed applications.

Allow-listed open and window actions:

* Outlook, Teams, Chrome, Edge, Word, Excel, PowerPoint, File Explorer, Settings, Control Panel, Task Manager, Notepad, Calculator, Paint, Snipping Tool, Photos, Camera, Windows Terminal, and PowerShell. Terminal/PowerShell are only opened; commands are never typed or executed.
* C drive, the projects root, Documents, Downloads, Desktop, Pictures, and the application output folder.
* User-supplied existing absolute Windows folders after validation and explicit confirmation.
* YouTube home or a validated YouTube search query, preferring Chrome and otherwise the default browser.
* Focus, minimize, maximize, or restore a visible window.
* Play/pause, next-track, and previous-track media keys.

Supported Windows Settings pages include sound, volume mixer, microphone, speaker, Wi-Fi, network status, Ethernet, VPN, proxy, mobile hotspot, Bluetooth, connected devices, display, notifications, power, battery, storage, default apps, Windows Update, optional features, printers, camera/microphone privacy, date/time, language, background, taskbar, accessibility, About, and installed apps.

Actions requiring desktop confirmation include changing master volume, muting/unmuting, closing a window, and opening a user-provided folder path. Every attempted computer action is written to `pc_action_log` with safe arguments, confirmation state, result, and timestamp.

Intentionally unsupported: generated PowerShell/CMD, arbitrary executables or URLs, coordinate clicking, free keyboard automation, direct Wi-Fi/Bluetooth adapter toggling, file deletion/move/rename, shutdown/restart/sleep/sign-out, sending email or Teams messages, creating/changing meetings, reading credentials/cookies/clipboard, and web-widget computer control.

### 4. Local Web Chat Widget

* Starts only on `127.0.0.1:8765` while the desktop application is open.
* Publishes one selected agent with a renewable token and this embed form:

```html
<script src="http://127.0.0.1:8765/widget.js" data-agent-token="..."></script>
```

* Uses Shadow DOM and supports text chat, browser microphone capture, silence-based utterance completion, transcription, and optional spoken replies.
* Endpoints: `GET /health`, `GET /widget.js`, `GET /api/agent`, `POST /api/chat`, `POST /api/transcribe`, and `POST /api/tts`.
* Computer-control tools are never included in web prompts. Web requests are forced to `pc_control=false` even when the desktop agent has permission.

### 5. Shorts Studio

* Creates a project from a YouTube URL with selectable output root, 1–10 clip candidates, maximum clip duration (60/90/180 seconds), local model name, and optional search time ranges.
* Provides dependency-aware selectable steps: video download, audio-only download, subtitle/transcript acquisition, transcript cleaning, ChatGPT candidate analysis, selected-short rendering, yellow subtitle burn-in, and metadata TXT generation.
* Attempts creator or automatic subtitles in available languages and falls back to Whisper transcription when subtitle download fails.
* Can prepare/copy a ChatGPT prompt, accept pasted JSON, or use the persistent ChatGPT Browser Assist session after the user signs in.
* Validates candidate timing and exposes render selection, start/end, duration, score, title, and reason in a table.
* Renders verified vertical `1080x1920` MP4 clips with FFmpeg, writes per-render logs, embeds subtitles during render, and emits Turkish title/description/hashtag metadata.
* Selected FLM model sessions are coordinated with Note Taker so incompatible heavy local models are not loaded concurrently.

### 6. YouTube Downloader

* Accepts one URL or multiple URLs separated by lines.
* Downloads a single video or a complete playlist/list.
* Supports merged MP4 video or best-quality MP3 extraction.
* Uses bundled `tools/yt-dlp.exe` / `tools/ffmpeg.exe` when present, otherwise resolves `yt-dlp` and `ffmpeg` from `PATH`.
* Displays per-item combined progress and logs, produces safe numbered filenames, and supports cancellation.

### 7. Settings, Logs, Language, and Browser Bridge

* A global language selector sits above all module tabs. Turkish is selected automatically for a Turkish Windows display language; otherwise English is selected.
* Settings/Logs reports module state, database path, active ASR/LLM configuration, diarization, silence warning, queue length, and recent `error_log.txt` entries.
* ChatGPT Browser Bridge can open a persistent Chrome profile, wait for manual ChatGPT sign-in, send a test prompt, and return the visible response. It does not read browser passwords or cookies.

---

## 🗄️ Local Data and Model Layout

| Path | Purpose |
| ---- | ------- |
| `taklino_notes.db` | Meetings, settings, agents, documents, conversations, messages, and PC action audit log |
| `chatbot_rag_data/documents/<agent-id>/` | Agent-specific imported document copies |
| `chatbot_rag_data/vector_db/` | Persistent Chroma vector collections |
| `models/chatbot_rag/embeddings/` | Local SentenceTransformers cache |
| `models/chatbot_rag/tts/` | Coqui model and Numba cache |
| `downloads/` | YouTube Downloader default output |
| `output/shorts_studio/` | Shorts Studio projects and renders |
| `error_log.txt` | Recent local application errors when generated |

Models, downloaded media, browser profiles, local documents, vector data, logs, and database files are excluded from Git where applicable.

---

## ♻️ Lazy Model and Service Lifecycle

* No LLM, embedding, Whisper, diarization, or TTS model is intentionally loaded merely because the desktop window opened.
* Note Taker warms the selected Whisper model when recording starts and unloads caches after recording and its background queue become idle.
* Chatbot-RAG keeps its selected LLM alive across messages and releases it when the chat ends, the agent changes, or the application shuts down.
* Local embeddings load temporarily for indexing and stay available while needed by an active RAG session.
* Voice STT/TTS starts with voice mode; microphone capture stops during TTS.
* A shared model-session coordinator prevents Note Taker and Chatbot-RAG/Shorts Studio from silently replacing incompatible FLM models in active use.
* The local FastAPI server and app-owned FLM/model processes are stopped during explicit application shutdown.

---

## 🧠 AI Provider Options

Local AI Suite separates **transcription provider** and **summary / analysis provider**.

### Transcription Providers

| Provider         | Best For                   | Notes                                           |
| ---------------- | -------------------------- | ----------------------------------------------- |
| FastFlowLM ASR   | AMD Ryzen AI / NPU systems | Default when AMD NPU and FLM are available      |
| Standard Whisper | Any compatible Windows PC  | Uses `faster-whisper`; does not require AMD NPU |
| Whisper v3       | Accuracy-focused local STT | Uses the explicit `large-v3` faster-whisper model |

For local Whisper providers, the selected model is warmed up automatically when recording starts. Finishing a meeting immediately frees the recorder for the next meeting; transcription, optional diarization, and summarization continue in a meeting-aware background queue. Once recording and the entire processing queue are idle, cached Whisper and pyannote models are released from memory and app-owned FLM model processes are stopped.

The recording panel also includes a configurable prolonged-silence reminder (20 seconds by default, or `0` to disable it). The reminder asks before ending a meeting and never stops a recording automatically.

### Optional Speaker Diarization

Enable **Separate speakers with pyannote** next to the transcription controls to replace the final live transcript with globally aligned speaker labels before summarization. In microphone-only mode every detected room speaker is separated; in online mode the local microphone remains `BEN` while remote voices are separated. First install `requirements-diarization.txt`, accept the conditions for `pyannote/speaker-diarization-community-1` on Hugging Face, and set `HF_TOKEN` (or run `hf auth login`). If diarization cannot run, the application keeps the live transcript and continues safely.

### Summary / LLM Providers

| Provider   | Best For                           | Notes                                         |
| ---------- | ---------------------------------- | --------------------------------------------- |
| FastFlowLM | AMD NPU systems                    | Default provider on supported AMD NPU devices |
| Ollama     | NVIDIA GPU / general local LLM use | Optional; setup can offer installation        |
| LM Studio  | AMD GPU / general local LLM use    | Optional; setup can offer installation        |

---

## 🖥️ Hardware Behavior

### AMD NPU Available

If AMD NPU and FastFlowLM are detected:

* FastFlowLM is selected by default
* FLM ASR can be used for live transcription
* FLM LLM can be used for meeting analysis
* Ollama and LM Studio can still be selected manually

### No AMD NPU

If AMD NPU is not detected:

* The app still opens
* FastFlowLM is not forced
* Standard Whisper can be used for transcription
* Ollama or LM Studio can be used for summarization
* Setup may suggest optional provider installation

---

## 💬 Chatbot-RAG and Voice Assistant

Create multiple local agents with individual names, system prompts, persistent chat history, optional RAG context, and an optional safe-computer-control permission. Agents use the shared LLM, embedding, STT, and TTS configuration selected at the top of the module.

Documents are staged before indexing, deduplicated per agent, split into source-aware chunks, embedded with either a Hugging Face SentenceTransformers model or FastFlowLM embeddings, and stored in the local Chroma database. PDF, DOCX, TXT, and Markdown files are supported. RAG sources remain available as structured metadata without being spoken by TTS.

Voice mode uses microphone activity detection and completes an utterance after approximately 1.6 seconds of silence. FLM Whisper Turbo and standard faster-whisper are supported. The microphone and speaker can be selected independently. Models are loaded lazily when an agent, service, or voice mode starts and are released according to the active session lifecycle.

Computer controls are desktop-only and restricted to a validated action catalog. The app never executes free-form PowerShell generated by an LLM, performs coordinate-based clicking, or exposes computer controls through the web widget.

The local widget service listens only on `127.0.0.1:8765` and exposes the selected agent while the desktop app is running.

---

## 🏗️ Architecture

```text
main.py
├── ui/
│   ├── splash.py                 → Startup screen and environment checks
│   └── main_window.py            → Main application UI
├── core/
│   ├── hw_check.py               → Hardware and provider detection
│   ├── flm_manager.py            → FastFlowLM service management
│   ├── audio_capture.py          → System and microphone audio capture
│   ├── asr_client.py             → FastFlowLM ASR / Standard Whisper transcription
│   ├── llm_analyzer.py           → FLM / Ollama / LM Studio analysis provider
│   ├── model_session_manager.py  → Model/session handling
│   ├── chatbot_runtime.py        → Chat, RAG, and safe-action routing
│   ├── chat_voice.py             → Lazy STT/TTS workers and model cache
│   ├── rag_store.py              → Document extraction and persistent vectors
│   ├── pc_control.py             → Allow-listed Windows action catalog
│   └── shorts_pipeline.py        → Shorts Studio processing pipeline
├── modules/
│   ├── chatbot_rag.py            → Agent, document, chat, voice, and widget UI
│   ├── shorts_studio.py          → Shorts Studio UI/module
│   └── youtube_downloader.py     → Video download helper
├── services/
│   ├── chatbot_web_service.py    → Loopback-only FastAPI chatbot widget
│   └── chatgpt_browser_bridge.py → Browser automation bridge
├── database/
│   └── db_manager.py             → SQLite local database
├── utils/
│   └── email_sender.py           → Email sending helper
└── assets/
    └── icon.ico / icon.png       → Application icons
```

---

## 🔧 Manual Usage

Install dependencies manually:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python main.py
```

---

## ❓ Frequently Asked Questions

### Is AMD NPU required?

No. AMD NPU is recommended for the FastFlowLM experience, but it is no longer mandatory. Users without AMD NPU can use Standard Whisper for transcription and Ollama or LM Studio for LLM analysis.

### What is the default setup?

On AMD NPU systems, FastFlowLM is the default provider.

### Can I use Standard Whisper instead of FastFlowLM?

Yes. In the Note Taker section, you can select Standard Whisper as the live transcription provider.

### Can I use Ollama or LM Studio?

Yes. Ollama and LM Studio are available as optional local LLM providers for summarization and analysis.

### Does the app install everything automatically?

`setup.bat` installs the Python packages in `requirements.txt`, including the PDF/DOCX readers, Chroma, SentenceTransformers, FastAPI/Uvicorn, faster-whisper, audio support, and Coqui TTS runtime. Optional pyannote diarization has its own requirements and Hugging Face access conditions. FastFlowLM, Ollama, and LM Studio are provider applications; setup detects them and can offer an installation path where supported. Model weights are checked or downloaded once when that feature is first used, with user confirmation where installation is required.

### Does an agent require RAG documents?

No. An agent can chat using only its name and system prompt. Enable RAG and add/index documents only when answers should use a private document collection. Each agent retrieves only from its own indexed documents.

### Is the LLM reloaded for every question?

No. Starting a chat loads or starts the selected shared LLM when needed and keeps that runtime available between messages. **End Chat**, switching agents, or closing the application releases the Chatbot-RAG session. Voice STT/TTS similarly remains available while voice mode is active and is released when voice mode ends.

### What parts of Chatbot-RAG are local?

Imported documents, Chroma vectors, agents, conversations, and messages are stored locally. SentenceTransformers embeddings, faster-whisper STT, Coqui TTS, and locally configured FLM/Ollama/LM Studio endpoints operate locally. Data may leave the computer only when the user explicitly configures a non-local endpoint or uses a network/browser integration such as YouTube, ICS, or ChatGPT Browser Assist.

### FLM service does not start. What should I check?

Try running FastFlowLM manually from the terminal and confirm that the FLM command is available. If FLM is missing or AMD NPU is not available, switch transcription to Standard Whisper and LLM provider to Ollama or LM Studio.

### Model loading takes too long. Is this normal?

Yes. The first model load can take longer depending on your hardware and provider. Later runs are usually faster.

---

## ⚠️ Notes

* Meeting data is stored locally.
* Do not commit local outputs, browser profiles, downloaded videos, models, or logs to Git.
* Provider availability depends on your local machine setup.
* Ollama and LM Studio model performance depends heavily on CPU/GPU/RAM.

---

## ❤️ Credits

Made with ❤️ by Serhat

📺 **Developer YouTube Channel:**
[Teknoloji ve Hayat](https://www.youtube.com/@TeknolojiHayat)

---

<br><br><br>

# 🇹🇷 Türkçe

# Local AI Suite

### Not Tutucu + Chatbot-RAG + Sesli Asistan + Shorts Studio

#### FastFlowLM · Standart Whisper · Ollama · LM Studio

Local AI Suite; toplantı kaydı, transkripsiyon ve özetleme, doküman bağlamlı Chatbot-RAG ajanları, sesli sohbet, güvenli bilgisayar kontrolleri, yerel web chatbot bileşeni ve kısa video üretim akışları sunan yerel öncelikli Windows masaüstü uygulamasıdır.

Uygulama ilk olarak **AMD NPU + FastFlowLM** odaklı geliştirilmiştir. Ancak artık AMD NPU zorunlu değildir. AMD NPU olan sistemlerde **FastFlowLM varsayılan** olarak gelir. AMD NPU olmayan kullanıcılar ise **Standart Whisper**, **Ollama** veya **LM Studio** seçenekleriyle uygulamayı kullanabilir.

## 💬 Temel Chatbot-RAG Akışı

Chatbot-RAG uygulamanın ek bir aracı değil, ana bölümlerinden biridir. Normal yerel kullanım akışı şöyledir:

1. Modülün üstünde bütün ajanların kullanacağı ortak **LLM**, **embedding**, **STT** ve **TTS** ayarlarını bir kez seçin.
2. Bir veya daha fazla adlandırılmış sohbet ajanı oluşturun; her ajana kendi sistem promptunu verin.
3. Seçili ajanla yerel olarak sohbet edin. Konuşmalar ve mesajlar ajan bazında SQLite içinde kalıcı tutulur; LLM, **Sohbeti Bitir** düğmesine basılana kadar sorular arasında hazır kalır.
4. İsterseniz ajana PDF, DOCX, TXT veya Markdown belgeleri yükleyin. Yükleme yalnız dosyayı arayüze ekler; **İndeksle** ve **Yeniden İndeksle** ayrı ve açık işlemlerdir.
5. RAG açıkken ajan, yalnız kendi kalıcı yerel Chroma koleksiyonundan ilgili parçaları getirir ve yanıtta doküman bağlamı olarak kullanır.
6. İsterseniz sesli modu açarak seçili mikrofondan soru sorun ve yerel TTS yanıtını seçili hoparlörden dinleyin.

Ajan, hiçbir belge eklenmeden yalnız sistem promptuyla normal chatbot olarak veya belgelerden bağlam alan bir RAG ajanı olarak çalışabilir. Modeller uygulama açılırken başlamaz: gereken çalışma zamanı ilk kullanımda başlar, etkin sohbet ya da ses oturumu boyunca yüklü kalır ve oturum bitirilince serbest bırakılır. Kullanıcı açıkça harici bir endpoint veya tarayıcı entegrasyonu seçmedikçe model dosyaları, içe aktarılan belgeler, vektör verileri, sohbet geçmişi, STT ve TTS yerel uygulama ortamında çalışır veya burada saklanır.

---

## ⚡ Kurulum

### Gereksinimler

| Gereksinim         | Durum                                    |
| ------------------ | ---------------------------------------- |
| Windows 10/11      | Zorunlu                                  |
| Python 3.11+       | Zorunlu                                  |
| AMD Ryzen AI / NPU | Opsiyonel, FastFlowLM için önerilir      |
| FastFlowLM         | AMD NPU sistemlerde varsayılan sağlayıcı |
| faster-whisper     | Standart Whisper için otomatik kurulur   |
| pyannote.audio     | Opsiyonel; konuşmacı ayrımı seçilince kurulur |
| Ollama             | Opsiyonel yerel LLM sağlayıcı            |
| LM Studio          | Opsiyonel yerel LLM sağlayıcı            |
| FFmpeg / yt-dlp    | Shorts Studio akışlarında kullanılır     |
| Chroma             | RAG için kalıcı yerel vektör veritabanı |
| Coqui TTS          | Hafif yerel Türkçe ses sentezi           |
| FastAPI / Uvicorn  | Yalnız yerelde çalışan chatbot servisi  |

---

## 🚀 Kurulum Adımları

```bash
git clone https://github.com/aserhat81/LocalAISuite.git
cd LocalAISuite
setup.bat
```

Kurulum sırasında:

* `requirements.txt` içindeki Python bağımlılıkları kurulur
* AMD NPU kontrolü yapılır
* FastFlowLM kontrolü yapılır
* AMD NPU ve FLM varsa FastFlowLM varsayılan kalır
* AMD NPU yoksa kurulum durdurulmaz
* Standart Whisper için `faster-whisper` kurulur
* Donanıma göre Ollama / LM Studio kurulumu önerilebilir
* Masaüstüne **Local AI Suite** kısayolu oluşturulur

---

## ▶️ Uygulamayı Başlatma

Uygulamayı şu yollardan biriyle başlatabilirsiniz:

```bash
python main.py
```

veya:

```text
run.bat
```

veya masaüstündeki kısayol:

```text
Local AI Suite
```

---

## 🎯 Ana Özellikler

| Özellik                      | Açıklama                                                           |
| ---------------------------- | ------------------------------------------------------------------ |
| 💬 Yerel Sohbet              | Ajan bazında kalıcı konuşma ve mesaj geçmişiyle yerel sohbet       |
| 🤖 Ajan Oluşturma            | Kendi adı ve sistem promptu olan ajanları oluşturma, yeniden adlandırma ve silme |
| 📚 Ajana Özel Yerel RAG      | PDF, DOCX, TXT veya MD ekleyip ajana özel yerel Chroma koleksiyonunda indeksleme |
| 🗣️ Yerel Sesli Sohbet        | Seçili mikrofondan soru sorma; yerel STT/TTS yanıtını seçili hoparlörden dinleme |
| 🎤 Sistem + Mikrofon Kaydı   | Online toplantılar için sistem sesi ve mikrofonu birlikte kaydeder |
| 🎙️ Sadece Mikrofon Modu     | Fiziksel toplantılar, dikte ve sesli notlar için                   |
| 📝 Canlı Transkripsiyon      | FastFlowLM ASR veya Standart Whisper seçilebilir                   |
| 🤖 AI Toplantı Analizi       | Başlık, özet, aksiyon maddeleri ve katılımcı notları üretir        |
| 🧠 Çoklu Yerel LLM Sağlayıcı | FastFlowLM, Ollama ve LM Studio desteği                            |
| 📂 Yerel Toplantı Arşivi     | Toplantılar yerel SQLite veritabanında saklanır                    |
| 📧 E-Posta Paylaşımı         | Toplantı notlarını e-posta ile paylaşma                            |
| 🎬 Shorts Studio             | Video indirme, transkript çıkarma ve kısa video üretim akışı       |
| 🖥️ Güvenli Bilgisayar Kontrolü | Doğrulanan ve gerektiğinde onay isteyen Windows eylemleri       |
| 🌐 Yerel Web Widget          | Seçili ajanı yalnız 127.0.0.1 üzerinde HTML sayfasına ekleme       |
| 🌍 Türkçe / İngilizce Arayüz | Windows dilinden varsayılan alan uygulama geneli dil seçimi        |
| 🔒 Yerel Öncelikli Tasarım   | Verileriniz varsayılan olarak bilgisayarınızda kalır               |

---

## 🧩 Eksiksiz Modül Rehberi

### 1. Not Tutucu

* Online toplantılar için **sistem sesi + mikrofon**, fiziksel toplantı, sesli not ve dikte için **yalnız mikrofon** kaydı yapar.
* Windows mikrofon ve loopback hoparlör aygıtlarını listeler, elle aygıt seçimi ve canlı ses seviyesi göstergesi sunar.
* Konuşmayı parçalara ayırmak için ses etkinliği algılama kullanır. Yapılandırılabilir uzun sessizlik uyarısı toplantıyı otomatik bitirmez; önce kullanıcıya sorar.
* **FLM ASR**, **Standart Whisper** ve sabit **Whisper large-v3** transkripsiyon modlarını destekler.
* İsteğe bağlı `pyannote.audio` ile toplantı genelinde konuşmacı ayrımı yapar. Online modda yerel mikrofon `BEN` olarak korunur, uzak konuşmacılar mümkün olduğunda ayrılır.
* Toplantı analizi için FLM, Ollama ve LM Studio desteklenir. Uzun transkriptler sessizce kesilmek yerine parça/birleştirme yaklaşımıyla işlenir.
* Toplantı başlığı, katılımcılar, amaç, kısa özet, ayrıntılı notlar, kararlar, riskler ve aksiyon maddeleri üretir.
* Toplantı bittiğinde kayıt alanı hemen serbest kalır; kalan ASR, konuşmacı ayrımı ve özetleme işleri toplantı bazlı arka plan kuyruğunda sürer.
* Bekleyen ve tamamlanan toplantıları SQLite içinde saklar.
* Arama ve tarih filtresi bulunan geçmiş toplantı arşivi ile ayrı özet/transkript sekmeleri sunar.
* Başlık, katılımcılar, özet ve transkript düzenlenip kaydedilebilir. Zengin metin editörü kalın, italik, altı çizili, punto, renk, bul/değiştir, büyük-küçük harf ve tümünü değiştir işlevlerini içerir.
* Eski transkriptler seçili LLM ile yeniden analiz edilebilir.
* Toplantı notları varsayılan e-posta uygulamasında `mailto:` taslağı olarak açılabilir.
* Windows COM üzerinden Outlook veya Outlook/ICS dışa aktarma adresi okunabilir; bugünün toplantıları ve sıradaki toplantı gösterilir, toplantı zamanı yaklaşınca önde bildirim açılabilir.
* Sistem tepsisinde çalışmaya devam eder; açıkça çıkış verildiğinde uygulamanın başlattığı servisleri ve modelleri kapatır.

### 2. Chatbot-RAG

* Birden fazla ajan oluşturma, yeniden adlandırma ve silme sunar. Her ajan kendi adını, sistem promptunu, RAG ve bilgisayar kontrolü izinlerini, konuşmalarını, mesajlarını, belgelerini ve yenilenebilir embed anahtarını saklar.
* Ajanlar ayrı model sabitlemez; modülün üstündeki ortak LLM, embedding, STT, konuşma dili ve TTS ayarlarını kullanır.
* LLM sağlayıcıları: düzenlenebilir model/endpoint ile **FastFlowLM**, **Ollama**, **LM Studio**. Bilinen yerel varsayılan portlar FLM `52625`, Ollama `11434`, LM Studio `1234`.
* Embedding sağlayıcıları: yerel Hugging Face **SentenceTransformers** veya **FastFlowLM embedding**. Varsayılan yerel model `intfloat/multilingual-e5-small`; uyumlu başka model kimliği yazılabilir. E5 modellerinde `query:` ve `passage:` önekleri otomatik uygulanır.
* STT sağlayıcıları: **FLM Whisper / ASR** ve **faster-whisper**. Konuşma dili otomatik, Türkçe veya İngilizce seçilebilir. FLM varsayılanı `whisper-v3:turbo`dur.
* TTS varsayılanı hafif Türkçe Coqui modeli `tts_models/tr/common-voice/glow-tts`tir. Mikrofon ve ses çıkışı ayrı seçilebilir.
* Sohbette hareketli düşünme durumu ve hızlı yazma efekti bulunur. Sohbeti bitirmek tutulan Chatbot-RAG modelini açıkça bellekten çıkarır.
* Konuşmalar ve mesajlar ajan bazında SQLite içinde kalıcı tutulur.

#### RAG belge akışı

1. PDF, DOCX, TXT veya Markdown dosyasını `chatbot_rag_data/documents/<agent-id>/` altına yükleyin.
2. Yeni belgeler için **İndeksle** düğmesine basın; yükleme seçildiği anda indeksleme başlamaz.
3. Seçili embedding ayarıyla mevcut belgeleri yenilemek için **Yeniden indeksle** kullanın.
4. Belgeler ajan bazında SHA-256 ile yinelenmeye karşı korunur.
5. Metin yaklaşık 350 kelimelik ve 50 kelime örtüşmeli parçalara ayrılır; PDF sayfası, DOCX paragrafı ve metin konum bilgileri korunur.
6. Vektörler `chatbot_rag_data/vector_db/` altındaki telemetrisiz kalıcı Chroma veritabanına yazılır ve ajan kimliğiyle izole edilir.
7. Sorguda en yakın sekiz parça alınır. Yapılandırılmış kaynak metadata’sı API için korunur, masaüstü TTS tarafından okunmaz.
8. Metin katmanı olmayan taranmış PDF’ler desteklenmiyor olarak bildirilir; OCR yapılmaz.
9. Embedding modeli/endpoint’i bazlı koleksiyon adları sayesinde farklı modelin eski koleksiyonu yeni indeks hazırlanmadan silinmez.

#### Sesli sohbet yaşam döngüsü

* Sesli mod açılmadıkça STT/TTS başlatılmaz; uygulama açılışında yüklenmez.
* FLM gerekli `--embed 1` ve `--asr 1` seçenekleriyle seçili LLM, embedding ve ASR’yi aynı `52625` portunda çalıştırabilir.
* Mikrofon konuşmayı algılar ve yaklaşık 1,6 saniye sessizlikten sonra cümleyi tamamlar.
* Transkripsiyon ve TTS sırasında mikrofon durur; ajan kendi yanıtını yeni komut olarak duymaz.
* İlk Coqui kullanımında uyumlu bağımlılıklar denetlenir, model uygulama klasörüne bir kez indirilir ve sesli mod açıkken önbellekte tutulur.
* Kaynak işaretleri, kaynak bölümleri ve Markdown biçimi seslendirme öncesi temizlenir.

### 3. Güvenli Bilgisayar Kontrolü

Bilgisayar kontrolü her yeni ajanda **varsayılan olarak kapalıdır** ve hem yönlendirme hem çalıştırma katmanında denetlenir. LLM yalnız katı eylem kimliği ve doğrulanmış JSON parametreleri seçebilir; executable yolu, shell/PowerShell metni, rastgele URL veya kod veremez.

Onaysız bilgi sorguları:

* Outlook/ICS üzerinden önümüzdeki 30 günün sıradaki toplantısı ve en fazla on yaklaşan toplantı.
* Görünür uygulamalar, öndeki pencere, CPU, RAM, disk, pil, yerel IP, Windows bilgisi ve ana ses/sessiz durumu.
* İzin listesindeki uygulamaların kurulu/kullanılabilir olup olmadığı.

İzin listeli açma ve pencere eylemleri:

* Outlook, Teams, Chrome, Edge, Word, Excel, PowerPoint, Dosya Gezgini, Ayarlar, Denetim Masası, Görev Yöneticisi, Not Defteri, Hesap Makinesi, Paint, Ekran Alıntısı Aracı, Fotoğraflar, Kamera, Windows Terminal ve PowerShell. Terminal/PowerShell yalnız açılır; içine komut yazılmaz.
* C sürücüsü, projeler kökü, Belgeler, İndirilenler, Masaüstü, Resimler ve uygulama çıktı klasörü.
* Kullanıcının verdiği mevcut mutlak Windows klasör yolu; doğrulama ve açık onayla.
* YouTube ana sayfası veya doğrulanmış YouTube araması; önce Chrome, yoksa varsayılan tarayıcı.
* Görünür pencereyi öne getirme, küçültme, büyütme veya geri yükleme.
* Oynat/duraklat, sonraki parça ve önceki parça medya tuşları.

Desteklenen Windows Ayarları sayfaları: ses, ses mikseri, mikrofon, hoparlör, Wi-Fi, ağ durumu, Ethernet, VPN, proxy, mobil erişim noktası, Bluetooth, bağlı cihazlar, ekran, bildirimler, güç, pil, depolama, varsayılan uygulamalar, Windows Update, isteğe bağlı özellikler, yazıcılar, kamera/mikrofon gizliliği, tarih/saat, dil, arka plan, görev çubuğu, erişilebilirlik, Hakkında ve yüklü uygulamalar.

Ana ses seviyesini değiştirme, sessize alma/açma, pencere kapatma ve kullanıcının verdiği klasör yolunu açma masaüstünde onay ister. Her bilgisayar eylemi güvenli parametreleri, onay durumu, sonucu ve zamanıyla `pc_action_log` tablosuna yazılır.

Bilerek desteklenmeyenler: üretilmiş PowerShell/CMD, rastgele executable/URL, koordinatla tıklama, serbest klavye otomasyonu, Wi-Fi/Bluetooth adaptörünü doğrudan değiştirme, dosya silme/taşıma/yeniden adlandırma, kapatma/yeniden başlatma/uyku/oturum kapatma, e-posta veya Teams mesajı gönderme, toplantı oluşturma/değiştirme, parola/çerez/pano okuma ve web widget üzerinden PC kontrolü.

### 4. Yerel Web Chatbot Widget

* Masaüstü uygulaması açıkken yalnız `127.0.0.1:8765` üzerinde başlar.
* Seçili ajanı yenilenebilir anahtarla şu biçimde yayımlar:

```html
<script src="http://127.0.0.1:8765/widget.js" data-agent-token="..."></script>
```

* Shadow DOM kullanır; yazılı sohbet, tarayıcı mikrofonu, sessizlikle cümle tamamlama, transkripsiyon ve isteğe bağlı sesli yanıt sunar.
* Uçlar: `GET /health`, `GET /widget.js`, `GET /api/agent`, `POST /api/chat`, `POST /api/transcribe`, `POST /api/tts`.
* PC kontrol araçları web promptuna hiç eklenmez; masaüstü ajanında izin olsa bile web istekleri zorla `pc_control=false` çalışır.

### 5. Shorts Studio

* YouTube URL, çıktı kökü, 1–10 klip adayı, 60/90/180 saniye azami süre, yerel model adı ve isteğe bağlı zaman aralıklarıyla proje oluşturur.
* Bağımlılıkları otomatik seçilen adımlar sunar: video indirme, yalnız ses indirme, altyazı/transkript edinme, transkript temizleme, ChatGPT aday analizi, seçili short’ları render etme, sarı altyazı gömme ve metadata TXT üretme.
* Mevcut üretici/otomatik altyazıları dil sırasıyla dener; indirme başarısız olursa Whisper transkripsiyonuna düşer.
* ChatGPT promptu hazırlayıp kopyalayabilir, yapıştırılmış JSON sonucu uygulayabilir veya kullanıcı oturum açtıktan sonra kalıcı ChatGPT Browser Assist oturumunu kullanabilir.
* Aday zamanlarını doğrular; render seçimi, başlangıç/bitiş, süre, puan, başlık ve neden alanlarını tabloda gösterir.
* FFmpeg ile doğrulanmış dikey `1080x1920` MP4 üretir, render başına log yazar, altyazıyı render sırasında gömer ve Türkçe başlık/açıklama/etiket metadata’sı üretir.
* Seçili FLM model oturumları Not Tutucu ile koordine edilir; uyumsuz ağır yerel modeller gizlice aynı anda yüklenmez.

### 6. YouTube İndirici

* Tek URL veya her satırda birden fazla URL kabul eder.
* Tek video ya da tam playlist/liste indirebilir.
* Birleştirilmiş MP4 video veya en iyi kalite MP3 çıkarımı sunar.
* Varsa paketlenmiş `tools/yt-dlp.exe` / `tools/ffmpeg.exe`, yoksa `PATH` üzerindeki `yt-dlp` ve `ffmpeg` kullanılır.
* Birleşik ilerleme ve ayrıntılı log gösterir, güvenli numaralı dosya adları üretir ve iptal destekler.

### 7. Ayarlar, Günlükler, Dil ve Tarayıcı Köprüsü

* Genel dil seçimi tüm modül sekmelerinin üstündedir. Windows görüntü dili Türkçeyse Türkçe, değilse İngilizce varsayılan gelir.
* Ayarlar/Günlükler; modül durumlarını, veritabanı yolunu, etkin ASR/LLM, diarization, sessizlik uyarısı, kuyruk uzunluğu ve son `error_log.txt` kayıtlarını gösterir.
* ChatGPT Browser Bridge kalıcı Chrome profili açabilir, elle ChatGPT oturumu açılmasını bekler, test promptu gönderir ve görünür yanıtı geri alır. Tarayıcı parola veya çerezlerini okumaz.

---

## 🗄️ Yerel Veri ve Model Dizini

| Yol | Amaç |
| --- | ---- |
| `taklino_notes.db` | Toplantılar, ayarlar, ajanlar, belgeler, konuşmalar, mesajlar ve PC eylem günlüğü |
| `chatbot_rag_data/documents/<agent-id>/` | Ajana özel içe aktarılan belge kopyaları |
| `chatbot_rag_data/vector_db/` | Kalıcı Chroma vektör koleksiyonları |
| `models/chatbot_rag/embeddings/` | Yerel SentenceTransformers önbelleği |
| `models/chatbot_rag/tts/` | Coqui modeli ve Numba önbelleği |
| `downloads/` | YouTube İndirici varsayılan çıktısı |
| `output/shorts_studio/` | Shorts Studio projeleri ve render çıktıları |
| `error_log.txt` | Oluştuğunda son yerel uygulama hataları |

Modeller, indirilen medya, tarayıcı profilleri, yerel belgeler, vektör verileri, günlükler ve veritabanı dosyaları uygun biçimde Git dışında tutulur.

---

## ♻️ Tembel Model ve Servis Yaşam Döngüsü

* Masaüstü penceresi açıldı diye LLM, embedding, Whisper, diarization veya TTS modeli yüklenmez.
* Not Tutucu seçili Whisper modelini kayıt başlayınca hazırlar; kayıt ve arka plan kuyruğu boşaldığında önbellekleri serbest bırakır.
* Chatbot-RAG seçili LLM’i mesajlar arasında açık tutar; sohbet bitince, ajan değişince veya uygulama kapanınca bırakır.
* Yerel embedding indeksleme için geçici yüklenir ve etkin RAG oturumu gerektirdiği sürece kullanılabilir.
* Sesli modla STT/TTS başlar; TTS sırasında mikrofon durur.
* Ortak model oturum koordinatörü Not Tutucu ile Chatbot-RAG/Shorts Studio’nun uyumsuz FLM modellerini birbirinin üstüne yüklemesini engeller.
* Yerel FastAPI servisi ve uygulamanın başlattığı FLM/model süreçleri açıkça çıkış sırasında kapatılır.

---

## 🧠 AI Sağlayıcı Seçenekleri

Local AI Suite içinde **transkripsiyon sağlayıcısı** ve **özetleme / analiz sağlayıcısı** ayrı seçilebilir.

### Transkripsiyon Sağlayıcıları

| Sağlayıcı        | En Uygun Kullanım              | Not                                            |
| ---------------- | ------------------------------ | ---------------------------------------------- |
| FastFlowLM ASR   | AMD Ryzen AI / NPU sistemler   | AMD NPU ve FLM varsa varsayılan gelir          |
| Standart Whisper | Uyumlu herhangi bir Windows PC | `faster-whisper` kullanır, AMD NPU gerektirmez |
| Whisper v3       | Doğruluk odaklı yerel STT       | Açıkça `large-v3` faster-whisper modelini kullanır |

Yerel Whisper sağlayıcılarında seçili model, kayıt başladığında otomatik olarak hazırlanır. Toplantı bitince kuyruktaki transkripsiyon ve varsa konuşmacı ayrımı tamamlanır; özetleme LLM'i başlamadan önce Whisper bellekten çıkarılır, böylece iki büyük model aynı anda RAM/VRAM'de tutulmaz.

### Opsiyonel Konuşmacı Ayrımı

Özetlemeden önce nihai transkripti toplantı genelinde tutarlı konuşmacı etiketleriyle yenilemek için transkripsiyon alanındaki **Pyannote ile konuşmacıları ayır** seçeneğini açın. Yalnız mikrofon modunda odadaki tüm konuşmacılar ayrılır; online modda yerel mikrofon `BEN` olarak korunurken uzaktaki sesler ayrılır. İlk kullanım öncesinde `requirements-diarization.txt` dosyasını kurun, Hugging Face üzerinde `pyannote/speaker-diarization-community-1` koşullarını kabul edin ve `HF_TOKEN` tanımlayın (veya `hf auth login` çalıştırın). Diarization çalışamazsa uygulama canlı transkripti koruyarak güvenli biçimde devam eder.

### Özetleme / LLM Sağlayıcıları

| Sağlayıcı  | En Uygun Kullanım                      | Not                                    |
| ---------- | -------------------------------------- | -------------------------------------- |
| FastFlowLM | AMD NPU sistemler                      | Destekli AMD NPU cihazlarda varsayılan |
| Ollama     | NVIDIA GPU / genel yerel LLM kullanımı | Opsiyonel; kurulum önerilebilir        |
| LM Studio  | AMD GPU / genel yerel LLM kullanımı    | Opsiyonel; kurulum önerilebilir        |

---

## 🖥️ Donanıma Göre Davranış

### AMD NPU Varsa

AMD NPU ve FastFlowLM algılanırsa:

* FastFlowLM varsayılan olarak seçilir
* Canlı transkripsiyon için FLM ASR kullanılabilir
* Toplantı analizi için FLM LLM kullanılabilir
* İstenirse Ollama veya LM Studio da seçilebilir

### AMD NPU Yoksa

AMD NPU algılanmazsa:

* Uygulama yine açılır
* FastFlowLM zorunlu tutulmaz
* Transkripsiyon için Standart Whisper kullanılabilir
* Özetleme için Ollama veya LM Studio kullanılabilir
* Kurulum sırasında opsiyonel sağlayıcılar önerilebilir

---

## 💬 Chatbot-RAG ve Sesli Asistan

Her biri ayrı ad, sistem promptu, kalıcı sohbet geçmişi, isteğe bağlı RAG bağlamı ve isteğe bağlı güvenli bilgisayar kontrolü izni taşıyan yerel ajanlar oluşturulabilir. Ajanlar modülün üst bölümünde seçilen ortak LLM, embedding, STT ve TTS ayarlarını kullanır.

Belgeler indekslemeden önce arayüze yüklenir, ajan içinde yinelenen dosyalar engellenir, kaynak bilgisi korunarak parçalara ayrılır ve SentenceTransformers veya FastFlowLM embedding ile uygulama klasöründeki Chroma veritabanına yazılır. PDF, DOCX, TXT ve Markdown desteklenir. RAG kaynakları yapılandırılmış metadata olarak korunur, TTS tarafından okunmaz.

Sesli mod mikrofon etkinliğini algılar ve yaklaşık 1,6 saniyelik sessizlikten sonra cümleyi tamamlar. FLM Whisper Turbo ve standart faster-whisper desteklenir; mikrofon ve hoparlör ayrı seçilebilir. Modeller uygulama açılışında değil, ajan, servis veya sesli mod başlatıldığında yüklenir ve etkin oturum yaşam döngüsüne göre bellekten çıkarılır.

Bilgisayar kontrolleri yalnız masaüstünde ve doğrulanmış eylem kataloğuyla çalışır. LLM tarafından üretilen serbest PowerShell komutları, koordinatla tıklama ve web widget üzerinden bilgisayar kontrolü desteklenmez.

Yerel widget servisi yalnız `127.0.0.1:8765` adresini dinler ve masaüstü uygulaması açıkken seçili ajanı yayımlar.

---

## 🏗️ Mimari

```text
main.py
├── ui/
│   ├── splash.py                 → Başlangıç ekranı ve ortam kontrolleri
│   └── main_window.py            → Ana uygulama arayüzü
├── core/
│   ├── hw_check.py               → Donanım ve sağlayıcı kontrolü
│   ├── flm_manager.py            → FastFlowLM servis yönetimi
│   ├── audio_capture.py          → Sistem ve mikrofon ses yakalama
│   ├── asr_client.py             → FastFlowLM ASR / Standart Whisper transkripsiyon
│   ├── llm_analyzer.py           → FLM / Ollama / LM Studio analiz sağlayıcısı
│   ├── model_session_manager.py  → Model ve oturum yönetimi
│   ├── chatbot_runtime.py        → Sohbet, RAG ve güvenli eylem yönlendirme
│   ├── chat_voice.py             → Tembel yüklenen STT/TTS işçileri ve model önbelleği
│   ├── rag_store.py              → Belge çıkarma ve kalıcı vektörler
│   ├── pc_control.py             → İzin listeli Windows eylem kataloğu
│   └── shorts_pipeline.py        → Shorts Studio işlem akışı
├── modules/
│   ├── chatbot_rag.py            → Ajan, belge, sohbet, ses ve widget arayüzü
│   ├── shorts_studio.py          → Shorts Studio modülü
│   └── youtube_downloader.py     → Video indirme yardımcısı
├── services/
│   ├── chatbot_web_service.py    → Yalnız yerelde çalışan FastAPI chatbot widget
│   └── chatgpt_browser_bridge.py → Tarayıcı otomasyon köprüsü
├── database/
│   └── db_manager.py             → SQLite yerel veritabanı
├── utils/
│   └── email_sender.py           → E-posta gönderim yardımcısı
└── assets/
    └── icon.ico / icon.png       → Uygulama ikonları
```

---

## 🔧 Manuel Kullanım

Bağımlılıkları manuel kurmak için:

```bash
pip install -r requirements.txt
```

Uygulamayı başlatmak için:

```bash
python main.py
```

---

## ❓ Sık Sorulan Sorular

### AMD NPU zorunlu mu?

Hayır. AMD NPU, FastFlowLM deneyimi için önerilir ama artık zorunlu değildir. AMD NPU olmayan kullanıcılar transkripsiyon için Standart Whisper, özetleme için Ollama veya LM Studio kullanabilir.

### Varsayılan kurulum nasıl çalışır?

AMD NPU olan sistemlerde FastFlowLM varsayılan sağlayıcı olarak gelir.

### FastFlowLM yerine Standart Whisper kullanabilir miyim?

Evet. Note Taker bölümünde canlı transkripsiyon sağlayıcısı olarak Standart Whisper seçilebilir.

### Ollama veya LM Studio kullanabilir miyim?

Evet. Ollama ve LM Studio, özetleme ve analiz için opsiyonel yerel LLM sağlayıcılarıdır.

### Uygulama her şeyi otomatik kuruyor mu?

`setup.bat`; PDF/DOCX okuyucuları, Chroma, SentenceTransformers, FastAPI/Uvicorn, faster-whisper, ses desteği ve Coqui TTS çalışma zamanı dahil `requirements.txt` içindeki Python paketlerini kurar. İsteğe bağlı pyannote konuşmacı ayrımı ayrı gereksinimlere ve Hugging Face erişim koşullarına sahiptir. FastFlowLM, Ollama ve LM Studio ayrı sağlayıcı uygulamalarıdır; kurulum bunları algılar ve desteklenen durumda kurulum yolu önerebilir. Model ağırlıkları özellik ilk kez kullanıldığında bir kez kontrol edilir veya indirilir; kurulum gerektiğinde kullanıcı onayı alınır.

### Ajanın çalışması için RAG dokümanı zorunlu mu?

Hayır. Ajan yalnız adı ve sistem promptuyla normal sohbet edebilir. Yanıtların özel bir doküman koleksiyonunu kullanması isteniyorsa RAG açılır ve belgeler yüklenip indekslenir. Her ajan yalnız kendi indekslenmiş belgelerinde arama yapar.

### LLM her soruda yeniden mi yükleniyor?

Hayır. Sohbet başlatılınca seçili ortak LLM gerektiğinde yüklenir veya servisi başlatılır ve mesajlar arasında hazır tutulur. **Sohbeti Bitir**, ajan değiştirme veya uygulamayı kapatma Chatbot-RAG oturumunu serbest bırakır. Sesli STT/TTS de sesli mod açık kaldığı sürece hazır tutulur ve mod kapanınca bırakılır.

### Chatbot-RAG'in hangi bölümleri yereldir?

İçe aktarılan belgeler, Chroma vektörleri, ajanlar, konuşmalar ve mesajlar yerelde saklanır. SentenceTransformers embedding, faster-whisper STT, Coqui TTS ve yerel yapılandırılmış FLM/Ollama/LM Studio endpoint'leri bilgisayarda çalışır. Veriler ancak kullanıcı yerel olmayan bir endpoint'i açıkça seçerse veya YouTube, ICS ya da ChatGPT Browser Assist gibi ağ/tarayıcı entegrasyonlarını kullanırsa bilgisayar dışına çıkabilir.

### FLM servisi başlamıyor. Ne yapmalıyım?

FastFlowLM komutunun terminalde çalıştığını kontrol edin. FLM yoksa veya AMD NPU bulunmuyorsa transkripsiyon sağlayıcısını Standart Whisper, LLM sağlayıcısını ise Ollama veya LM Studio olarak değiştirebilirsiniz.

### Model yükleme uzun sürüyor. Normal mi?

Evet. İlk model yüklemesi donanımınıza ve seçtiğiniz sağlayıcıya göre uzun sürebilir. Sonraki kullanımlarda genellikle daha hızlı olur.

---

## ⚠️ Notlar

* Toplantı verileri yerel olarak saklanır.
* Yerel çıktı klasörleri, tarayıcı profilleri, indirilen videolar, modeller ve log dosyaları Git’e eklenmemelidir.
* Sağlayıcıların çalışması yerel makine kurulumunuza bağlıdır.
* Ollama ve LM Studio performansı CPU/GPU/RAM durumuna göre değişir.

---

## ❤️ Geliştirici

Made with ❤️ by Serhat

📺 **Geliştirici YouTube Kanalı:**
[Teknoloji ve Hayat](https://www.youtube.com/@TeknolojiHayat)
