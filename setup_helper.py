"""
Local AI Suite - Setup / Kurulum Yardımcısı
OS dilini okur, adım adım kurulum yapar, masaüstü kısayolu oluşturur.
"""
import sys
import os
import subprocess
import locale
import urllib.request
import shutil

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Dil tespiti ─────────────────────────────────────────────────────────────
def get_lang():
    try:
        # Python 3.11+ için modern yol
        loc = locale.getlocale()[0] or ""
        if loc.lower().startswith("tr"):
            return "tr"
    except Exception:
        pass
    try:
        import ctypes
        windll = ctypes.windll.kernel32
        lang_id = windll.GetUserDefaultUILanguage() & 0xFF
        if lang_id == 0x1F:  # Turkish LCID primary
            return "tr"
    except Exception:
        pass
    return "en"

LANG = get_lang()

TEXTS = {
    "tr": {
        "git_update":    "Git ile güncelleniyor...",
        "first_install": "İlk kurulum yapılıyor...",
        "step1":         "[1/4] Python kontrol ediliyor...",
        "step1_ok":      "[OK]  Python",
        "step2":         "[2/4] Kütüphaneler yükleniyor / güncelleniyor...",
        "step2_ok":      "[OK]  Tüm kütüphaneler hazır.",
        "step2_err":     "[HATA] Kütüphane yüklenemedi!",
        "step3":         "[3/4] AMD NPU donanımı kontrol ediliyor...",
        "step3_ok":      "[OK]  AMD NPU bulundu:",
        "step3_err":     "[UYARI] AMD NPU bulunamadı. Ryzen AI serisi gereklidir.",
        "step4":         "[4/4] FastFlowLM kontrol ediliyor...",
        "step4_ok":      "[OK]  FastFlowLM mevcut.",
        "step4_miss":    "FastFlowLM kurulu değil.",
        "step4_ask":     "İndirip kurmak ister misiniz? (e/h): ",
        "step4_dl":      "İndiriliyor... (lütfen bekleyin)",
        "step4_inst":    "Kurulum başlatıldı, tamamlayın ve Enter'a basın.",
        "step4_retry":   "Kurulumu tamamlayıp bilgisayarı yeniden başlatın.",
        "shortcut":      "Masaüstü kısayolu oluşturuluyor...",
        "shortcut_ok":   "[OK]  Kısayol oluşturuldu.",
        "shortcut_err":  "[INFO] Kısayol oluşturulamadı, run.bat kullanın.",
        "done":          "\n✓ Kurulum / Güncelleme tamamlandı!",
        "launch_ask":    "Uygulamayı şimdi başlatmak ister misiniz? (e/h): ",
    },
    "en": {
        "git_update":    "Updating via git...",
        "first_install": "First-time installation...",
        "step1":         "[1/4] Checking Python...",
        "step1_ok":      "[OK]  Python",
        "step2":         "[2/4] Installing / updating packages...",
        "step2_ok":      "[OK]  All packages ready.",
        "step2_err":     "[ERROR] Failed to install packages!",
        "step3":         "[3/4] Checking AMD NPU hardware...",
        "step3_ok":      "[OK]  AMD NPU found:",
        "step3_err":     "[WARNING] AMD NPU not found. Ryzen AI series required.",
        "step4":         "[4/4] Checking FastFlowLM...",
        "step4_ok":      "[OK]  FastFlowLM is installed.",
        "step4_miss":    "FastFlowLM is not installed.",
        "step4_ask":     "Download and install it now? (y/n): ",
        "step4_dl":      "Downloading... (please wait)",
        "step4_inst":    "Installer launched. Complete it and press Enter.",
        "step4_retry":   "Please complete the installer and restart your PC.",
        "shortcut":      "Creating desktop shortcut...",
        "shortcut_ok":   "[OK]  Desktop shortcut created.",
        "shortcut_err":  "[INFO] Could not create shortcut, use run.bat.",
        "done":          "\n✓ Setup / Update complete!",
        "launch_ask":    "Launch the app now? (y/n): ",
    }
}
T = TEXTS[LANG]


