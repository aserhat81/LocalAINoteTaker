# Local AI Note Taker by Serhat
### Powered by AMD NPU · FastFlowLM · Whisper · Gemma3

🌍 **[Türkçe versiyon için aşağı kaydırın](#-türkçe)**

Record, transcribe, and auto-summarize your meetings using **local artificial intelligence**. The entire process runs on your NPU, requiring no internet connection.

---

## ⚡ Installation (One-Click)

### Prerequisites
| Requirement | Status |
|---|---|
| Windows 10/11 | ✅ Required |
| AMD Ryzen AI / NPU supported processor | ✅ Required |
| [Python 3.11+](https://www.python.org/downloads/) | ✅ Required |
| [FastFlowLM](https://github.com/FastFlowLM/FastFlowLM/releases/latest/download/flm-setup.exe) | ✅ Required (setup.bat downloads it automatically) |

### Setup Steps

```
1. Download or clone this repo
   git clone https://github.com/yourusername/local-ai-note-taker

2. Double click the setup.bat file
   → Python dependencies are installed automatically
   → AMD NPU check is performed
   → Offers to download FastFlowLM if missing
   → Desktop shortcut is created
```

### Start the Application
- Double click the **"Local AI Note Taker"** shortcut on your desktop  
- or double click the `run.bat` file  
- or in the terminal: `python main.py`

---

## 🎯 Features

| Feature | Description |
|---|---|
| 🎤 **System + Microphone Recording** | Audio from both sources for online meetings |
| 🎙️ **Microphone Only** | For physical meetings and dictation |
| 📝 **Real-Time Subtitles** | NPU-powered instant transcription via Whisper |
| 🤖 **AI Analysis** | Automatic title, summary, and participant detection via Gemma3 |
| 📂 **Meeting Archive** | All meetings are stored in a local database |
| 📧 **Send Email** | Share meeting notes via email with a single click |
| 🔒 **100% Local** | Your data is never sent to the cloud |

---

## 🏗️ Architecture

```
main.py
├── ui/
│   ├── splash.py        → Welcome screen (NPU & FLM check)
│   └── main_window.py   → Main UI
├── core/
│   ├── hw_check.py      → AMD NPU detection
│   ├── flm_manager.py   → FastFlowLM service management
│   ├── audio_capture.py → System + Mic audio capture
│   ├── asr_client.py    → Whisper ASR API client
│   └── llm_analyzer.py  → Gemma3 LLM analysis client
├── database/
│   └── db_manager.py    → SQLite meeting database
└── utils/
    └── email_sender.py  → Email dispatch helper
```

---

## 🔧 Manual Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Start the application
python main.py
```

---

## ❓ Frequently Asked Questions

**FLM service doesn't start?**  
→ Test `flm serve gemma3:4b --asr 1` command in the terminal. If it works, the app will auto-detect it.

**Model loading takes too long?**  
→ Whisper (~30s) + Gemma3 (~90s) is expected on the VERY first load. It will be much faster afterwards.

**No AMD NPU found?**  
→ Requires the Ryzen AI series (7000+, 8000+, 9000+ series). Unsupported processors: AMD Ryzen 5000 and older.

---

**Attention:** This application was developed specifically featuring hardware acceleration via the **AMD NPU** (Neural Processing Unit).

*Made with ❤️ by Serhat | Powered by AMD NPU, FastFlowLM, Whisper, Gemma3*
<br>
📺 **Developer YouTube Channel:** [Teknoloji ve Hayat](https://www.youtube.com/@TeknolojiHayat)


<br><br><br>

# 🇹🇷 Türkçe

Toplantılarınızı **yerel yapay zeka** ile kaydedin, metne dönüştürün ve otomatik özetleyin. Tüm işlem NPU üzerinde, internet bağlantısı gerekmez.

---

## ⚡ Kurulum (tek tıkla)

### Ön gereksinimler
| Gereksinim | Durum |
|---|---|
| Windows 10/11 | ✅ Zorunlu |
| AMD Ryzen AI / NPU destekli işlemci | ✅ Zorunlu |
| [Python 3.11+](https://www.python.org/downloads/) | ✅ Zorunlu |
| [FastFlowLM](https://github.com/FastFlowLM/FastFlowLM/releases/latest/download/flm-setup.exe) | ✅ Zorunlu (setup.bat otomatik indirir) |

### Kurulum adımları

```
1. Bu repoyu indirin veya klonlayın
   git clone https://github.com/kullaniciadiniz/local-ai-note-taker

2. setup.bat dosyasına çift tıklayın
   → Python bağımlılıkları otomatik yüklenir
   → AMD NPU kontrolü yapılır
   → FastFlowLM yoksa indirme teklif edilir
   → Masaüstü kısayolu oluşturulur
```

### Uygulamayı başlat
- Masaüstündeki **"Local AI Note Taker"** kısayoluna çift tıkla  
- veya `run.bat` dosyasına çift tıkla  
- veya terminalde: `python main.py`

---

## 🎯 Özellikler

| Özellik | Açıklama |
|---|---|
| 🎤 **Sistem + Mikrofon Kaydı** | Online toplantılar için her iki kaynaktan ses |
| 🎙️ **Sadece Mikrofon** | Fiziksel toplantılar ve dikte için |
| 📝 **Gerçek Zamanlı Altyazı** | Whisper ile NPU destekli anlık transkripsiyon |
| 🤖 **AI Analiz** | Gemma3 ile otomatik başlık, özet ve katılımcı tespiti |
| 📂 **Toplantı Arşivi** | Tüm toplantılar yerel veritabanında saklanır |
| 📧 **E-Posta Gönderimi** | Toplantı notlarını tek tıkla e-posta ile paylaş |
| 🔒 **%100 Yerel** | Verileriniz asla buluta gönderilmez |

---

## 🏗️ Mimari

```
main.py
├── ui/
│   ├── splash.py        → Başlangıç ekranı (NPU & FLM kontrolü)
│   └── main_window.py   → Ana arayüz
├── core/
│   ├── hw_check.py      → AMD NPU tespiti
│   ├── flm_manager.py   → FastFlowLM servis yönetimi
│   ├── audio_capture.py → Sistem + Mikrofon ses yakalama
│   ├── asr_client.py    → Whisper ASR API istemcisi
│   └── llm_analyzer.py  → Gemma3 LLM analiz istemcisi
├── database/
│   └── db_manager.py    → SQLite toplantı veritabanı
└── utils/
    └── email_sender.py  → E-posta gönderim yardımcısı
```

---

## 🔧 Manuel kullanım

```bash
# Bağımlılıkları kur
pip install -r requirements.txt

# Uygulamayı başlat
python main.py
```

---

## ❓ Sık Sorulan Sorular

**FLM servisi başlamıyor?**  
→ `flm serve gemma3:4b --asr 1` komutunu terminalden test edin. Çalışıyorsa uygulama otomatik algılar.

**Model yüklemesi uzun sürüyor?**  
→ Whisper (~30sn) + Gemma3 (~90sn) ilk yüklemede beklenebilir. Bir kez yüklendi mi hızlanır.

**AMD NPU bulunamıyor?**  
→ Ryzen AI serisini (7000+, 8000+, 9000+ serisi) gerektirir. Desteklemez işlemci: AMD Ryzen 5000 ve öncesi.

---

**Dikkat:** Bu uygulama donanım ivmelendirmesi için **AMD NPU** (Neural Processing Unit) kullanılarak geliştirilmiştir.

*Made with ❤️ by Serhat | Powered by AMD NPU, FastFlowLM, Whisper, Gemma3*
<br>
📺 **Geliştirici YouTube Kanalı:** [Teknoloji ve Hayat](https://www.youtube.com/@TeknolojiHayat)
