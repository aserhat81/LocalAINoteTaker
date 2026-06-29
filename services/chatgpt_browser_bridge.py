import json
import re
import threading
import time
import webbrowser
from pathlib import Path

try:
    import win32clipboard
    import win32con
except Exception as exc:  # pragma: no cover - reported at runtime.
    win32clipboard = None
    win32con = None
    WIN32_IMPORT_ERROR = exc
else:
    WIN32_IMPORT_ERROR = None

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except Exception as exc:  # pragma: no cover - reported at runtime.
    PlaywrightError = Exception
    sync_playwright = None
    PLAYWRIGHT_IMPORT_ERROR = exc
else:
    PLAYWRIGHT_IMPORT_ERROR = None


CHATGPT_URL = "https://chatgpt.com"
READY_ERROR = "ChatGPT input not found. Please make sure you are logged in and the chat page is open."
LOGIN_MESSAGE = "Please login in the opened Chrome window, then click Continue."
TIMEOUT_ERROR = "ChatGPT response timeout."
CHROME_NOT_FOUND = "Google Chrome not found. Please install Chrome or use manual mode."


class ChatGptBrowserBridge:
    _job_lock = threading.Lock()

    def __init__(self, user_data_dir=None, log=None):
        self.root_dir = Path(__file__).resolve().parents[1]
        self.user_data_dir = Path(user_data_dir) if user_data_dir else self.root_dir / "browser_profiles" / "chatgpt_chrome"
        self.log = log or (lambda message: None)
        self._playwright = None
        self.context = None
        self.page = None

    def open_chatgpt_session(self):
        self._ensure_available()
        self.log("Opening ChatGPT Chrome browser")
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        if not self._playwright:
            self._playwright = sync_playwright().start()
        if not self.context:
            try:
                self.context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    channel="chrome",
                    headless=False,
                    viewport={"width": 1280, "height": 900},
                    accept_downloads=False,
                )
            except PlaywrightError as exc:
                raise RuntimeError(CHROME_NOT_FOUND) from exc
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.goto(CHATGPT_URL, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_load_state("domcontentloaded", timeout=60000)
        return self.page

    def ensure_ready(self, on_login_required=None):
        self.log("Checking login/session")
        self.open_chatgpt_session()
        if self._find_chat_input(timeout_ms=5000):
            return True
        if self._security_challenge_visible():
            message = "ChatGPT verification or rate limit screen detected. Please complete it manually in the opened Chrome window, then click Continue."
            if on_login_required:
                on_login_required(message)
            else:
                raise RuntimeError(message)
            self.page.wait_for_timeout(1000)
            if self._find_chat_input(timeout_ms=15000):
                return True
        if on_login_required:
            on_login_required(LOGIN_MESSAGE)
        else:
            raise RuntimeError("Please login to ChatGPT in the opened browser window.")
        self.page.wait_for_timeout(1000)
        if self._find_chat_input(timeout_ms=15000):
            return True
        raise RuntimeError(READY_ERROR)

    def send_prompt(self, prompt_text):
        self.log("Sending prompt")
        if not prompt_text or not str(prompt_text).strip():
            raise ValueError("Prompt text is required.")
        composer = self._find_chat_input(timeout_ms=10000)
        if not composer:
            raise RuntimeError(READY_ERROR)
        self._set_clipboard(str(prompt_text))
        composer.click(timeout=10000)
        self.page.keyboard.press("Control+V")
        self.page.wait_for_timeout(400)
        send_button = self._find_send_button(timeout_ms=2500)
        if send_button:
            send_button.click(timeout=5000)
        else:
            self.page.keyboard.press("Enter")

    def wait_for_response_complete(self, timeout_seconds=300):
        self.log("Waiting for response")
        deadline = time.time() + int(timeout_seconds or 300)
        last_text = ""
        last_change = time.time()
        saw_assistant_text = False

        while time.time() < deadline:
            if self._security_challenge_visible():
                raise RuntimeError("ChatGPT verification, rate limit, or suspicious activity screen detected. Please continue manually in the opened Chrome window.")
            stop_visible = self._is_stop_generating_visible()
            current_text = self._last_assistant_text()
            if current_text:
                saw_assistant_text = True
                if current_text != last_text:
                    last_text = current_text
                    last_change = time.time()
                elif not stop_visible and time.time() - last_change >= 5:
                    self.log("Response completed")
                    return True
            copy_button = self._last_assistant_copy_button(timeout_ms=300)
            if saw_assistant_text and copy_button and not stop_visible and time.time() - last_change >= 2:
                self.log("Response completed")
                return True
            self.page.wait_for_timeout(2000)

        raise RuntimeError(TIMEOUT_ERROR)

    def get_last_response(self):
        self.log("Copying response")
        copy_button = self._last_assistant_copy_button(timeout_ms=1500)
        if copy_button:
            before = self._get_clipboard()
            try:
                copy_button.click(timeout=5000)
                self.page.wait_for_timeout(500)
                copied = self._get_clipboard()
                if copied and copied != before:
                    return copied.strip()
                if copied:
                    return copied.strip()
            except Exception:
                pass
        text = self._last_assistant_text()
        if not text:
            raise RuntimeError("ChatGPT response could not be read.")
        return text.strip()

    def run_prompt(self, prompt_text, expect_json=False, on_login_required=None, timeout_seconds=300):
        if not self._job_lock.acquire(blocking=False):
            raise RuntimeError("Another ChatGPT Browser Bridge job is already running.")
        try:
            try:
                self.ensure_ready(on_login_required=on_login_required)
            except RuntimeError as exc:
                if str(exc) == CHROME_NOT_FOUND:
                    self._open_manual_fallback(prompt_text)
                    raise RuntimeError(
                        f"{CHROME_NOT_FOUND} Prompt was copied to clipboard and ChatGPT was opened in your default browser. "
                        "Please paste the response manually."
                    ) from exc
                raise
            self.send_prompt(prompt_text)
            self.wait_for_response_complete(timeout_seconds=timeout_seconds)
            response_text = self.get_last_response()
            if not expect_json:
                return {"ok": True, "text": response_text}
            self.log("Parsing JSON")
            try:
                return {"ok": True, "json": parse_json_response(response_text), "raw_text": response_text}
            except Exception as exc:
                return {"ok": False, "raw_text": response_text, "error": str(exc)}
        finally:
            self.close()
            self._job_lock.release()

    def open_ready_session(self, on_login_required=None):
        if not self._job_lock.acquire(blocking=False):
            raise RuntimeError("Another ChatGPT Browser Bridge job is already running.")
        try:
            try:
                return self.ensure_ready(on_login_required=on_login_required)
            except RuntimeError as exc:
                if str(exc) == CHROME_NOT_FOUND:
                    self._open_manual_fallback()
                raise
        finally:
            self.close()
            self._job_lock.release()

    def close(self):
        if self.context:
            try:
                self.context.close()
            except Exception:
                pass
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
        self.context = None
        self.page = None
        self._playwright = None

    def _ensure_available(self):
        if PLAYWRIGHT_IMPORT_ERROR:
            raise RuntimeError(f"Playwright is unavailable: {PLAYWRIGHT_IMPORT_ERROR}")
        if WIN32_IMPORT_ERROR:
            raise RuntimeError(f"Windows clipboard support is unavailable: {WIN32_IMPORT_ERROR}")

    def _open_manual_fallback(self, prompt_text=None):
        if prompt_text:
            self._set_clipboard(str(prompt_text))
        webbrowser.open(CHATGPT_URL)

    def _find_chat_input(self, timeout_ms=3000):
        selectors = [
            "#prompt-textarea",
            "[data-testid='composer-root'] [contenteditable='true']",
            "div[contenteditable='true'][role='textbox']",
            "textarea[placeholder*='Message']",
            "textarea",
        ]
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            for selector in selectors:
                locator = self.page.locator(selector).last
                try:
                    if locator.count() > 0 and locator.is_visible(timeout=300):
                        return locator
                except Exception:
                    continue
            self.page.wait_for_timeout(300)
        return None

    def _find_send_button(self, timeout_ms=1500):
        selectors = [
            "[data-testid='send-button']",
            "[data-testid='composer-submit-button']",
            "button[aria-label*='Send']",
            "button:has-text('Send')",
        ]
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            for selector in selectors:
                locator = self.page.locator(selector).last
                try:
                    if locator.count() > 0 and locator.is_visible(timeout=200) and locator.is_enabled(timeout=200):
                        return locator
                except Exception:
                    continue
            self.page.wait_for_timeout(200)
        return None

    def _assistant_message_locators(self):
        return [
            self.page.locator("[data-message-author-role='assistant']"),
            self.page.locator("article").filter(has=self.page.locator("[data-message-author-role='assistant']")),
        ]

    def _last_assistant_message(self):
        for locator in self._assistant_message_locators():
            try:
                count = locator.count()
                if count:
                    candidate = locator.nth(count - 1)
                    if candidate.is_visible(timeout=300):
                        return candidate
            except Exception:
                continue
        return None

    def _last_assistant_text(self):
        message = self._last_assistant_message()
        if not message:
            return ""
        try:
            return message.inner_text(timeout=1000).strip()
        except Exception:
            return ""

    def _last_assistant_copy_button(self, timeout_ms=1000):
        message = self._last_assistant_message()
        if not message:
            return None
        selectors = [
            "button[aria-label*='Copy']",
            "button[data-testid*='copy']",
            "[data-testid*='copy'] button",
            "button:has-text('Copy')",
        ]
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            for selector in selectors:
                locator = message.locator(selector).last
                try:
                    if locator.count() > 0 and locator.is_visible(timeout=200):
                        return locator
                except Exception:
                    continue
            self.page.wait_for_timeout(200)
        return None

    def _is_stop_generating_visible(self):
        selectors = [
            "[data-testid='stop-button']",
            "button[aria-label*='Stop']",
            "button:has-text('Stop generating')",
            "button:has-text('Stop')",
        ]
        for selector in selectors:
            locator = self.page.locator(selector).last
            try:
                if locator.count() > 0 and locator.is_visible(timeout=200):
                    return True
            except Exception:
                continue
        return False

    def _security_challenge_visible(self):
        try:
            text = (self.page.locator("body").inner_text(timeout=1000) or "").casefold()
        except Exception:
            return False
        challenge_terms = [
            "verify you are human",
            "verification",
            "captcha",
            "rate limit",
            "too many requests",
            "suspicious activity",
            "unusual activity",
            "security check",
        ]
        return any(term in text for term in challenge_terms)

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


def clean_json_markdown(text):
    text = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text


def parse_json_response(text):
    cleaned = clean_json_markdown(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise
