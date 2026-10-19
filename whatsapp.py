"""Unofficial WhatsApp Web automation (Selenium).

Uses the browser native to each OS:
- macOS: Safari (built into selenium, no extra download — but the user must
  enable Safari's "Allow Remote Automation" once, see SAFARI_SETUP_HINT).
- Windows: Google Chrome (must be installed; matching chromedriver is
  downloaded once on first connect and cached).

This relies on WhatsApp Web's page structure, which Meta can change at
any time without notice. If sending stops working, the CSS/XPath
selectors below are the first place to check.
"""
import platform
import re
import time
import urllib.parse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import db

LOGGED_IN_SELECTOR = (By.CSS_SELECTOR, "div#pane-side")
SEND_BOX_SELECTOR = (By.CSS_SELECTOR, "footer div[contenteditable='true']")
SEARCH_BOX_SELECTOR = (By.CSS_SELECTOR, "div#pane-side div[contenteditable='true']")
INVALID_NUMBER_SELECTOR = (By.XPATH, "//*[contains(text(), 'Phone number shared via url is invalid')]")
CHAT_ROW_SELECTOR = (By.CSS_SELECTOR, "div#pane-side div[role='listitem']")
CHAT_ROW_TITLE_SELECTOR = (By.CSS_SELECTOR, "span[title]")
CHAT_HEADER_TITLE_SELECTOR = (By.CSS_SELECTOR, "header span[title]")
PHONE_TEXT_PATTERN = re.compile(r"\+\d[\d\s]{6,}\d")

IS_MAC = platform.system() == "Darwin"

SAFARI_SETUP_HINT = (
    "Safari needs to allow automation once:\n"
    "Safari menu -> Settings -> Advanced -> check 'Show features for web developers',\n"
    "then Develop menu -> check 'Allow Remote Automation'."
)


class WhatsAppError(Exception):
    pass


