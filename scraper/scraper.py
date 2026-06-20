#!/usr/bin/env python3
"""
Google AI Mode Direct Scraper - FIXED HEADLESS MODE
Uses Google's AI Mode page directly for reliable AI responses.

Pipeline:
- Open Google AI Mode
- Ask a question
- Grab HTML of main content area (with fallbacks)
- Clean HTML into plain text
- Heuristically slice out ONLY the AI answer part
- Collapse to a single well-formed paragraph
- Detect tables in the AI HTML and:
    - keep them as markdown internally
    - pretty-print them as ASCII tables using tabulate in the terminal
"""

import time
import random
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.driver_cache import DriverCacheManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from tabulate import tabulate
from config.settings import BROWSER_HEADLESS


LOG_HTML_DIR = Path("logs/html")
LOG_SCREENSHOT_DIR = Path("logs/screenshots")
LOG_BROWSER_DIR = Path("logs/browser")
LOG_BROWSER_TMP_DIR = LOG_BROWSER_DIR / "tmp"
LOG_BROWSER_RUNTIME_DIR = LOG_BROWSER_DIR / "runtime"
WEBDRIVER_CACHE_DIR = Path(".wdm")


def _safe_name(text):
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()[:80] or "ai_mode"


class GoogleAIModeScraper:
    """Direct Google AI Mode scraper using the AI Mode URL"""

    AI_MODE_URL = "https://www.google.com/search"

    def __init__(self, headless=True, verbose=True):
        self.headless = headless
        self.verbose = verbose
        self.driver = None
        self.profile_dir = None
        self.setup_driver()

    def log(self, message, level="INFO"):
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")

    def setup_driver(self):
        """Setup Chrome driver with ENHANCED stealth options for headless"""
        chrome_options = Options()

        if self.headless:
            LOG_BROWSER_DIR.mkdir(parents=True, exist_ok=True)
            self.profile_dir = Path(
                tempfile.mkdtemp(prefix="chrome-profile-", dir=str(LOG_BROWSER_DIR))
            )
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-accelerated-video-decode")
            chrome_options.add_argument(
                "--disable-features=VaapiVideoDecoder,VaapiIgnoreDriverChecks,UseChromeOSDirectVideoDecoder"
            )
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"--user-data-dir={self.profile_dir}")
            chrome_options.add_argument(f"--disk-cache-dir={LOG_BROWSER_DIR / 'cache'}")

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--remote-debugging-pipe")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--lang=en-US")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        chrome_options.add_experimental_option(
            "prefs",
            {
                "profile.default_content_setting_values.notifications": 2,
                "intl.accept_languages": "en-US,en",
                "profile.managed_default_content_settings.images": 1,
            },
        )

        try:
            WEBDRIVER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            LOG_BROWSER_TMP_DIR.mkdir(parents=True, exist_ok=True)
            LOG_BROWSER_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            cache_manager = DriverCacheManager(root_dir=str(WEBDRIVER_CACHE_DIR))
            service_env = os.environ.copy()
            service_env["TMPDIR"] = str(LOG_BROWSER_TMP_DIR.resolve())
            service_env["XDG_RUNTIME_DIR"] = str(LOG_BROWSER_RUNTIME_DIR.resolve())
            service = Service(
                ChromeDriverManager(cache_manager=cache_manager).install(),
                env=service_env,
            )
            self.log(f"ChromeDriver path: {service.path}")

            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(60)
            self.driver.set_window_size(1920, 1080)

            self.driver.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {
                    "userAgent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                    "acceptLanguage": "en-US,en;q=0.9",
                    "platform": "Win32",
                },
            )
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                        
                        window.chrome = {
                            runtime: {},
                            loadTimes: function() {},
                            csi: function() {},
                            app: {},
                        };
                        
                        const originalQuery = window.navigator.permissions.query;
                        window.navigator.permissions.query = (parameters) => (
                            parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                        );
                    """
                },
            )

            self.log("✓ Browser driver initialized successfully")
        except Exception as e:
            self.log(f"✗ Failed to setup driver: {e}", "ERROR")
            raise

    def human_delay(self, min_sec=1, max_sec=3):
        """Random human-like delay"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def _ai_mode_url(self):
        params = {
            "q": "",
            "sourceid": "chrome",
            "ie": "UTF-8",
            "udm": "50",
            "aep": "48",
            "cud": "0",
            "qsubts": str(int(time.time() * 1000)),
        }
        return f"{self.AI_MODE_URL}?{urlencode(params)}"

    def _write_debug_artifacts(self, question, reason):
        LOG_HTML_DIR.mkdir(parents=True, exist_ok=True)
        LOG_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        stem = f"{_safe_name(question)}_{reason}"
        html_path = LOG_HTML_DIR / f"{stem}.html"
        screenshot_path = LOG_SCREENSHOT_DIR / f"{stem}.png"

        html_path.write_text(self.driver.page_source, encoding="utf-8")
        try:
            self.driver.save_screenshot(str(screenshot_path))
        except Exception:
            screenshot_path = None

        return html_path, screenshot_path

    def human_type(self, element, text):
        """Type text with human-like variation"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))

    def _find_search_input(self, selectors):
        for selector in selectors:
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                elements = self.driver.find_elements(By.XPATH, selector)
                candidates = []
                for element in elements:
                    try:
                        rect = element.rect
                        if (
                            element.is_displayed()
                            and element.is_enabled()
                            and rect.get("width", 0) > 0
                            and rect.get("height", 0) > 0
                        ):
                            candidates.append(element)
                    except Exception:
                        continue

                if candidates:
                    self.log(f"✓ Found input box with selector: {selector[:50]}...")
                    return max(candidates, key=lambda el: el.rect.get("y", 0))
            except TimeoutException:
                continue

        return None

    def _set_input_value_with_js(self, element, text):
        self.driver.execute_script(
            """
            const el = arguments[0];
            const value = arguments[1];
            const proto = Object.getPrototypeOf(el);
            const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');

            if (descriptor && descriptor.set) {
                descriptor.set.call(el, value);
            } else if ('value' in el) {
                el.value = value;
            } else {
                el.innerText = value;
            }

            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            element,
            text,
        )

    def _insert_text_with_cdp(self, element, text):
        self.driver.execute_script("arguments[0].focus();", element)
        self.driver.execute_cdp_cmd("Input.insertText", {"text": text})

    def _focus_and_enter_question(self, element, question):
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        self.human_delay(0.5, 1)

        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
        self.human_delay(0.3, 0.5)

        is_contenteditable = (
            (element.get_attribute("contenteditable") or "").lower() == "true"
        )
        if is_contenteditable:
            self.driver.execute_script(
                "arguments[0].innerText = ''; arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
                element,
            )
        else:
            try:
                element.clear()
            except Exception:
                element.send_keys(Keys.CONTROL, "a")
                element.send_keys(Keys.BACKSPACE)

        self.human_delay(0.3, 0.5)
        try:
            self.human_type(element, question)
        except Exception:
            self.log("Falling back to Chrome DevTools text insertion", "WARNING")
            try:
                self._insert_text_with_cdp(element, question)
            except Exception:
                self.log("Falling back to JavaScript input injection", "WARNING")
                self._set_input_value_with_js(element, question)

    def _submit_question(self, element):
        try:
            element.send_keys(Keys.RETURN)
            return
        except Exception:
            self.log("Return key submit failed; trying DevTools Enter", "WARNING")

        try:
            self.driver.execute_cdp_cmd(
                "Input.dispatchKeyEvent",
                {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13},
            )
            self.driver.execute_cdp_cmd(
                "Input.dispatchKeyEvent",
                {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13},
            )
            return
        except Exception:
            self.log("DevTools Enter failed; trying send button", "WARNING")

        send_selectors = [
            "//button[@aria-label='Send']",
            "//button[contains(@aria-label, 'Send')]",
            "//*[@role='button' and contains(@aria-label, 'Send')]",
        ]
        for selector in send_selectors:
            buttons = self.driver.find_elements(By.XPATH, selector)
            visible_buttons = []
            for button in buttons:
                try:
                    if button.is_displayed() and button.is_enabled():
                        visible_buttons.append(button)
                except Exception:
                    continue
            if visible_buttons:
                self.driver.execute_script("arguments[0].click();", visible_buttons[-1])
                return

        raise RuntimeError("Could not submit AI Mode question")

    def ask_ai_mode(self, question):
        """Ask question directly in Google AI Mode"""
        try:
            self.log(f"🤖 Asking AI Mode: '{question}'")
            # Navigate directly to AI Mode page
            self.driver.get(self._ai_mode_url())
            self.human_delay(4, 6)

            self._handle_cookies()

            # EXTENDED wait before looking for input
            self.human_delay(2, 3)

            # Find the "Ask anything" input box
            self.log("Looking for AI Mode input box...")
            input_selectors = [
                "//textarea[contains(@placeholder, 'Ask anything')]",
                "//textarea[@name='q']",
                "//textarea[contains(@aria-label, 'Search')]",
                "//input[@name='q']",
                "//div[@role='combobox']//textarea",
                "//div[@role='combobox']//input",
                "//*[@contenteditable='true']",
                "//textarea",  # Broader fallback
            ]

            search_input = self._find_search_input(input_selectors)

            if not search_input:
                html_path, screenshot_path = self._write_debug_artifacts(
                    question, "no_input"
                )
                self.log(f"Saved debug HTML to {html_path}", "WARNING")
                if screenshot_path:
                    self.log(f"Saved debug screenshot to {screenshot_path}", "WARNING")
                return {
                    "question": question,
                    "answer": None,
                    "tables": [],
                    "raw_html": None,
                    "success": False,
                    "error": f"Could not find AI Mode input box. Page saved to {html_path}",
                    "format": None,
                }

            self._focus_and_enter_question(search_input, question)
            self.human_delay(0.5, 1)

            # Submit the question
            self.log("Submitting question...")
            self._submit_question(search_input)

            self.log("Waiting for AI response...")
            deadline = time.time() + 70
            ai_response_html = None
            last_answer = ""
            last_tables = []

            while time.time() < deadline:
                self.human_delay(2, 3)
                ai_response_html = self._extract_ai_response()
                if not ai_response_html:
                    continue

                full_text, answer_only, tables_md = self._clean_html_and_extract_answer(
                    ai_response_html, question
                )
                answer_final = answer_only or full_text
                answer_final = self._sanitize_answer(answer_final)
                last_answer = answer_final
                last_tables = tables_md

                if self._is_meaningful_answer(answer_final):
                    return {
                        "question": question,
                        "answer": answer_final,
                        "tables": tables_md,  # list of markdown tables
                        "raw_html": ai_response_html,
                        "success": True,
                        "timestamp": datetime.now().isoformat(),
                        "format": "text",
                    }

                self.log("AI response shell found, waiting for answer text...")

            if not ai_response_html or not self._is_meaningful_answer(last_answer):
                html_path, screenshot_path = self._write_debug_artifacts(
                    question, "no_response"
                )
                self.log(f"Saved debug HTML to {html_path}", "WARNING")
                if screenshot_path:
                    self.log(f"Saved debug screenshot to {screenshot_path}", "WARNING")
                return {
                    "question": question,
                    "answer": None,
                    "tables": [],
                    "raw_html": None,
                    "success": False,
                    "error": f"No usable AI response found. Page saved to {html_path}",
                    "format": None,
                }

        except Exception as e:
            self.log(f"✗ Error asking AI Mode: {e}", "ERROR")
            try:
                html_path, screenshot_path = self._write_debug_artifacts(
                    question, "error"
                )
                self.log(f"Saved debug HTML to {html_path}", "WARNING")
                if screenshot_path:
                    self.log(f"Saved debug screenshot to {screenshot_path}", "WARNING")
            except Exception:
                pass
            return {
                "question": question,
                "answer": None,
                "tables": [],
                "raw_html": None,
                "success": False,
                "error": str(e),
                "format": None,
            }

    def _handle_cookies(self):
        """Handle cookie consent popup"""
        try:
            cookie_selectors = [
                "//button[contains(., 'Accept all')]",
                "//button[contains(., 'I agree')]",
                "//button[@id='L2AGLb']",
                "//button[contains(text(), 'Reject all')]",
            ]

            for selector in cookie_selectors:
                try:
                    button = WebDriverWait(self.driver, 5).until(  # Increased timeout
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    button.click()
                    self.log("✓ Cookie consent handled")
                    self.human_delay(1, 2)
                    return
                except TimeoutException:
                    continue
        except Exception:
            pass

    def _extract_ai_response(self):
        """Extract AI response from the page as HTML (preserve structure)"""
        self.log("Extracting AI response...")

        # Multiple selectors to try for AI responses
        response_selectors = [
            # AI Mode specific (guesses)
            "//div[contains(@class, 'ai-mode-response')]",
            "//div[@data-attrid='AIResponse']",
            "//div[contains(@class, 'generated-content')]",

            # SGE/AI Overview selectors (guesses)
            "//div[@data-attrid='SGEAnswer']",
            "//div[contains(@class, 'VjFXz')]",
            "//div[contains(@class, 'ai-overview')]",
            "//div[contains(@class, 'SPZz6b')]",

            # General content areas
            "//div[@id='rso']//div[contains(@class, 'g')]",
            "//div[contains(@class, 'kp-blk')]",

            # Fallback - main content area
            "//div[@id='search']",
            "//div[@id='main']",
        ]

        for selector in response_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    html = element.get_attribute("innerHTML") or ""
                    html = html.strip()
                    if html and len(html) > 50:  # Reasonable response length
                        self.log(
                            f"✓ AI response HTML found ({len(html)} chars) with selector: {selector}"
                        )
                        return html
            except Exception:
                continue

        # Try getting all visible HTML as last resort
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            html = body.get_attribute("innerHTML") or ""
            html = html.strip()
            if html and len(html) > 100:
                self.log(
                    f"⚠️  Using body HTML as fallback ({len(html)} chars)"
                )
                return html
        except Exception:
            pass

        self.log("✗ No AI response found", "WARNING")
        return None

    def _is_meaningful_answer(self, answer):
        if not answer:
            return False

        normalized = re.sub(r"\s+", " ", answer).strip().lower()
        if len(normalized) < 80:
            return False

        ui_phrases = [
            "quick settings sign in",
            "ai mode all images videos news more shopping maps",
            "google apps sign in",
            "loading",
        ]
        if any(phrase in normalized[:300] for phrase in ui_phrases):
            return False

        return True

    def _sanitize_answer(self, answer):
        answer = re.sub(r"\b(?:justdial|weddingwire(?:\.in|\.com)?)\b", "", answer, flags=re.IGNORECASE)
        answer = re.sub(r"\s*\+\d+\b", "", answer)
        answer = re.sub(r"\bTranscribing\.\.\.", "", answer, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", answer).strip()

    def _clean_html_and_extract_answer(self, html: str, question: str):
        """
        Convert HTML -> cleaned text, then heuristically extract only
        the AI answer block based on the question and known footer markers.
        Also extracts any tables in the HTML and converts them to Markdown.
        Returns (full_clean_text, answer_only_text or '', [tables_markdown]).
        """
        if not html:
            return "", "", []

        soup = BeautifulSoup(html, "html.parser")

        # Remove noise: scripts, styles, SVGs, noscript, etc.
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        # Extract tables as Markdown before flattening everything
        tables_md = self._extract_tables_markdown(soup)

        text = soup.get_text(separator="\n")
        # Strip and drop empty lines
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]

        full_clean = "\n".join(lines)
        full_clean = re.sub(r"\n{3,}", "\n\n", full_clean).strip()

        # Now slice out only the part that looks like the AI answer.
        answer_only = self._extract_answer_from_lines(lines, question)

        return full_clean, answer_only, tables_md

    def _extract_answer_from_lines(self, lines, question: str) -> str:
        """
        Heuristically find the answer block:

        - Find line containing the question text.
        - Start after that, skipping trivial UI lines.
        - Stop at footer markers like 'AI can make mistakes', 'Your feedback helps Google improve', etc.
        - Finally, collapse everything into ONE clean paragraph.
        """
        if not lines:
            return ""

        q = question.strip().lower()
        start_idx = None

        for i, line in enumerate(lines):
            if line.strip().lower() == "you said:":
                start_idx = i + 1
                break

        if start_idx is None:
            for i, line in enumerate(lines):
                if q and q in line.lower():
                    start_idx = i
                    break

        if start_idx is None:
            return ""

        # Move forward a bit to skip UI noise like 'Thinking', 'Searching', etc.
        i = start_idx + 1
        skip_exact = {
            "thinking",
            "searching",  # Added this - it was cutting off your answer!
            "draft",
            "meet ai mode",
            "filters and topics",
            "ai mode",
            "all",
            "images",
            "videos",
            "news",
            "more",
            "shopping",
            "maps",
            "books",
            "flights",
            "finance",
            "start new search",
            "help me pack for my trip to kerala next week",
            "compare leather sofas vs fabric sofas",
            "how to identify if the pashmina shawl i am buying is genuine?",
        }

        # Skip known UI elements
        while i < len(lines) and lines[i].strip().lower() in skip_exact:
            i += 1

        # More comprehensive footer markers
        footer_markers = [
            "ai can make mistakes",
            "ai overview can make mistakes",
            "ai overviews can make mistakes",
            "your feedback helps google improve",
            "thank you for your feedback",
            "thank you",
            "share more feedback",
            "report a problem",
            "report legal issue",
            "10 sites",
            "search results",
            "dismiss",
            "my ad centre",
            "turn on your visual search history",
            "learn more about these results",
            "about this result",
            "view all",
            "see more",
        ]

        collected = []
        
        # Collect lines until we hit a footer marker
        for j in range(i, len(lines)):
            low = lines[j].lower()
            
            # Stop if we hit a clear footer marker
            if any(marker in low for marker in footer_markers):
                break
            
            # Skip single-word navigation/UI elements
            if len(lines[j].split()) == 1 and lines[j].lower() in skip_exact:
                continue
                
            collected.append(lines[j])

        # Join lines and collapse to a single paragraph
        answer = "\n".join(collected).strip()
        
        # Collapse everything to single paragraph (remove all newlines, keep single spaces)
        answer_single_paragraph = re.sub(r"\s+", " ", answer).strip()
        
        return answer_single_paragraph

    def _clean_cell_text(self, text: str) -> str:
        """
        Clean up table cell text:
        - collapse whitespace
        - strip trailing source junk like 'TechTarget +7', 'IBM +4', 'Quora +4'
        """
        t = re.sub(r"\s+", " ", text).strip()
        # Remove trailing 'SourceName +N' patterns we saw in examples
        t = re.sub(
            r"\s+(IBM|Quora|TechTarget)\s*\+\d+$", "", t, flags=re.IGNORECASE
        )
        return t

    def _extract_tables_markdown(self, soup: BeautifulSoup):
        """
        Find all <table> elements in the soup and convert them to Markdown-style tables.
        Cleans header/cell text for readability.
        Returns a list of strings, each string is one markdown table.
        """
        tables_md = []
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            parsed_rows = []

            for row in rows:
                cells = row.find_all(["th", "td"])
                cell_texts = [
                    self._clean_cell_text(c.get_text(" ", strip=True))
                    for c in cells
                ]
                # Skip fully empty rows
                if any(cell_texts):
                    parsed_rows.append(cell_texts)

            if not parsed_rows:
                continue

            # Determine header row
            header = parsed_rows[0]
            data_rows = parsed_rows[1:] if len(parsed_rows) > 1 else []

            # Normalize header: if first cell starts with "feature", make it just "Feature"
            if header and header[0].lower().startswith("feature"):
                header[0] = "Feature"

            # Build markdown
            max_cols = max(len(r) for r in parsed_rows)
            header = header + [""] * (max_cols - len(header))
            norm_data_rows = [
                r + [""] * (max_cols - len(r)) for r in data_rows
            ]

            md_lines = []
            # Header
            md_lines.append("| " + " | ".join(header) + " |")
            # Separator
            md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")
            # Data rows
            for r in norm_data_rows:
                md_lines.append("| " + " | ".join(r) + " |")

            tables_md.append("\n".join(md_lines))

        return tables_md

    def close(self):
        """Close browser driver"""
        if self.driver:
            self.driver.quit()
            self.log("Browser closed")
        if self.profile_dir:
            shutil.rmtree(self.profile_dir, ignore_errors=True)


def ask_google_ai(question, headless=None, verbose=True):
    """Compatibility wrapper used by the main enrichment flow."""
    scraper = GoogleAIModeScraper(
        headless=BROWSER_HEADLESS if headless is None else headless,
        verbose=verbose,
    )
    try:
        return scraper.ask_ai_mode(question)
    finally:
        scraper.close()


def print_banner():
    """Print application banner"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║   Google AI Mode Direct Scraper (Paragraph + Tables)      ║
║                          FIXED                            ║
║  - Paragraph answers                                      ║
║  - Markdown tables rendered as ASCII with tabulate        ║
║  - Headless mode now works properly!                      ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_markdown_table_as_ascii(md: str):
    """
    Take a markdown table string and print it as a nice ASCII table using tabulate.
    """
    lines = [l.strip() for l in md.splitlines() if l.strip()]
    if len(lines) < 2:
        return

    # First line: header row, second: separator, rest: data
    header_line = lines[0]
    data_lines = lines[2:]  # skip separator row

    headers = [h.strip() for h in header_line.strip("|").split("|")]
    rows = []
    for line in data_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)

    print(tabulate(rows, headers=headers, tablefmt="grid"))


def print_result(result):
    """Pretty print AI response"""
    print("\n" + "=" * 60)
    print(f"Question: {result['question']}")
    print(f"Success: {'✓' if result['success'] else '✗'}")
    print(f"Format: {result.get('format')}")
    print("-" * 60)

    if result["success"] and result.get("answer"):
        print("\n🤖 AI Response (paragraph):")
        print("-" * 60)
        print(result["answer"])

        tables = result.get("tables") or []
        if tables:
            for idx, md_table in enumerate(tables, start=1):
                print(f"\n📊 Table {idx}:")
                print_markdown_table_as_ascii(md_table)

    elif not result["success"]:
        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
        print("\n💡 Tips:")
        print("   - Check ai_mode_page.html to see the actual page")
        print("   - Check ai_mode_debug.png screenshot if available")
        print("   - Try running in non-headless mode to debug")
        print("   - Make sure you're signed into Google")

    print("=" * 60 + "\n")


def save_to_file(results, filename="ai_responses.json"):
    """Save results to JSON file"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"✓ Results saved to {filename}")


def main():
    """Main terminal interface"""
    print_banner()

    # Configuration
    print("Configuration:")
    headless_input = input(
        "Run in headless mode? (y/n) [default: n]: "
    ).strip().lower()
    headless = headless_input == "y"

    print("\nInitializing AI Mode scraper...")
    scraper = None
    all_results = []

    try:
        scraper = GoogleAIModeScraper(headless=headless)

        print("\n✓ Scraper ready!")
        print("\n📝 Commands:")
        print("  - Type your question and press Enter")
        print("  - Type 'batch' to ask multiple questions")
        print("  - Type 'save' to save all responses to file")
        print("  - Type 'quit' to exit")
        print("\n💡 Tip: Ask detailed questions for better AI responses!\n")

        while True:
            question = input("❓ Ask AI: ").strip()

            if not question:
                continue

            if question.lower() == "quit":
                print("\n👋 Exiting...")
                break

            elif question.lower() == "save":
                if all_results:
                    filename = (
                        input("Filename [ai_responses.json]: ").strip()
                        or "ai_responses.json"
                    )
                    save_to_file(all_results, filename)
                else:
                    print("❌ No results to save yet!")
                continue

            elif question.lower() == "batch":
                print("\n📋 Batch Mode - Enter questions (empty line to finish):")
                questions = []
                while True:
                    q = input(f"  Question {len(questions)+1}: ").strip()
                    if not q:
                        break
                    questions.append(q)

                if questions:
                    print(f"\n🚀 Processing {len(questions)} questions...")
                    for i, q in enumerate(questions, 1):
                        print(f"\n[{i}/{len(questions)}] Processing: {q}")
                        result = scraper.ask_ai_mode(q)
                        all_results.append(result)
                        print_result(result)

                        if i < len(questions):
                            delay = random.uniform(10, 20)
                            print(
                                f"⏳ Waiting {delay:.1f}s before next question..."
                            )
                            time.sleep(delay)
                continue

            # Single question
            result = scraper.ask_ai_mode(question)
            all_results.append(result)
            print_result(result)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
    finally:
        if scraper:
            scraper.close()

        if all_results:
            save_choice = (
                input("\n💾 Save results before exiting? (y/n): ")
                .strip()
                .lower()
            )
            if save_choice == "y":
                save_to_file(all_results)


if __name__ == "__main__":
    main()
