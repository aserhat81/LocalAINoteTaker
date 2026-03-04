"""
Local AI Note Taker - Setup / Kurulum Yardımcısı
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
    from core.hw_check import check_amd_npu
    npu_name = check_amd_npu()
except Exception:
    npu_name = None

# hw_check başarısız olursa PowerShell ile tekrar dene
if not npu_name:
    ps_cmd = (
        'Get-CimInstance Win32_PnPEntity | '
        'Where-Object Name -match "NPU|Ryzen AI|Radeon 890M|Radeon 780M" | '
        'Select-Object -First 1 -ExpandProperty Name'
    )
    npu_name = run(f'powershell -NoProfile -Command "{ps_cmd}"').stdout.strip()

if not npu_name:
    print(T["step3_err"])
    input("\nPress Enter to exit...")
    sys.exit(1)
print(f"{T['step3_ok']} {npu_name}")

# ─── 4. FastFlowLM ────────────────────────────────────────────────────────────
print()
print(T["step4"])
flm_exists = shutil.which("flm") is not None
if flm_exists:
    print(T["step4_ok"])
else:
    print(T["step4_miss"])
    answer = input(T["step4_ask"]).strip().lower()
    if answer in ("e", "y", "evet", "yes"):
        print(T["step4_dl"])
        flm_exe = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "flm-setup.exe")
        urllib.request.urlretrieve(
            "https://github.com/FastFlowLM/FastFlowLM/releases/latest/download/flm-setup.exe",
            flm_exe
        )
        subprocess.Popen([flm_exe])
        print(T["step4_inst"])
        input()
        if not shutil.which("flm"):
            print(T["step4_retry"])
            input("\nPress Enter to exit...")
            sys.exit(1)

# ─── Masaüstü kısayolu ────────────────────────────────────────────────────────
print()
print(T["shortcut"])
try:
    desktop = run(
        'powershell -NoProfile -Command "[Environment]::GetFolderPath(\'Desktop\')"'
    ).stdout.strip()
    shortcut_path = os.path.join(desktop, "Local AI Note Taker.lnk")
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
$s.Description = 'Local AI Note Taker by Serhat'
$s.Save()
""")

    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1_path],
        capture_output=True, text=True
    )

    if os.path.exists(shortcut_path):
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