class WhatsAppSession:
    """Holds a single persistent browser/WhatsApp Web session for the app's lifetime."""

    def __init__(self):
        self._driver = None

    @property
    def profile_dir(self):
        return db.get_data_dir() / "whatsapp_profile"

    def is_connected(self) -> bool:
        if self._driver is None:
            return False
        try:
            self._driver.find_element(*LOGGED_IN_SELECTOR)
            return True
        except Exception:
            return False

    def _create_driver(self):
        if IS_MAC:
            from selenium.webdriver.safari.service import Service as SafariService

            try:
                # Point straight at the OS-provided safaridriver so Selenium never
                # falls back to its "Selenium Manager" auto-download mechanism,
                # which this app doesn't bundle a binary for on macOS.
                service = SafariService(executable_path="/usr/bin/safaridriver")
                return webdriver.Safari(service=service)
            except Exception as exc:  # noqa: BLE001
                raise WhatsAppError(f"Could not start Safari automation.\n{SAFARI_SETUP_HINT}\n\n({exc})")

        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--disable-notifications")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def connect(self, timeout_seconds: int = 120) -> bool:
        """Opens WhatsApp Web. Blocks until logged in (QR scanned) or timeout.
        Safe to call again if already connected — it's a no-op."""
        if self.is_connected():
            return True

        if self._driver is None:
            self._driver = self._create_driver()

        self._driver.get("https://web.whatsapp.com")
        try:
            WebDriverWait(self._driver, timeout_seconds).until(
                EC.presence_of_element_located(LOGGED_IN_SELECTOR)
            )
            return True
        except TimeoutException:
            return False

    def send_message(self, phone: str, message: str, contact_name: str = None) -> None:
        if not self.is_connected():
            raise WhatsAppError("WhatsApp is not connected. Click 'Connect WhatsApp' first.")

        clean_phone = "".join(ch for ch in phone if ch.isdigit() or ch == "+")

        # Fast path: open the chat through WhatsApp Web's own search box, reusing the
        # page that's already loaded and authenticated. Only used once we've re-confirmed
        # the opened chat's header actually matches this phone/name — any mismatch or
        # missing element falls back to the slower but always correctly-targeted method
        # below, so a failed fast path never risks typing into the wrong chat.
        if self._open_chat_via_search(clean_phone, contact_name):
            self._type_into_open_chat(message)
            return

        self._send_via_navigation(clean_phone, phone, message)

    def _open_chat_via_search(self, clean_phone: str, contact_name: str) -> bool:
        digits = clean_phone.lstrip("+")
        if len(digits) < 6:
            return False
        try:
            search_box = WebDriverWait(self._driver, 5).until(
                EC.element_to_be_clickable(SEARCH_BOX_SELECTOR)
            )
            search_box.click()
            select_all_key = Keys.COMMAND if IS_MAC else Keys.CONTROL
            search_box.send_keys(select_all_key, "a")
            search_box.send_keys(Keys.BACKSPACE)
            search_box.send_keys(digits)
            time.sleep(1)

            rows = self._driver.find_elements(*CHAT_ROW_SELECTOR)
            if not rows:
                raise WhatsAppError("no search results for this number")
            rows[0].click()

            header = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located(CHAT_HEADER_TITLE_SELECTOR)
            )
            header_text = (header.get_attribute("title") or header.text or "").strip()
            header_digits = "".join(ch for ch in header_text if ch.isdigit())
            digits_match = bool(header_digits) and digits[-8:] in header_digits
            name_match = bool(contact_name) and contact_name.strip().lower() == header_text.lower()
            if not (digits_match or name_match):
                raise WhatsAppError("opened chat header doesn't match the requested contact")

            self._clear_search_box()
            return True
        except Exception:
            self._clear_search_box()
            return False

    def _clear_search_box(self):
        try:
            search_box = self._driver.find_element(*SEARCH_BOX_SELECTOR)
            select_all_key = Keys.COMMAND if IS_MAC else Keys.CONTROL
            search_box.send_keys(select_all_key, "a")
            search_box.send_keys(Keys.BACKSPACE)
        except Exception:
            pass

    def _type_into_open_chat(self, message: str) -> None:
        last_exc = None
        for _attempt in range(5):
            try:
                box = WebDriverWait(self._driver, 10).until(
                    EC.element_to_be_clickable(SEND_BOX_SELECTOR)
                )
                box.click()
                self._driver.execute_script(
                    "arguments[0].focus(); document.execCommand('insertText', false, arguments[1]);",
                    box, message,
                )
                time.sleep(0.3)
                box.send_keys(Keys.ENTER)
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                time.sleep(1)

        raise WhatsAppError(
            f"The message box kept changing before it could be typed into. Please try sending again.\n({last_exc})"
        )

    def _send_via_navigation(self, clean_phone: str, phone: str, message: str) -> None:
        url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={urllib.parse.quote(message)}"
        self._driver.get(url)

        try:
            WebDriverWait(self._driver, 30).until(
                EC.presence_of_element_located(SEND_BOX_SELECTOR)
            )
        except TimeoutException:
            try:
                self._driver.find_element(*INVALID_NUMBER_SELECTOR)
                raise WhatsAppError(f"'{phone}' is not a valid WhatsApp number.")
            except WhatsAppError:
                raise
            except Exception:
                raise WhatsAppError("Timed out opening the chat. Check the phone number and try again.")

        time.sleep(1.5)  # let the message box fully render before typing

        # WhatsApp Web can swap this element out (React re-render) right as we're
        # about to interact with it, turning a single find_element() into a race.
        # Re-locate it fresh on each attempt instead of trusting one snapshot.
        last_exc = None
        for _attempt in range(5):
            try:
                box = WebDriverWait(self._driver, 10).until(
                    EC.element_to_be_clickable(SEND_BOX_SELECTOR)
                )
                box.click()
                box.send_keys(Keys.ENTER)
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                time.sleep(1)

        raise WhatsAppError(
            f"The message box kept changing before it could be clicked. Please try sending again.\n({last_exc})"
        )

    def sync_chat_contacts(self, progress_callback=None):
        """Best-effort scrape of the WhatsApp chat list: for each chat, opens it
        and reads the contact's name + phone number from the Contact Info panel.

        This only picks up people you've already chatted with (not your whole
        phone contact book), since that's the one part of WhatsApp Web's page
        that's reasonably stable to automate. Group chats and any row that
        doesn't yield a recognizable phone number are silently skipped, and a
        failure on one row never aborts the rest of the scan.
        """
        if not self.is_connected():
            raise WhatsAppError("WhatsApp is not connected. Click 'Connect WhatsApp' first.")

        self._driver.get("https://web.whatsapp.com")
        WebDriverWait(self._driver, 30).until(EC.presence_of_element_located(LOGGED_IN_SELECTOR))
        time.sleep(1)

        rows = self._driver.find_elements(*CHAT_ROW_SELECTOR)
        total = len(rows)
        results = []

        for idx in range(total):
            try:
                rows = self._driver.find_elements(*CHAT_ROW_SELECTOR)  # DOM may re-render between clicks
                if idx >= len(rows):
                    break
                row = rows[idx]
                title_el = row.find_element(*CHAT_ROW_TITLE_SELECTOR)
                name = (title_el.get_attribute("title") or title_el.text or "").strip()
                if not name:
                    continue

                row.click()
                time.sleep(1)

                header = self._driver.find_element(*CHAT_HEADER_TITLE_SELECTOR)
                header.click()
                time.sleep(1)

                phone = None
                for span in self._driver.find_elements(By.TAG_NAME, "span"):
                    text = (span.text or "").strip()
                    if PHONE_TEXT_PATTERN.fullmatch(text):
                        phone = text.replace(" ", "")
                        break

                self._driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(0.3)

                if phone:
                    results.append((name, phone))
            except Exception:
                continue  # one bad row shouldn't stop the whole sync
            finally:
                if progress_callback:
                    progress_callback(idx + 1, total)

        return results

    def close(self):
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None


session = WhatsAppSession()
