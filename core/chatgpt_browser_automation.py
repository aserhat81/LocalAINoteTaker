import re
import time

try:
    import psutil
    import win32api
    import win32clipboard
    import win32con
    import win32gui
    import win32process
except Exception as exc:  # pragma: no cover - import error is reported at runtime.
    psutil = None
    win32api = None
    win32clipboard = None
    win32con = None
    win32gui = None
    win32process = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


CHATGPT_START_MARKER = "LOCAL_AI_SUITE_TRANSLATION_START"
CHATGPT_END_MARKER = "LOCAL_AI_SUITE_TRANSLATION_END"

BROWSER_PROCESS_NAMES = {
    "chrome.exe",
    "msedge.exe",
    "brave.exe",
    "firefox.exe",
    "opera.exe",
    "vivaldi.exe",
}


class ChatGptBrowserAutomation:
    def __init__(self, log=None, wait_timeout=900):
        self.log = log or (lambda message: None)
        self.wait_timeout = wait_timeout

    def run_translation(self, prompt):
        self._ensure_available()
        window = self._find_chatgpt_window()
        if not window:
            raise RuntimeError("ChatGPT tarayici penceresi bulunamadi. chatgpt.com'u acip giris yapili sekmeyi birak.")

        self.log(f"ChatGPT window found: {win32gui.GetWindowText(window)}")
        self._focus_window(window)
        self._send_prompt(window, prompt)
        return self._wait_for_marked_response(window)

    def _ensure_available(self):
        if IMPORT_ERROR:
            raise RuntimeError(f"Windows browser automation dependencies are unavailable: {IMPORT_ERROR}")

    def _find_chatgpt_window(self):
        windows = []

        def collect(hwnd, _extra):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd) or ""
            if not title.strip():
                return
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                name = psutil.Process(pid).name().casefold()
            except Exception:
                name = ""
            title_l = title.casefold()
            is_browser = name in BROWSER_PROCESS_NAMES or any(token in title_l for token in ["chrome", "edge", "firefox", "brave"])
            if is_browser and any(token in title_l for token in ["chatgpt", "openai", "chat.openai.com"]):
                windows.append(hwnd)

        win32gui.EnumWindows(collect, None)
        return windows[0] if windows else None

    def _focus_window(self, hwnd):
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)

    def _send_prompt(self, hwnd, prompt):
        self.log("Prompt is being pasted into ChatGPT...")
        self._click_chatgpt_composer(hwnd)
        self._set_clipboard(prompt)
        self._hotkey(win32con.VK_CONTROL, ord("V"))
        time.sleep(0.4)
        self._press(win32con.VK_RETURN)
        self.log("Prompt submitted. Waiting for ChatGPT response...")

    def _click_chatgpt_composer(self, hwnd):
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        x = left + max(200, (right - left) // 2)
        y = bottom - 140
        win32api.SetCursorPos((x, y))
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
        time.sleep(0.3)

    def _wait_for_marked_response(self, hwnd):
        deadline = time.time() + self.wait_timeout
        last_seen = ""
        stable_seen_at = None

        while time.time() < deadline:
            self._focus_window(hwnd)
            page_text = self._copy_page_text()
            marked = extract_marked_response(page_text)
            if marked:
                if marked == last_seen:
                    if stable_seen_at and time.time() - stable_seen_at >= 8:
                        self.log("ChatGPT marked response captured.")
                        return marked
                else:
                    last_seen = marked
                    stable_seen_at = time.time()
                    self.log("Marked response detected; waiting for it to finish...")
            time.sleep(4)

        raise RuntimeError("ChatGPT response marker bulunamadi veya cevap zamaninda tamamlanmadi.")

    def _copy_page_text(self):
        self._press(win32con.VK_ESCAPE)
        time.sleep(0.1)
        self._hotkey(win32con.VK_CONTROL, ord("L"))
        time.sleep(0.1)
        self._press(win32con.VK_ESCAPE)
        time.sleep(0.1)
        self._hotkey(win32con.VK_CONTROL, ord("A"))
        time.sleep(0.1)
        self._hotkey(win32con.VK_CONTROL, ord("C"))
        time.sleep(0.3)
        return self._get_clipboard()

    def _set_clipboard(self, text):
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        finally:
            win32clipboard.CloseClipboard()

    def _get_clipboard(self):
        win32clipboard.OpenClipboard()
        try:
            if not win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                return ""
            return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT) or ""
        finally:
            win32clipboard.CloseClipboard()

    def _hotkey(self, *keys):
        for key in keys:
            self._key_down(key)
        for key in reversed(keys):
            self._key_up(key)

    def _press(self, key):
        self._key_down(key)
        self._key_up(key)

    def _key_down(self, key):
        win32api.keybd_event(key, 0, 0, 0)
        time.sleep(0.03)

    def _key_up(self, key):
        win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.03)


def with_response_markers(prompt):
    return (
        prompt.rstrip()
        + "\n\nCevabini kesinlikle su iki marker arasinda ver:\n"
        + f"{CHATGPT_START_MARKER}\n"
        + "TSV satirlari burada olacak\n"
        + f"{CHATGPT_END_MARKER}\n"
        + "Marker disinda hicbir aciklama yazma."
    )


def extract_marked_response(text):
    pattern = re.compile(
        rf"{re.escape(CHATGPT_START_MARKER)}\s*(.*?)\s*{re.escape(CHATGPT_END_MARKER)}",
        re.DOTALL | re.IGNORECASE,
    )
    matches = pattern.findall(text or "")
    if not matches:
        return ""
    return matches[-1].strip()
