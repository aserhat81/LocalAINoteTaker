import subprocess
import os
import shutil

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
