import subprocess
import os
import shutil


def _winget_list_matches(*needles):
    if not shutil.which("winget"):
        return False
    try:
        result = subprocess.run(
            ["winget", "list"],
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        text = (result.stdout or "").lower()
        return any(needle.lower() in text for needle in needles)
    except Exception:
        return False

def check_amd_npu():
    """
    Checks if an AMD NPU or IPU or Ryzen AI device is present using PowerShell.
    Returns:
        bool: True if AMD NPU is detected, False otherwise.
    """
    try:
        # PnPDevice sorgusu ile aygıt yöneticisinde NPU varlığını kontrol eder
        cmd = 'powershell -Command "Get-CimInstance Win32_PnPEntity | Where-Object Name -match \'AMD NPU|AMD IPU|Ryzen AI|Radeon 890M|Radeon 780M\' | Select-Object -ExpandProperty Name"'
        result = subprocess.check_output(cmd, shell=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
        
        if result:
            return True
        return False
    except Exception as e:
        print(f"NPU Check Error: {e}")
        return False

def check_flm_installed():
    """
    Checks if FastFlowLM is installed and accessible in PATH or default directories.
    Returns:
        bool: True if installed, False otherwise.
    """
    # 1. Check if 'flm' is in PATH
    if shutil.which("flm"):
        return True
    
    # 2. Check default installation directories
    default_paths = [
        r"C:\Program Files\flm\flm.exe",
        r"C:\Program Files (x86)\flm\flm.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\flm\flm.exe")
    ]
    
    for path in default_paths:
        if os.path.exists(path):
            return True
            
    return False


def check_ollama_installed():
    return shutil.which("ollama") is not None or _winget_list_matches("ollama")


def check_lm_studio_installed():
    known_paths = [
        os.path.expanduser(r"~\AppData\Local\Programs\LM Studio\LM Studio.exe"),
        os.path.expanduser(r"~\AppData\Local\LM-Studio\LM Studio.exe"),
        r"C:\Program Files\LM Studio\LM Studio.exe",
    ]
    if any(os.path.exists(path) for path in known_paths):
        return True
    return _winget_list_matches("lm studio", "lmstudio")

def get_flm_executable_path():
    """Returns the absolute path to the flm executable."""
    flm_path = shutil.which("flm")
    if flm_path:
        return flm_path
    
    default_paths = [
        r"C:\Program Files\flm\flm.exe",
        r"C:\Program Files (x86)\flm\flm.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\flm\flm.exe")
    ]
    for path in default_paths:
        if os.path.exists(path):
            return path
    return None