def run(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def answer_yes(value):
    return (value or "").strip().lower() in ("e", "evet", "y", "yes")


def check_python_package(module_name):
    result = subprocess.run(
        [sys.executable, "-c", f"import {module_name}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def detect_gpu_vendor():
    try:
        ps_cmd = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object -ExpandProperty Name"
        )
        result = run(f'powershell -NoProfile -Command "{ps_cmd}"')
        names = result.stdout.lower()
    except Exception:
        names = ""

    return {
        "nvidia": "nvidia" in names,
        "amd": "amd" in names or "radeon" in names,
        "names": names.strip(),
    }


def winget_available():
    return shutil.which("winget") is not None


def winget_list_matches(*needles):
    if not winget_available():
        return False
    try:
        result = subprocess.run(
            ["winget", "list"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        text = (result.stdout or "").lower()
        return any(needle.lower() in text for needle in needles)
    except Exception:
        return False


def ollama_installed():
    return shutil.which("ollama") is not None or winget_list_matches("ollama")


def lm_studio_installed():
    known_paths = [
        os.path.expanduser(r"~\AppData\Local\Programs\LM Studio\LM Studio.exe"),
        os.path.expanduser(r"~\AppData\Local\LM-Studio\LM Studio.exe"),
        r"C:\Program Files\LM Studio\LM Studio.exe",
    ]
    if any(os.path.exists(path) for path in known_paths):
        return True
    return winget_list_matches("lm studio", "lmstudio")


def install_with_winget(label, winget_args):
    if not winget_available():
        print(f"[INFO] winget bulunamadi. {label} otomatik kurulamadi.")
        return False

    print(f"{label} winget ile kuruluyor...")
    try:
        result = subprocess.run(
            ["winget", "install", *winget_args, "--accept-package-agreements", "--accept-source-agreements"],
            text=True,
        )
        return result.returncode == 0
    except Exception as exc:
        print(f"[INFO] {label} kurulumu baslatilamadi: {exc}")
        return False


# ─── Git güncelleme ───────────────────────────────────────────────────────────
print()
if os.path.isdir(os.path.join(APP_DIR, ".git")) and shutil.which("git"):
    print(T["git_update"])
    run(f'git -C "{APP_DIR}" pull --quiet')
else:
    print(T["first_install"])

# ─── 1. Python ────────────────────────────────────────────────────────────────
print()
print(T["step1"])
ver = sys.version.split()[0]
print(f"{T['step1_ok']} {ver}")

# ─── 2. pip install ───────────────────────────────────────────────────────────
print()
print(T["step2"])
req_path = os.path.join(APP_DIR, "requirements.txt")
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", req_path, "--upgrade", "--quiet"],
    capture_output=True, text=True
)
if result.returncode != 0:
    print(T["step2_err"])
    print(result.stderr)
    sys.exit(1)
print(T["step2_ok"])


# ─── 3. AMD NPU ───────────────────────────────────────────────────────────────
print()
print(T["step3"])

# hw_check modülündeki hazır fonksiyonu kullan
sys.path.insert(0, APP_DIR)
try:
    from core.hw_check import check_amd_npu, check_flm_installed
    npu_detected = check_amd_npu()
except Exception:
    npu_detected = False
    check_flm_installed = lambda: shutil.which("flm") is not None

# hw_check başarısız olursa PowerShell ile tekrar dene
ps_cmd = (
    'Get-CimInstance Win32_PnPEntity | '
    'Where-Object Name -match "AMD NPU|AMD IPU|Ryzen AI|Radeon 890M|Radeon 780M" | '
    'Select-Object -First 1 -ExpandProperty Name'
)
npu_name = run(f'powershell -NoProfile -Command "{ps_cmd}"').stdout.strip()
if npu_detected and not npu_name:
    npu_name = "AMD NPU"

if not npu_name:
    print(T["step3_err"])
else:
    print(f"{T['step3_ok']} {npu_name}")

# ─── 4. FastFlowLM ────────────────────────────────────────────────────────────
print()
print(T["step4"])
flm_exists = check_flm_installed()
if flm_exists:
    print(T["step4_ok"])
else:
    print(T["step4_miss"])
    if npu_name:
        answer = input(T["step4_ask"]).strip().lower()
    else:
        print("[INFO] AMD NPU yoksa FLM zorunlu degil. Standart Whisper + Ollama/LM Studio kullanabilirsiniz.")
        answer = input("Yine de FastFlowLM kurulsun mu? (e/h): ").strip().lower()
    if answer_yes(answer):
        print(T["step4_dl"])
        flm_exe = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "flm-setup.exe")
        urllib.request.urlretrieve(
            "https://github.com/FastFlowLM/FastFlowLM/releases/latest/download/flm-setup.exe",
            flm_exe
        )
        subprocess.Popen([flm_exe])
        print(T["step4_inst"])
        input()
        if not check_flm_installed():
            print(T["step4_retry"])
            input("\nPress Enter to exit...")
            sys.exit(1)

print()
print("[5/5] Opsiyonel yerel AI saglayicilari kontrol ediliyor...")
gpu = detect_gpu_vendor()
print("[OK]  Standart Whisper (faster-whisper) Python kutuphanesi hazir." if check_python_package("faster_whisper") else "[UYARI] faster-whisper bulunamadi. requirements kurulumu kontrol edilmeli.")
print("[OK]  Pyannote diarization hazir." if check_python_package("pyannote.audio") else "[INFO] Pyannote diarization opsiyonel; uygulamadaki secenek acilinca kurulabilir.")

ollama_ok = ollama_installed()
lm_studio_ok = lm_studio_installed()
print("[OK]  Ollama mevcut." if ollama_ok else "[INFO] Ollama kurulu degil.")
print("[OK]  LM Studio mevcut." if lm_studio_ok else "[INFO] LM Studio kurulu degil.")

if not npu_name:
    if gpu["nvidia"] and not ollama_ok:
        if answer_yes(input("NVIDIA GPU algilandi. Ollama kurulsun mu? (e/h): ")):
            install_with_winget("Ollama", ["--id", "Ollama.Ollama", "-e"])
    elif gpu["amd"] and not lm_studio_ok:
        if answer_yes(input("AMD GPU algilandi. LM Studio kurulsun mu? (e/h): ")):
            install_with_winget("LM Studio", ["--name", "LM Studio"])
    elif not ollama_ok:
        if answer_yes(input("Yerel LLM icin Ollama kurulsun mu? (e/h): ")):
            install_with_winget("Ollama", ["--id", "Ollama.Ollama", "-e"])
else:
    print("[INFO] AMD NPU bulundu; FLM varsayilan olarak kullanilabilir.")
    if not ollama_ok and answer_yes(input("Opsiyonel olarak Ollama da kurulsun mu? (e/h): ")):
        install_with_winget("Ollama", ["--id", "Ollama.Ollama", "-e"])
    if not lm_studio_ok and answer_yes(input("Opsiyonel olarak LM Studio da kurulsun mu? (e/h): ")):
        install_with_winget("LM Studio", ["--name", "LM Studio"])

# ─── Masaüstü kısayolu ────────────────────────────────────────────────────────
print()
print(T["shortcut"])
try:
    desktop = run(
        'powershell -NoProfile -Command "[Environment]::GetFolderPath(\'Desktop\')"'
    ).stdout.strip()
    shortcut_path = os.path.join(desktop, "Local AI Suite.lnk")
    old_shortcut_path = os.path.join(desktop, "Local AI Note Taker.lnk")
    main_py = os.path.join(APP_DIR, "main.py")

    # pythonw.exe tam yolunu bul (kısayol için tam yol şart)
    python_dir = os.path.dirname(sys.executable)
    pythonw_path = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw_path):
        pythonw_path = sys.executable  # pythonw yoksa python.exe kullan

    # PS1 dosyasına yaz (inline quoting sorunlarını önler)
    ps1_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "make_shortcut.ps1")
    icon_path = os.path.join(APP_DIR, "assets", "icon.ico")
    with open(ps1_path, "w", encoding="utf-8") as f:
        f.write(f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{shortcut_path}')
$s.TargetPath = '{pythonw_path}'
$s.Arguments = '"{main_py}"'
$s.WorkingDirectory = '{APP_DIR}'
$s.IconLocation = '{icon_path}'
$s.Description = 'Local AI Suite by Serhat'
$s.Save()
""")

    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1_path],
        capture_output=True, text=True
    )

    if os.path.exists(shortcut_path):
        if os.path.exists(old_shortcut_path):
            try:
                os.remove(old_shortcut_path)
            except OSError:
                pass
        print(T["shortcut_ok"])
    else:
        print(T["shortcut_err"])
        if result.stderr:
            print(f"  Detail: {result.stderr.strip()[:120]}")
except Exception as e:
    print(f"{T['shortcut_err']} ({e})")

# ─── Bitti ────────────────────────────────────────────────────────────────────
print(T["done"])
print()
answer = input(T["launch_ask"]).strip().lower()
if answer in ("e", "y", "evet", "yes"):
    subprocess.Popen(
        [shutil.which("pythonw") or sys.executable, main_py],
        cwd=APP_DIR,
        close_fds=True
    )
