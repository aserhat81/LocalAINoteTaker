# Local AI Suite

### Local AI Note Taker + Shorts Studio

#### FastFlowLM · Standard Whisper · Ollama · LM Studio

🌍 **[Türkçe versiyon için aşağı kaydırın](#-türkçe)**

Local AI Suite is a Windows desktop application for recording meetings, transcribing speech, summarizing notes, and creating short-form video workflows with local AI tools.

The app was originally designed around **AMD NPU + FastFlowLM**, but it now also supports standard local alternatives. AMD NPU users get **FastFlowLM as the default experience**, while users without AMD NPU can still use **Standard Whisper**, **Ollama**, or **LM Studio** depending on their hardware and preference.

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
| Ollama             | Optional local LLM provider                  |
| LM Studio          | Optional local LLM provider                  |
| FFmpeg / yt-dlp    | Used by Shorts Studio workflows              |

---

## 🚀 Setup

```bash
git clone https://github.com/aserhat81/LocalAINoteTaker.git
cd LocalAINoteTaker
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
| 🎤 System + Microphone Recording | Capture both system audio and microphone audio for online meetings                 |
| 🎙️ Microphone Only Mode         | Record physical meetings, dictation, or voice notes                                |
| 📝 Live Transcription            | Use FastFlowLM ASR or Standard Whisper                                             |
| 🤖 AI Meeting Analysis           | Generate titles, summaries, action items, and participant notes                    |
| 🧠 Multiple Local LLM Providers  | FastFlowLM, Ollama, and LM Studio support                                          |
| 📂 Local Meeting Archive         | Store meeting records in a local SQLite database                                   |
| 📧 Email Sharing                 | Send meeting notes via email                                                       |
| 🎬 Shorts Studio                 | Download, transcribe, and process video content for short-form workflows           |
| 🔒 Local-First Design            | Meeting data stays on your computer unless you explicitly configure external tools |

---

## 🧠 AI Provider Options

Local AI Suite separates **transcription provider** and **summary / analysis provider**.

### Transcription Providers

| Provider         | Best For                   | Notes                                           |
| ---------------- | -------------------------- | ----------------------------------------------- |
| FastFlowLM ASR   | AMD Ryzen AI / NPU systems | Default when AMD NPU and FLM are available      |
| Standard Whisper | Any compatible Windows PC  | Uses `faster-whisper`; does not require AMD NPU |

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
│   └── shorts_pipeline.py        → Shorts Studio processing pipeline
├── modules/
│   ├── shorts_studio.py          → Shorts Studio UI/module
│   └── youtube_downloader.py     → Video download helper
├── services/
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

Python dependencies and faster-whisper are handled through setup. Ollama and LM Studio are optional; the app/setup can suggest installation and ask for confirmation.

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

### Local AI Note Taker + Shorts Studio

#### FastFlowLM · Standart Whisper · Ollama · LM Studio

Local AI Suite; toplantı kaydetme, konuşmayı metne dönüştürme, toplantı notlarını özetleme ve kısa video üretim akışlarını yerel yapay zeka araçlarıyla yönetmek için geliştirilmiş Windows masaüstü uygulamasıdır.

Uygulama ilk olarak **AMD NPU + FastFlowLM** odaklı geliştirilmiştir. Ancak artık AMD NPU zorunlu değildir. AMD NPU olan sistemlerde **FastFlowLM varsayılan** olarak gelir. AMD NPU olmayan kullanıcılar ise **Standart Whisper**, **Ollama** veya **LM Studio** seçenekleriyle uygulamayı kullanabilir.

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
| Ollama             | Opsiyonel yerel LLM sağlayıcı            |
| LM Studio          | Opsiyonel yerel LLM sağlayıcı            |
| FFmpeg / yt-dlp    | Shorts Studio akışlarında kullanılır     |

---

## 🚀 Kurulum Adımları

```bash
git clone https://github.com/aserhat81/LocalAINoteTaker.git
cd LocalAINoteTaker
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
| 🎤 Sistem + Mikrofon Kaydı   | Online toplantılar için sistem sesi ve mikrofonu birlikte kaydeder |
| 🎙️ Sadece Mikrofon Modu     | Fiziksel toplantılar, dikte ve sesli notlar için                   |
| 📝 Canlı Transkripsiyon      | FastFlowLM ASR veya Standart Whisper seçilebilir                   |
| 🤖 AI Toplantı Analizi       | Başlık, özet, aksiyon maddeleri ve katılımcı notları üretir        |
| 🧠 Çoklu Yerel LLM Sağlayıcı | FastFlowLM, Ollama ve LM Studio desteği                            |
| 📂 Yerel Toplantı Arşivi     | Toplantılar yerel SQLite veritabanında saklanır                    |
| 📧 E-Posta Paylaşımı         | Toplantı notlarını e-posta ile paylaşma                            |
| 🎬 Shorts Studio             | Video indirme, transkript çıkarma ve kısa video üretim akışı       |
| 🔒 Yerel Öncelikli Tasarım   | Verileriniz varsayılan olarak bilgisayarınızda kalır               |

---

## 🧠 AI Sağlayıcı Seçenekleri

Local AI Suite içinde **transkripsiyon sağlayıcısı** ve **özetleme / analiz sağlayıcısı** ayrı seçilebilir.

### Transkripsiyon Sağlayıcıları

| Sağlayıcı        | En Uygun Kullanım              | Not                                            |
| ---------------- | ------------------------------ | ---------------------------------------------- |
| FastFlowLM ASR   | AMD Ryzen AI / NPU sistemler   | AMD NPU ve FLM varsa varsayılan gelir          |
| Standart Whisper | Uyumlu herhangi bir Windows PC | `faster-whisper` kullanır, AMD NPU gerektirmez |

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
│   └── shorts_pipeline.py        → Shorts Studio işlem akışı
├── modules/
│   ├── shorts_studio.py          → Shorts Studio modülü
│   └── youtube_downloader.py     → Video indirme yardımcısı
├── services/
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

Python bağımlılıkları ve faster-whisper kurulum tarafından yönetilir. Ollama ve LM Studio opsiyoneldir; uygulama veya setup gerektiğinde kullanıcı onayıyla kurulum önerebilir.

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
