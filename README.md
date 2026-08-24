Copilot Chat
New chat


```
import requests
import json
import logging
import os
from datetime import datetime
import asyncio
import time
import re
from typing import Optional, Dict, Any
import random
import subprocess
import platform
import sys
import io
import tempfile
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

from config import *
from captcha_services import get_service_instance

# Fix Unicode on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

COMMAND_INTERVAL = 20

logger.info("Using Chrome Browser - Manual Login Required")

# Human-like delays
def random_delay(min_sec=1, max_sec=3):
    """Add random delay to mimic human behavior"""
    time.sleep(random.uniform(min_sec, max_sec))

class DiscordChromeClient:
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.driver = None
        self.username = None
        self.user_id = None
        self.last_seen_messages = set()  # Track messages we've already seen
        
        logger.info("Initializing Discord Chrome Browser Client...")
        self.setup_browser()
    
    def setup_browser(self):
        """Setup Selenium with Chrome browser"""
        
        chrome_options = Options()
        
        # Realistic user agent
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Basic arguments
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-crash-reporter")
        chrome_options.add_argument("--disable-popup-blocking")
        
        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            logger.info("Downloading ChromeDriver...")
            service = Service(ChromeDriverManager().install())
            
            logger.info("Launching Chrome browser...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(30)
            
            logger.info("Chrome browser launched successfully!")
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome browser: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def wait_for_login(self) -> bool:
        """Wait for user to manually login"""
        try:
            logger.info("\n" + "="*50)
            logger.info("PLEASE LOGIN TO DISCORD")
            logger.info("="*50)
            logger.info("A browser window has opened.")
            logger.info("Login using your email/password or SSO.")
            logger.info("Waiting for you to login...")
            logger.info("="*50 + "\n")
            
            self.driver.get("https://discord.com/login")
            time.sleep(2)
            
            # Wait for either guild scroller OR check URL change
            start_time = time.time()
            timeout = 300  # 5 minutes
            
            while time.time() - start_time < timeout:
                try:
                    current_url = self.driver.current_url
                    
                    # Check if logged in by URL (should not be on /login anymore)
                    if "discord.com" in current_url and "/login" not in current_url and "/register" not in current_url:
                        logger.info("Login detected via URL change!")
                        time.sleep(3)  # Wait for page to fully load
                        return True
                    
                    # Try to find guild scroller
                    try:
                        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='guild-scroller']")
                        logger.info("Login detected via guild scroller!")
                        return True
                    except:
                        pass
                    
                    time.sleep(1)
                
                except Exception as e:
                    logger.debug(f"Error during login check: {e}")
                    time.sleep(1)
            
            logger.error("Login timeout - user did not login within 5 minutes")
            return False
        
        except Exception as e:
            logger.error(f"Login wait failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def navigate_to_channel(self) -> bool:
        """Navigate to target channel"""
        try:
            logger.info(f"Navigating to channel {self.channel_id}...")
            
            channel_url = f"https://discord.com/channels/@me/{self.channel_id}"
            self.driver.get(channel_url)
            
            time.sleep(5)
            random_delay(1, 2)
            
            logger.info("In target channel")
            return True
        
        except Exception as e:
            logger.error(f"Error navigating: {e}")
            return False
    
    def get_message_contents(self):
        """Get actual message contents using article selector"""
        try:
            message_contents = []
            
            # Use article selector since we know it works
            articles = self.driver.find_elements(By.CSS_SELECTOR, "[role='article']")
            
            for article in articles:
                try:
                    text = article.text.strip()
                    if text:
                        message_contents.append(text)
                except:
                    pass
            
            return message_contents
        except Exception as e:
            logger.debug(f"Error getting messages: {e}")
            return []
    
    def wait_for_start_command(self) -> bool:
        """Wait for !start command in chat"""
        try:
            logger.info("\n" + "="*50)
            logger.info("WAITING FOR COMMAND IN DISCORD")
            logger.info("="*50)
            logger.info("Type !start in the channel to begin")
            logger.info("Checking for messages every 0.5 seconds...")
            logger.info("="*50 + "\n")
            
            # Debug: show current messages
            time.sleep(2)
            current_messages = self.get_message_contents()
            for msg in current_messages:
                self.last_seen_messages.add(msg)
            
            logger.info(f"Found {len(current_messages)} messages")
            
            timeout = 120  # 2 minute timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    current_messages = self.get_message_contents()
                    
                    # Check for new messages
                    for msg in current_messages:
                        if msg not in self.last_seen_messages:
                            self.last_seen_messages.add(msg)
                            
                            if "!start" in msg.lower():
                                logger.info("START command detected!")
                                time.sleep(1)
                                return True
                    
                    time.sleep(0.5)
                
                except Exception as e:
                    logger.debug(f"Error checking messages: {e}")
                    time.sleep(0.5)
            
            logger.error("Timeout waiting for !start command (2 minutes)")
            return False
        
        except Exception as e:
            logger.error(f"Error waiting for start: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def check_for_stop_command(self) -> bool:
        """Check if !stop command was sent"""
        try:
            messages = self.get_message_contents()
            
            if messages:
                last_message = messages[-1].lower()
                
                if "!stop" in last_message:
                    logger.info("STOP command detected!")
                    return True
            
            return False
        
        except Exception as e:
            logger.debug(f"Error checking for stop: {e}")
            return False
    
    def send_message(self, content: str) -> bool:
        """Send message to Discord channel"""
        try:
            logger.info("Attempting to find and click message input box...")
            
            # Close any open search/modals first by pressing Escape
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            
            # Find message input using the aria-label that starts with "Message"
            message_input_xpath = "//div[@role='textbox' and @contenteditable='true' and contains(@aria-label, 'Message')]"
            
            try:
                message_box = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, message_input_xpath))
                )
                logger.info("Found message input box")
            except Exception as e:
                logger.error(f"Could not find message input box: {e}")
                return False
            
            # Scroll to ensure it's visible
            self.driver.execute_script("arguments[0].scrollIntoView(true);", message_box)
            time.sleep(0.5)
            
            # Click on the message box
            ActionChains(self.driver).move_to_element(message_box).click().perform()
            time.sleep(0.5)
            
            # Wait for focus
            WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("return document.activeElement === arguments[0]", message_box)
            )
            
            # Clear any existing text
            message_box.send_keys(Keys.CONTROL + 'a')
            time.sleep(0.1)
            message_box.send_keys(Keys.DELETE)
            time.sleep(0.3)
            
            # Type the message character by character
            for char in content:
                message_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.12))
            
            time.sleep(0.5)
            
            # Send the message with Enter
            message_box.send_keys(Keys.RETURN)
            
            logger.info(f"Message sent: {content}")
            time.sleep(1)
            return True
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def wait_for_response(self, timeout: int = 45) -> Optional[str]:
        """Wait for owo bot response - wait for complete message"""
        try:
            start_time = time.time()
            
            logger.info(f"Waiting for response... (timeout: {timeout}s)")
            
            last_response = None
            stable_count = 0  # Counter to check if message is stable
            
            while time.time() - start_time < timeout:
                try:
                    current_messages = self.get_message_contents()
                    
                    # Check all messages for new owo responses
                    for msg in current_messages:
                        if msg not in self.last_seen_messages:
                            self.last_seen_messages.add(msg)
                            
                            msg_lower = msg.lower()
                            
                            # Look for owo response indicators
                            if any(keyword in msg_lower for keyword in ['spent', 'cowoncy', 'coin spins', 'heads', 'tails', 'chose']):
                                last_response = msg
                                stable_count = 0  # Reset counter when new message found
                                logger.debug(f"Found potential response, waiting for it to stabilize...")
                    
                    # If we have a response, check if it's complete
                    if last_response:
                        msg_lower = last_response.lower()
                        
                        # Check if the message is complete (has either won or lost in it)
                        if 'you won' in msg_lower or 'you lost' in msg_lower or 'gained' in msg_lower or 'lost it all' in msg_lower:
                            logger.info(f"Bot response complete and detected!")
                            return last_response
                        
                        # If message has "coin spins" but no won/lost yet, it might still be editing
                        if 'coin spins' in msg_lower:
                            stable_count += 1
                            if stable_count >= 3:  # Wait for 3 seconds of stable incomplete message
                                # Maybe the message won't complete, return it anyway
                                logger.warning("Message seems incomplete but stable, returning it")
                                return last_response
                    
                    time.sleep(1)
                
                except Exception as e:
                    logger.error(f"Error checking messages: {e}")
                    time.sleep(1)
            
            if last_response:
                logger.warning(f"Timeout reached but have incomplete response, returning it")
                return last_response
            
            logger.warning(f"No response received after {timeout} seconds")
            return None
        
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
            return None
    
    def close(self):
        """Close browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome browser closed")
            except:
                pass

# Game State
class GameState:
    def __init__(self):
        self.current_bet = INITIAL_BET
        self.total_games = 0
        self.wins = 0
        self.losses = 0
        self.is_running = False
        self.last_result = None
        self.last_timestamp = None
    
    def on_win(self):
        self.wins += 1
        self.total_games += 1
        self.current_bet = INITIAL_BET
        logger.info(f"WIN! Bet reset to {INITIAL_BET}. Stats: {self.wins}W - {self.losses}L")
    
    def on_loss(self):
        self.losses += 1
        self.total_games += 1
        self.current_bet *= BET_MULTIPLIER
        logger.warning(f"LOSS! Bet doubled to {self.current_bet}. Stats: {self.wins}W - {self.losses}L")
    
    def get_stats(self):
        win_rate = (self.wins / self.total_games * 100) if self.total_games > 0 else 0
        return {
            "current_bet": self.current_bet,
            "total_games": self.total_games,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": win_rate
        }

game_state = GameState()

async def play_game(browser_client: DiscordChromeClient):
    """Main game loop"""
    logger.info("Starting game loop...")
    logger.info(f"Command interval: {COMMAND_INTERVAL} seconds")
    logger.info("Bot is running! Type !stop in Discord to stop.\n")
    
    while game_state.is_running:
        try:
            # Check for stop command
            if browser_client.check_for_stop_command():
                logger.info("Stop command received!")
                game_state.is_running = False
                break
            
            command_text = f"{COMMAND} {game_state.current_bet}"
            logger.info(f"Sending command: {command_text}")
            
            if not browser_client.send_message(command_text):
                logger.error("Failed to send message")
                await asyncio.sleep(COMMAND_INTERVAL)
                continue
            
            random_delay(2, 4)
            
            result = browser_client.wait_for_response(timeout=45)
            
            if result:
                game_state.last_result = result
                game_state.last_timestamp = datetime.now()
                
                result_lower = result.lower()
                
                # Log the full message for debugging
                logger.info(f"Full bot message: {result}")
                
                # Determine win or loss based on exact keywords
                is_loss = False
                is_win = False
                
                # Check for specific loss pattern
                if 'you lost' in result_lower or 'lost it all' in result_lower:
                    is_loss = True
                    logger.info("Detected: 'you lost' or 'lost it all'")
                
                # Check for specific win pattern
                if 'you won' in result_lower or 'gained' in result_lower:
                    is_win = True
                    logger.info("Detected: 'you won' or 'gained'")
                
                logger.info(f"Win check: {is_win}, Loss check: {is_loss}")
                
                if is_loss and not is_win:  # Make sure it's ONLY a loss
                    logger.info("Result: LOSS detected")
                    game_state.on_loss()
                elif is_win and not is_loss:  # Make sure it's ONLY a win
                    logger.info("Result: WIN detected")
                    game_state.on_win()
                else:
                    logger.warning(f"Could not determine win/loss or message was incomplete.")
                    logger.warning(f"Message: {result[:300]}")
            else:
                logger.warning("No response received from bot")
            
            random_interval = COMMAND_INTERVAL + random.randint(-5, 5)
            logger.info(f"Waiting {random_interval} seconds...\n")
            await asyncio.sleep(random_interval)
        
        except Exception as e:
            logger.error(f"Error in game loop: {e}")
            await asyncio.sleep(COMMAND_INTERVAL)

def print_stats():
    """Print game statistics"""
    stats = game_state.get_stats()
    print("\n" + "="*50)
    print("GAME STATISTICS")
    print("="*50)
    print(f"Current Bet: {stats['current_bet']}")
    print(f"Total Games: {stats['total_games']}")
    print(f"Wins: {stats['wins']}")
    print(f"Losses: {stats['losses']}")
    print(f"Win Rate: {stats['win_rate']:.2f}%")
    print("="*50 + "\n")

def main():
    """Main entry point"""
    
    if not CHANNEL_ID or CHANNEL_ID == 0:
        logger.error("CHANNEL_ID not found in .env file!")
        return
    
    logger.info("Starting Discord Coin Flip Bot (Chrome Browser Mode)...")
    logger.info(f"Command interval: {COMMAND_INTERVAL} seconds\n")
    
    browser_client = DiscordChromeClient(CHANNEL_ID)
    
    try:
        # Wait for manual login
        if not browser_client.wait_for_login():
            logger.error("Login failed!")
            return
        
        # Navigate to channel
        if not browser_client.navigate_to_channel():
            logger.error("Failed to navigate to channel!")
            return
        
        # Wait for !start command
        if not browser_client.wait_for_start_command():
            logger.error("Failed waiting for start command!")
            return
        
        # Start the game
        game_state.is_running = True
        asyncio.run(play_game(browser_client))
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        game_state.is_running = False
        print_stats()
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        game_state.is_running = False
    
    finally:
        print_stats()
        browser_client.close()

if __name__ == "__main__":
    main()
```

i want some update in my code 

ill give one code 
and i will specify


this 
I can help — but I need you to tell me which update(s) you want. Below are sensible, safe improvements I can make to your script. Pick one or more and I’ll implement them and show the updated code.

Suggested updates (pick by number or describe your own):

Persist login/session (save/load cookies or use Chrome user-data-dir) so you don’t need to manually login each run.
Add a headless / CLI mode toggle and optional profile directory flags.
Make message scraping more robust (return structured messages: author, content, timestamp) using a small JS extractor instead of relying on article.text.
Improve message-send reliability (clear focus, retry, handle contenteditable quirks, optional paste instead of typing).
Better response parsing (regex rules + confidence checks) and make win/loss detection configurable.
Add exponential backoff & retries for flaky Selenium actions.
Add debug artifacts: optional screenshots on errors and more detailed logging (rotate logs).
Convert blocking waits to asyncio-friendly non-blocking waits (avoid time.sleep in async loop).
Validate config at startup and fail fast with clear messages (CHANNEL_ID, env vars).
Minor code cleanup: typing annotations, docstrings, and a few unit-testable functions.
Small preview: cookie/session persistence (option 1)

What I’ll change:
On browser startup, load cookies from a file if present and verify logged-in state.
After successful manual login, save cookies to file for subsequent runs.
Optionally add user-data-dir argument so Chrome can persist full profile.
Example patch (preview snippet) — I will implement this if you pick option 1:

In setup_browser(), add optional user-data-dir if provided.
Add methods load_cookies(path) and save_cookies(path).
After wait_for_login() succeeds, call save_cookies().
If you want option 3 (structured scraping) I’ll replace get_message_contents() with a JS-based extractor that returns a list of dicts: [{"author":"...", "content":"...", "ts":"..."}] and update code that checks new messages accordingly.

Tell me:

Which option(s) from the list do you want implemented?
Or describe the exact change you want (show an example of the behavior you expect). Once you confirm I’ll apply the change and return the modified code and a short description of what changed and why.
2/2
2/2
```
#!/usr/bin/env python3
"""
Full bot.py - Headless Discord multi-token runner with API-based captcha detection and DM-confirm resume.

Features:
- Discord REST API used for sending/fetching messages and DM handling.
- hCaptcha solving via configurable solvers (NopeCHA / Capsolver / 2Captcha).
- Central captcha checker that detects OwO captcha messages and pauses affected accounts.
- After solve: poll OwO DM for authoritative verification phrase; fallback to posting a trigger in channel.
- Avoid reprocessing the same OwO captcha message by tracking handled message IDs.
- UTF-8-safe logging for Windows consoles where possible.
"""
import os
import sys
import time
import logging
import hashlib
import random
import threading
import requests
import urllib3
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

import config

# Disable urllib3 warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load config
GUILD_ID = config.GUILD_ID
PROFILES_DIR = getattr(config, "PROFILES_DIR", "profiles")
TOKENS_FILE = config.TOKENS_FILE
CONCURRENCY = getattr(config, "CONCURRENCY", 1)
COMMANDS = config.COMMANDS
COMMAND_INTERVAL_CFG = config.COMMAND_INTERVAL
ROUNDS_PER_ACCOUNT = config.ROUNDS_PER_ACCOUNT
LOG_FILE = getattr(config, "LOG_FILE", "multi_token_runner.log")

# Captcha config
OWO_BOT_ID = config.OWO_BOT_ID
CAPTCHA_CHECK_INTERVAL = getattr(config, "CAPTCHA_CHECK_INTERVAL", 8)
CAPTCHA_SOLVE_TIMEOUT = getattr(config, "CAPTCHA_SOLVE_TIMEOUT", 120)
CAPTCHA_KEYWORDS = [kw.lower() for kw in (getattr(config, "CAPTCHA_KEYWORDS", []) or [])]
CAPTCHA_SOLVERS = getattr(config, "CAPTCHA_SOLVERS", {})
CAPTCHA_SOLVER_ORDER = getattr(config, "CAPTCHA_SOLVER_ORDER", list(CAPTCHA_SOLVERS.keys()))

# hCaptcha constants (sitekey / page for OwO)
HCAPTCHA_SITEKEY = "a6a1d5ce-612d-472d-8e37-7601408fbc09"
HCAPTCHA_PAGE_URL = "https://owobot.com/captcha"

# Resume trigger and cooldown (can be overridden in config if you add them there)
TRIGGER_TEXT = getattr(config, "TRIGGER_TEXT", "captcha solved! resuming")
POST_SOLVE_COOLDOWN = getattr(config, "POST_SOLVE_COOLDOWN", 12)

# DM polling
DM_POLL_TIMEOUT = getattr(config, "DM_POLL_TIMEOUT", 30)
DM_POLL_INTERVAL = getattr(config, "DM_POLL_INTERVAL", 2)
DM_VERIFIED_PHRASES = [p.lower() for p in getattr(config, "DM_VERIFIED_PHRASES", [
    "i have verified that you are human",
    "you're free to go",
    "you are human",
    "verified"
])]

# Logging (UTF-8 safe handler on Windows if possible)
from logging import FileHandler, StreamHandler, Formatter, getLogger, INFO

file_handler = FileHandler(LOG_FILE) if LOG_FILE else None
if file_handler:
    file_handler.setFormatter(Formatter("%(asctime)s - %(levelname)s - %(message)s"))

try:
    stream = sys.stdout
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")
    stream_handler = StreamHandler(stream)
except Exception:
    stream_handler = StreamHandler()
stream_handler.setFormatter(Formatter("%(asctime)s - %(levelname)s - %(message)s"))

handlers = []
if file_handler:
    handlers.append(file_handler)
handlers.append(stream_handler)

logging.basicConfig(level=INFO, handlers=handlers)
logger = getLogger(__name__)

# Suppress noisy urllib3 logs
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)


@dataclass
class AccountState:
    """Track per-account state"""
    token: str
    channel_id: str
    account_id: str
    driver: Optional[object] = None
    is_paused: bool = False
    captcha_detected_at: Optional[datetime] = None
    is_solving: bool = False
    message_loop_active: bool = False
    pause_event: threading.Event = field(default_factory=threading.Event)
    solve_retries: int = 0
    last_solved_at: Optional[float] = None
    needs_manual_intervention: bool = False
    user_id: Optional[str] = None  # Discord user id (string)
    # New fields to avoid reprocessing the same OwO message
    handled_owo_message_ids: set = field(default_factory=set)
    captcha_message_id: Optional[str] = None


def short_id(token: str) -> str:
    return hashlib.sha1(token.encode("utf-8")).hexdigest()[:10]


def parse_interval(cfg) -> float:
    """Parse a COMMAND_INTERVAL-like config into a float seconds."""
    if isinstance(cfg, (int, float)):
        return float(cfg)
    if not isinstance(cfg, str):
        return 20.0
    s = cfg.strip()
    if "-" in s:
        a, b = s.split("-", 1)
        try:
            a_f = float(a)
            b_f = float(b)
            lo, hi = (a_f, b_f) if a_f <= b_f else (b_f, a_f)
            return random.uniform(lo, hi)
        except Exception:
            return 20.0
    try:
        return float(s)
    except Exception:
        return 20.0


def create_session():
    """requests.Session with retries/connection pooling"""
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5, total=5)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# ============================================================================
# HCaptcha solver implementations (Capsolver, NopeCHA, 2Captcha)
# ============================================================================

class HCaptchaSolver:
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self):
        self.enabled_solvers = self._get_enabled_solvers()

    def _get_enabled_solvers(self) -> list:
        enabled = []
        for name in CAPTCHA_SOLVER_ORDER:
            cfg = CAPTCHA_SOLVERS.get(name)
            if cfg and cfg.get("enabled"):
                enabled.append(name)
        return enabled

    def _solve_capsolver(self, api_key: str) -> Optional[str]:
        session = create_session()
        try:
            resp = session.post("https://api.capsolver.com/createTask", json={
                "clientKey": api_key,
                "task": {
                    "type": "HCaptchaTaskProxyLess",
                    "websiteURL": HCAPTCHA_PAGE_URL,
                    "websiteKey": HCAPTCHA_SITEKEY,
                }
            }, timeout=15)
            logger.debug("Capsolver create status=%s body=%s", resp.status_code, resp.text[:1000])
            data = resp.json()
            task_id = data.get("taskId")
            if not task_id:
                logger.debug("Capsolver create failed: %s", data)
                return None
            for _ in range(60):
                time.sleep(3)
                poll = session.post("https://api.capsolver.com/getTaskResult", json={"clientKey": api_key, "taskId": task_id}, timeout=15)
                logger.debug("Capsolver poll status=%s body=%s", poll.status_code, poll.text[:1000])
                pd = poll.json()
                if pd.get("status") == "ready":
                    token = pd.get("solution", {}).get("gRecaptchaResponse")
                    if token:
                        logger.info("Capsolver solved hCaptcha")
                        return token
                if pd.get("status") == "failed" or pd.get("errorCode"):
                    logger.debug("Capsolver failure: %s", pd)
                    return None
            logger.debug("Capsolver timed out")
            return None
        except Exception as e:
            logger.debug("Capsolver exception: %s", e)
            return None

    def _solve_nopecha(self, api_key: str) -> Optional[str]:
        session = create_session()
        try:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            sub = session.post("https://api.nopecha.com/token", json={"type": "hcaptcha", "sitekey": HCAPTCHA_SITEKEY, "url": HCAPTCHA_PAGE_URL}, headers=headers, timeout=15)
            logger.debug("NopeCHA submit status=%s body=%s", sub.status_code, sub.text[:1000])
            sd = sub.json()
            task_id = sd.get("data")
            if not task_id:
                logger.debug("NopeCHA submit failed: %s", sd)
                return None
            for _ in range(180):
                time.sleep(1)
                poll = session.get(f"https://api.nopecha.com/token?id={task_id}", headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
                logger.debug("NopeCHA poll status=%s body=%s", poll.status_code, poll.text[:1000])
                if poll.status_code == 409:
                    continue
                pd = poll.json()
                token = pd.get("data")
                if token and isinstance(token, str):
                    logger.info("NopeCHA solved hCaptcha")
                    return token
                logger.debug("NopeCHA poll returned: %s", pd)
                return None
            logger.debug("NopeCHA timed out")
            return None
        except Exception as e:
            logger.debug("NopeCHA exception: %s", e)
            return None

    def _solve_2captcha(self, api_key: str) -> Optional[str]:
        session = create_session()
        try:
            data = {
                "key": api_key,
                "method": "hcaptcha",
                "sitekey": HCAPTCHA_SITEKEY,
                "pageurl": HCAPTCHA_PAGE_URL,
                "json": 1,
            }
            sub = session.post("https://2captcha.com/in.php", data=data, timeout=15)
            logger.debug("2Captcha submit status=%s body=%s", sub.status_code, sub.text[:1000])
            try:
                sd = sub.json()
            except Exception:
                logger.debug("2Captcha submit non-json: %s", sub.text[:1000])
                return None
            if sd.get("status") != 1:
                logger.debug("2Captcha submit failed: %s", sd.get("request"))
                return None
            captcha_id = sd.get("request")
            if not captcha_id:
                logger.debug("2Captcha no id: %s", sd)
                return None
            for _ in range(40):
                time.sleep(5)
                poll_url = f"https://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}&json=1"
                poll = session.get(poll_url, timeout=15)
                logger.debug("2Captcha poll status=%s body=%s", poll.status_code, poll.text[:1000])
                try:
                    pd = poll.json()
                except Exception:
                    logger.debug("2Captcha poll non-json: %s", poll.text[:1000])
                    continue
                if pd.get("status") == 1:
                    token = pd.get("request")
                    logger.info("2Captcha solved hCaptcha")
                    return token
                if pd.get("request") != "CAPCHA_NOT_READY":
                    logger.debug("2Captcha poll error: %s", pd)
                    return None
            logger.debug("2Captcha timed out")
            return None
        except Exception as e:
            logger.debug("2Captcha exception: %s", e)
            return None

    def solve_captcha(self, discord_token: str, guild_id: Optional[str] = None) -> bool:
        """Perform the OAuth->redirect->solve->verify flow using a fresh session."""
        try:
            if not self.enabled_solvers:
                logger.error("No captcha solvers enabled!")
                return False

            session = create_session()
            ua_headers = {"User-Agent": self.UA}

            logger.info("Step 1: Getting Discord OAuth2 URL from owobot...")
            auth_res = session.get("https://owobot.com/api/auth/discord", allow_redirects=False, headers=ua_headers, timeout=10)
            oauth_loc = auth_res.headers.get("Location") or auth_res.headers.get("location")
            if not oauth_loc or "discord.com" not in oauth_loc:
                logger.error("owobot oauth returned unexpected response")
                return False

            oauth_url = urlparse(oauth_loc)
            oauth_params = parse_qs(oauth_url.query)
            client_id = oauth_params.get("client_id", [""])[0]
            redirect_uri = oauth_params.get("redirect_uri", [""])[0]
            scope = oauth_params.get("scope", ["identify"])[0]
            state = oauth_params.get("state", [None])[0]
            if not client_id or not redirect_uri:
                logger.error("Could not parse OAuth2 parameters")
                return False

            logger.info("Step 2: Authorizing with Discord...")
            auth_url = (f"https://discord.com/api/v9/oauth2/authorize"
                        f"?client_id={client_id}"
                        f"&redirect_uri={redirect_uri}"
                        f"&response_type=code"
                        f"&scope={scope}")
            if state:
                auth_url += f"&state={state}"

            auth_body = {"permissions": "0", "authorize": True}
            if guild_id:
                auth_body["guild_id"] = guild_id

            discord_res = session.post(auth_url, json=auth_body,
                                      headers={"Authorization": discord_token, "Content-Type": "application/json", "User-Agent": self.UA},
                                      allow_redirects=False, timeout=10)
            if not discord_res.ok:
                try:
                    err = discord_res.json().get("message", f"Discord {discord_res.status_code}")
                except Exception:
                    err = f"Discord {discord_res.status_code}"
                logger.error("Discord authorization failed: %s", err)
                return False

            cb = None
            try:
                cb = discord_res.json().get("location")
            except Exception:
                pass
            if not cb:
                cb = discord_res.headers.get("Location") or discord_res.headers.get("location")
            if not cb:
                logger.error("Discord returned no callback URL")
                return False

            logger.info("Discord OAuth2 authorized")

            logger.info("Step 3: Following OAuth2 redirects...")
            current_url = cb
            for _ in range(8):
                follow_res = session.get(current_url, allow_redirects=False, headers=ua_headers, timeout=10)
                next_loc = follow_res.headers.get("Location") or follow_res.headers.get("location")
                if not next_loc or follow_res.status_code < 300 or follow_res.status_code >= 400:
                    break
                current_url = urljoin("https://owobot.com", next_loc)

            logger.info("Session established with cookies: %s", list(session.cookies.keys()))

            logger.info("Step 4: Solving hCaptcha...")
            hcaptcha_token = None
            for solver in self.enabled_solvers:
                logger.info("Trying solver %s...", solver)
                if solver == "capsolver":
                    api_key = CAPTCHA_SOLVERS.get("capsolver", {}).get("api_key")
                    if api_key:
                        hcaptcha_token = self._solve_capsolver(api_key)
                        if hcaptcha_token:
                            break
                elif solver == "nopecha":
                    api_key = CAPTCHA_SOLVERS.get("nopecha", {}).get("api_key")
                    if api_key:
                        hcaptcha_token = self._solve_nopecha(api_key)
                        if hcaptcha_token:
                            break
                elif solver == "2captcha":
                    api_key = CAPTCHA_SOLVERS.get("2captcha", {}).get("api_key")
                    if api_key:
                        hcaptcha_token = self._solve_2captcha(api_key)
                        if hcaptcha_token:
                            break

            if not hcaptcha_token:
                logger.error("Failed to obtain hCaptcha token from solvers")
                return False

            logger.info("Step 5: Submitting solution to owobot.com...")
            verify_res = session.post("https://owobot.com/api/captcha/verify",
                                      json={"token": hcaptcha_token},
                                      headers={"Content-Type": "application/json", "User-Agent": self.UA, "Origin": "https://owobot.com", "Referer": "https://owobot.com/captcha"},
                                      timeout=15)
            if verify_res.ok:
                logger.info("CAPTCHA VERIFIED on owobot.com")
                return True
            else:
                logger.error("owobot verify failed %s: %s", verify_res.status_code, verify_res.text[:300])
                return False

        except Exception as e:
            logger.error("Exception in solve_captcha: %s", e)
            return False


# ============================================================================
# Discord API client helper
# ============================================================================

class DiscordAPIClient:
    def __init__(self, token: str):
        self.token = token
        self.session = create_session()
        self.base_url = "https://discord.com/api/v9"
        self.headers = {"Authorization": token, "User-Agent": "Mozilla/5.0"}

    def send_message(self, channel_id: str, content: str, account_state: Optional[AccountState] = None, force: bool = False) -> bool:
        """Send a message to a channel. If force=True, bypass paused check for this send."""
        try:
            if account_state and account_state.is_paused and not force:
                logger.info("Skipping send_message because account is paused")
                return False
            url = f"{self.base_url}/channels/{channel_id}/messages"
            resp = self.session.post(url, json={"content": content}, headers=self.headers, timeout=10)
            if resp.status_code in (200, 201):
                logger.info("Message sent via API: %s", content)
                return True
            logger.warning("Failed to send message: HTTP %s - %s", resp.status_code, resp.text[:300])
            return False
        except Exception as e:
            logger.error("Error sending message: %s", e)
            return False

    def fetch_messages(self, channel_id: str, limit: int = 20) -> List[dict]:
        """Fetch recent messages for a channel (or DM channel)."""
        try:
            url = f"{self.base_url}/channels/{channel_id}/messages?limit={limit}"
            resp = self.session.get(url, headers=self.headers, timeout=10)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.debug("fetch_messages HTTP %s: %s", resp.status_code, resp.text[:300])
            return []
        except Exception as e:
            logger.debug("fetch_messages error: %s", e)
            return []

    def get_current_user_id(self) -> Optional[str]:
        try:
            resp = self.session.get(f"{self.base_url}/users/@me", headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("id")
            logger.debug("get_current_user_id HTTP %s: %s", resp.status_code, resp.text[:300])
            return None
        except Exception as e:
            logger.debug("get_current_user_id error: %s", e)
            return None

    def get_dm_channel_with(self, recipient_id: str) -> Optional[str]:
        """Create or return DM channel ID with recipient (OwO bot)."""
        try:
            resp = self.session.post(f"{self.base_url}/users/@me/channels", json={"recipient_id": recipient_id}, headers=self.headers, timeout=10)
            if resp.status_code in (200, 201):
                return resp.json().get("id")
            logger.debug("get_dm_channel_with HTTP %s: %s", resp.status_code, resp.text[:300])
            return None
        except Exception as e:
            logger.debug("get_dm_channel_with error: %s", e)
            return None


# ============================================================================
# Central captcha checker
# ============================================================================

class CentralCaptchaChecker:
    def __init__(self):
        self.accounts: Dict[str, AccountState] = {}
        self.lock = threading.Lock()
        self.running = True

    def initialize_browser(self):
        logger.info("Central captcha checker initialized (API-based detection)")

    def register_account(self, account_state: AccountState):
        with self.lock:
            self.accounts[account_state.account_id] = account_state

    def unregister_account(self, account_id: str):
        with self.lock:
            if account_id in self.accounts:
                del self.accounts[account_id]

    def start_checking(self):
        t = threading.Thread(target=self._check_loop, daemon=True)
        t.start()
        logger.info("Central captcha checker started (API)")

    def _parse_msg_ts(self, ts: Optional[str]) -> Optional[datetime]:
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None

    def _check_loop(self):
        while self.running:
            try:
                with self.lock:
                    for account_id, account_state in list(self.accounts.items()):
                        # skip inactive / solving / manual accounts
                        if not account_state.message_loop_active or account_state.is_solving or account_state.needs_manual_intervention:
                            continue

                        # respect cooldown after successful solve
                        now_ts = time.time()
                        if account_state.last_solved_at and (now_ts - account_state.last_solved_at) < POST_SOLVE_COOLDOWN:
                            continue

                        try:
                            discord = DiscordAPIClient(account_state.token)
                            msgs = discord.fetch_messages(account_state.channel_id, limit=25)

                            # If paused: look for account's own trigger message and compare with OwO captcha message timestamps
                            if account_state.is_paused and account_state.captcha_detected_at:
                                latest_trigger_ts = None
                                latest_owo_ts = None
                                for m in msgs:
                                    msg_id = m.get("id")
                                    author_id = str(m.get("author", {}).get("id", ""))
                                    content = (m.get("content") or "").lower()
                                    ts = self._parse_msg_ts(m.get("timestamp"))
                                    # account's own trigger message
                                    if account_state.user_id and author_id == str(account_state.user_id) and TRIGGER_TEXT in content:
                                        if ts and (latest_trigger_ts is None or ts > latest_trigger_ts):
                                            latest_trigger_ts = ts
                                    # OwO captcha message (if not already handled)
                                    if msg_id and msg_id in account_state.handled_owo_message_ids:
                                        continue
                                    if author_id == str(OWO_BOT_ID):
                                        if ("⚠️" in content) or any(kw in content for kw in CAPTCHA_KEYWORDS):
                                            if ts and (latest_owo_ts is None or ts > latest_owo_ts):
                                                latest_owo_ts = ts

                                # If trigger exists and is newer-or-equal, resume account
                                if latest_trigger_ts and (not latest_owo_ts or latest_trigger_ts >= latest_owo_ts):
                                    account_state.is_paused = False
                                    account_state.pause_event.clear()
                                    account_state.last_solved_at = time.time()
                                    logger.info("✅ Resuming account %s after seeing trigger message/DM", account_id)
                                    continue

                            # If not paused, detect new OwO captcha messages (skip handled ones)
                            if not account_state.is_paused:
                                for m in msgs:
                                    msg_id = m.get("id")
                                    author_id = str(m.get("author", {}).get("id", ""))
                                    content = (m.get("content") or "").lower()
                                    if msg_id and msg_id in account_state.handled_owo_message_ids:
                                        continue
                                    if author_id == str(OWO_BOT_ID):
                                        if ("⚠️" in content) or any(kw in content for kw in CAPTCHA_KEYWORDS):
                                            account_state.is_paused = True
                                            account_state.captcha_detected_at = datetime.now()
                                            account_state.captcha_message_id = msg_id
                                            account_state.pause_event.set()
                                            logger.warning("❌ CAPTCHA DETECTED - Account: %s | Channel: %s | msg_id=%s", account_id, account_state.channel_id, msg_id)
                                            break

                        except Exception as e:
                            logger.debug("Error checking account %s: %s", account_id, e)

                time.sleep(CAPTCHA_CHECK_INTERVAL)
            except Exception as e:
                logger.error("Captcha checker top-level error: %s", e)
                time.sleep(CAPTCHA_CHECK_INTERVAL)

    def stop_checking(self):
        self.running = False


captcha_checker = CentralCaptchaChecker()


# ============================================================================
# Per-account captcha handling and message loop
# ============================================================================

def handle_captcha_for_account(account_state: AccountState, hcaptcha_solver: HCaptchaSolver, discord: DiscordAPIClient):
    aid = account_state.account_id
    account_state.is_solving = True

    try:
        logger.info("Sending captcha notice for %s", aid)
        # Optional notice (defensive; will skip if paused)
        discord.send_message(account_state.channel_id, "oh no i got a captcha let me solve it", account_state=account_state)

        time.sleep(1)

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            logger.info("Solving captcha for %s (attempt %d/%d)", aid, attempt, max_attempts)
            success = hcaptcha_solver.solve_captcha(account_state.token, GUILD_ID)
            if success:
                logger.info("CAPTCHA SOLVED - Account: %s", aid)

                # First, try to confirm via OwO DM
                logger.info("[%s] verify succeeded, checking OwO DM for confirmation", aid)
                dm_channel = discord.get_dm_channel_with(str(OWO_BOT_ID))
                verified = False
                if dm_channel:
                    deadline = time.time() + DM_POLL_TIMEOUT
                    while time.time() < deadline:
                        msgs = discord.fetch_messages(dm_channel, limit=10)
                        for m in msgs:
                            auth = str(m.get("author", {}).get("id", ""))
                            content = (m.get("content") or "").lower()
                            if auth == str(OWO_BOT_ID):
                                for phrase in DM_VERIFIED_PHRASES:
                                    if phrase in content:
                                        verified = True
                                        break
                                if verified:
                                    break
                        if verified:
                            break
                        time.sleep(DM_POLL_INTERVAL)

                if verified:
                    # Unpause immediately and mark handled
                    account_state.is_paused = False
                    account_state.pause_event.clear()
                    account_state.last_solved_at = time.time()
                    account_state.is_solving = False
                    # mark handled message id if present
                    if account_state.captcha_message_id:
                        account_state.handled_owo_message_ids.add(account_state.captcha_message_id)
                        account_state.captcha_message_id = None
                    logger.info("[%s] Resumed after OwO DM verification", aid)
                    return True
                else:
                    # Fallback: post trigger message into channel (force send) so CentralCaptchaChecker can resume it
                    logger.info("[%s] OwO DM not seen within timeout, posting fallback trigger", aid)
                    discord.send_message(account_state.channel_id, TRIGGER_TEXT, account_state=account_state, force=True)
                    account_state.last_solved_at = time.time()
                    account_state.is_solving = False
                    # mark handled so we don't re-open same message
                    if account_state.captcha_message_id:
                        account_state.handled_owo_message_ids.add(account_state.captcha_message_id)
                        account_state.captcha_message_id = None
                    # keep is_paused True; CentralCaptchaChecker will clear it when it sees the trigger
                    return True

            else:
                account_state.solve_retries += 1
                logger.warning("Failed to solve captcha for %s on attempt %d", aid, attempt)
                if attempt < max_attempts:
                    backoff = 2 ** attempt
                    logger.info("Waiting %ds before retrying for %s", backoff, aid)
                    time.sleep(backoff)

        logger.error("All captcha solve attempts failed for %s. Marking for manual review.", aid)
        account_state.is_solving = False
        account_state.needs_manual_intervention = True
        account_state.message_loop_active = False
        return False

    except Exception as e:
        logger.error("Exception handling captcha for %s: %s", aid, e)
        account_state.is_solving = False
        return False


def handle_account(token: str, channel_id: str, hcaptcha_solver: HCaptchaSolver):
    aid = short_id(token)
    account_state: Optional[AccountState] = None
    try:
        logger.info("Starting account %s -> channel %s", aid, channel_id)
        account_state = AccountState(token=token, channel_id=channel_id, account_id=aid)
        captcha_checker.register_account(account_state)

        discord = DiscordAPIClient(token)
        # resolve user id for resume trigger by self
        user_id = discord.get_current_user_id()
        if user_id:
            account_state.user_id = user_id
            logger.info("[%s] resolved user_id = %s", aid, user_id)
        else:
            logger.warning("[%s] could not resolve user id; resume trigger by self won't work", aid)

        account_state.message_loop_active = True
        logger.info("Starting message loop for account %s", aid)

        if ROUNDS_PER_ACCOUNT == 0:
            loop_iter = cycle(COMMANDS)
        else:
            seq = []
            for i in range(ROUNDS_PER_ACCOUNT):
                seq.append(COMMANDS[i % len(COMMANDS)])
            loop_iter = iter(seq)

        for message in loop_iter:
            # If paused, solve captcha
            if account_state.is_paused:
                logger.info("Account %s paused - solving captcha...", aid)
                handle_captcha_for_account(account_state, hcaptcha_solver, discord)
                # CentralCaptchaChecker will resume when it sees trigger or DM
                continue

            wait_time = parse_interval(COMMAND_INTERVAL_CFG)
            if wait_time < 0.01:
                wait_time = 0.01

            logger.info("[%s] Next message in %.1fs: %s", aid, wait_time, message)

            # wait but respond immediately to pause_event
            wait_end = time.time() + wait_time
            while True:
                now = time.time()
                remaining = wait_end - now
                if remaining <= 0:
                    break
                was_set = account_state.pause_event.wait(timeout=min(remaining, 0.5))
                if was_set or account_state.is_paused:
                    logger.info("Account %s paused during wait - solving captcha...", aid)
                    handle_captcha_for_account(account_state, hcaptcha_solver, discord)
                    break

            if not account_state.is_paused:
                ok = discord.send_message(channel_id, message, account_state=account_state)
                if ok:
                    logger.info("[%s] Message sent: %s", aid, message)
                else:
                    logger.warning("[%s] Failed to send message: %s", aid, message)
                time.sleep(random.uniform(0.2, 0.8))

    except Exception as e:
        logger.error("Exception in handle_account %s: %s", aid, e)
    finally:
        if account_state:
            account_state.message_loop_active = False
            captcha_checker.unregister_account(account_state.account_id)
        logger.info("Finished account %s", aid)


# ============================================================================
# Main
# ============================================================================

def parse_tokens(path: str):
    if not os.path.exists(path):
        logger.error("Tokens file not found: %s", path)
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            if ":" in s:
                token, ch = s.split(":", 1)
                token = token.strip()
                ch = ch.strip()
                if token and ch:
                    out.append((token, ch))
            else:
                logger.warning("Malformed tokens line: %s", s)
    return out


def main():
    logger.info("=" * 60)
    logger.info("Headless Discord Bot Runner - Starting (API detection mode)")
    logger.info("=" * 60)

    if not GUILD_ID:
        logger.error("GUILD_ID not set in config.py")
        return

    accounts = parse_tokens(TOKENS_FILE)
    if not accounts:
        logger.error("No accounts found in tokens file")
        return

    enabled = [s for s, cfg in CAPTCHA_SOLVERS.items() if cfg.get("enabled")]
    if not enabled:
        logger.error("No captcha solvers enabled in config.py")
        return
    logger.info("Enabled captcha solvers: %s", ", ".join(enabled))

    hcaptcha_solver = HCaptchaSolver()
    captcha_checker.initialize_browser()
    captcha_checker.start_checking()

    max_workers = len(accounts) if CONCURRENCY <= 0 else min(CONCURRENCY, len(accounts))
    logger.info("Running %d accounts with concurrency=%d (API detection)", len(accounts), max_workers)
    logger.info("=" * 60)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = []
        for token, ch in accounts:
            futures.append(ex.submit(handle_account, token, ch, hcaptcha_solver))
        for f in futures:
            try:
                f.result()
            except Exception as e:
                logger.error("Account job failed: %s", e)

    captcha_checker.stop_checking()
    logger.info("=" * 60)
    logger.info("All done")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
```

i want it to do some more thing
like this time 

it firstly sends message 
owo cash - checks how much cash we do have 
then owo bot replies with the amount the account has 




then it starts betting with 
owo cf 50 
if this loses it doubles bet amount  and instead of cf it does slots 

if slots loses too it doubles bet amount and goes back to cf 

and keeps repeating the proccess and also counts the wins and loses wins in green colour loses in red colour 



ill give u one code that i have we want its tokens.txt thing its captcha solving thing
tokens logging in things and working on api thing

this
Thanks — I updated your headless API-based runner to implement the betting flow you described and added per-account win/loss counting with colored console output. Changes I made (summary):

New config fallback INITIAL_BET (defaults to 50 if not in config.py).
AccountState extended with fields: initial_bet, current_bet, wins, losses, next_game_is_cf.
On account start we now send "owo cash", parse OwO's reply to read the account's cowoncy balance (best-effort regex).
Betting loop:
Starts with "owo cf {bet}" (initial bet = INITIAL_BET).
If that loses: doubles bet and next command becomes "owo slots".
If slots loses: doubles bet and switches back to "owo cf".
If any bet wins: reset bet to INITIAL_BET and go back to "owo cf".
The loop respects pause/captcha handling already present.
Response handling: after sending a command we poll channel messages (short timeout) for an OwO bot reply and attempt to detect win/loss based on keywords (you won/gained/you lost/lost it all/etc). Best-effort parsing only (OwO messages vary).
Colored output: wins printed in green, losses in red (ANSI escape codes). Also included concise per-account stats output after each round.
Kept all existing captcha solving & central checker logic; integration is thread-safe and uses the existing DiscordAPIClient send/fetch methods.
No change to tokens / captcha config parsing; the script continues to use tokens.txt, config.py, and the solver logic you already have.
Below is the full modified script. Drop it in place of your previous file and run as before. If you want tweaks (e.g., different initial bet per account, max-bet cap, safer parsing for specific OwO message formats, or logging colors instead of print), tell me which and I’ll update it.

Python
#!/usr/bin/env python3
"""
Full bot.py - Headless Discord multi-token runner with API-based captcha detection and DM-confirm resume.

Features:
- Discord REST API used for sending/fetching messages and DM handling.
- hCaptcha solving via configurable solvers (NopeCHA / Capsolver / 2Captcha).
- Central captcha checker that detects OwO captcha messages and pauses affected accounts.
- After solve: poll OwO DM for authoritative verification phrase; fallback to posting a trigger in channel.
- Avoid reprocessing the same OwO captcha message by tracking handled message IDs.
- UTF-8-safe logging for Windows consoles where possible.
"""
import os
import sys
import time
import logging
import hashlib
import random
import threading
import requests
import urllib3
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import re

import config

# Disable urllib3 warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load config
GUILD_ID = config.GUILD_ID
PROFILES_DIR = getattr(config, "PROFILES_DIR", "profiles")
TOKENS_FILE = config.TOKENS_FILE
CONCURRENCY = getattr(config, "CONCURRENCY", 1)
COMMANDS = config.COMMANDS
COMMAND_INTERVAL_CFG = config.COMMAND_INTERVAL
ROUNDS_PER_ACCOUNT = config.ROUNDS_PER_ACCOUNT
LOG_FILE = getattr(config, "LOG_FILE", "multi_token_runner.log")

# New: initial bet default (can be overridden in config.py)
INITIAL_BET = getattr(config, "INITIAL_BET", 50)

# Captcha config
OWO_BOT_ID = config.OWO_BOT_ID
CAPTCHA_CHECK_INTERVAL = getattr(config, "CAPTCHA_CHECK_INTERVAL", 8)
CAPTCHA_SOLVE_TIMEOUT = getattr(config, "CAPTCHA_SOLVE_TIMEOUT", 120)
CAPTCHA_KEYWORDS = [kw.lower() for kw in (getattr(config, "CAPTCHA_KEYWORDS", []) or [])]
CAPTCHA_SOLVERS = getattr(config, "CAPTCHA_SOLVERS", {})
CAPTCHA_SOLVER_ORDER = getattr(config, "CAPTCHA_SOLVER_ORDER", list(CAPTCHA_SOLVERS.keys()))

# hCaptcha constants (sitekey / page for OwO)
HCAPTCHA_SITEKEY = "a6a1d5ce-612d-472d-8e37-7601408fbc09"
HCAPTCHA_PAGE_URL = "https://owobot.com/captcha"

# Resume trigger and cooldown (can be overridden in config if you add them there)
TRIGGER_TEXT = getattr(config, "TRIGGER_TEXT", "captcha solved! resuming")
POST_SOLVE_COOLDOWN = getattr(config, "POST_SOLVE_COOLDOWN", 12)

# DM polling
DM_POLL_TIMEOUT = getattr(config, "DM_POLL_TIMEOUT", 30)
DM_POLL_INTERVAL = getattr(config, "DM_POLL_INTERVAL", 2)
DM_VERIFIED_PHRASES = [p.lower() for p in getattr(config, "DM_VERIFIED_PHRASES", [
    "i have verified that you are human",
    "you're free to go",
    "you are human",
    "verified"
])]

# Logging (UTF-8 safe handler on Windows if possible)
from logging import FileHandler, StreamHandler, Formatter, getLogger, INFO

file_handler = FileHandler(LOG_FILE) if LOG_FILE else None
if file_handler:
    file_handler.setFormatter(Formatter("%(asctime)s - %(levelname)s - %(message)s"))

try:
    stream = sys.stdout
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")
    stream_handler = StreamHandler(stream)
except Exception:
    stream_handler = StreamHandler()
stream_handler.setFormatter(Formatter("%(asctime)s - %(levelname)s - %(message)s"))

handlers = []
if file_handler:
    handlers.append(file_handler)
handlers.append(stream_handler)

logging.basicConfig(level=INFO, handlers=handlers)
logger = getLogger(__name__)

# Suppress noisy urllib3 logs
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)


@dataclass
class AccountState:
    """Track per-account state"""
    token: str
    channel_id: str
    account_id: str
    driver: Optional[object] = None
    is_paused: bool = False
    captcha_detected_at: Optional[datetime] = None
    is_solving: bool = False
    message_loop_active: bool = False
    pause_event: threading.Event = field(default_factory=threading.Event)
    solve_retries: int = 0
    last_solved_at: Optional[float] = None
    needs_manual_intervention: bool = False
    user_id: Optional[str] = None  # Discord user id (string)
    # New fields to avoid reprocessing the same OwO message
    handled_owo_message_ids: set = field(default_factory=set)
    captcha_message_id: Optional[str] = None

    # Betting state
    initial_bet: int = field(default_factory=lambda: INITIAL_BET)
    current_bet: int = field(default_factory=lambda: INITIAL_BET)
    wins: int = 0
    losses: int = 0
    # True => next game is coinflip (cf), False => slots
    next_game_is_cf: bool = True


def short_id(token: str) -> str:
    return hashlib.sha1(token.encode("utf-8")).hexdigest()[:10]


def parse_interval(cfg) -> float:
    """Parse a COMMAND_INTERVAL-like config into a float seconds."""
    if isinstance(cfg, (int, float)):
        return float(cfg)
    if not isinstance(cfg, str):
        return 20.0
    s = cfg.strip()
    if "-" in s:
        a, b = s.split("-", 1)
        try:
            a_f = float(a)
            b_f = float(b)
            lo, hi = (a_f, b_f) if a_f <= b_f else (b_f, a_f)
            return random.uniform(lo, hi)
        except Exception:
            return 20.0
    try:
        return float(s)
    except Exception:
        return 20.0


def create_session():
    """requests.Session with retries/connection pooling"""
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5, total=5)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# ============================================================================
# HCaptcha solver implementations (Capsolver, NopeCHA, 2Captcha)
# ============================================================================

class HCaptchaSolver:
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self):
        self.enabled_solvers = self._get_enabled_solvers()

    def _get_enabled_solvers(self) -> list:
        enabled = []
        for name in CAPTCHA_SOLVER_ORDER:
            cfg = CAPTCHA_SOLVERS.get(name)
            if cfg and cfg.get("enabled"):
                enabled.append(name)
        return enabled

    def _solve_capsolver(self, api_key: str) -> Optional[str]:
        session = create_session()
        try:
            resp = session.post("https://api.capsolver.com/createTask", json={
                "clientKey": api_key,
                "task": {
                    "type": "HCaptchaTaskProxyLess",
                    "websiteURL": HCAPTCHA_PAGE_URL,
                    "websiteKey": HCAPTCHA_SITEKEY,
                }
            }, timeout=15)
            logger.debug("Capsolver create status=%s body=%s", resp.status_code, resp.text[:1000])
            data = resp.json()
            task_id = data.get("taskId")
            if not task_id:
                logger.debug("Capsolver create failed: %s", data)
                return None
            for _ in range(60):
                time.sleep(3)
                poll = session.post("https://api.capsolver.com/getTaskResult", json={"clientKey": api_key, "taskId": task_id}, timeout=15)
                logger.debug("Capsolver poll status=%s body=%s", poll.status_code, poll.text[:1000])
                pd = poll.json()
                if pd.get("status") == "ready":
                    token = pd.get("solution", {}).get("gRecaptchaResponse")
                    if token:
                        logger.info("Capsolver solved hCaptcha")
                        return token
                if pd.get("status") == "failed" or pd.get("errorCode"):
                    logger.debug("Capsolver failure: %s", pd)
                    return None
            logger.debug("Capsolver timed out")
            return None
        except Exception as e:
            logger.debug("Capsolver exception: %s", e)
            return None

    def _solve_nopecha(self, api_key: str) -> Optional[str]:
        session = create_session()
        try:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            sub = session.post("https://api.nopecha.com/token", json={"type": "hcaptcha", "sitekey": HCAPTCHA_SITEKEY, "url": HCAPTCHA_PAGE_URL}, headers=headers, timeout=15)
            logger.debug("NopeCHA submit status=%s body=%s", sub.status_code, sub.text[:1000])
            sd = sub.json()
            task_id = sd.get("data")
            if not task_id:
                logger.debug("NopeCHA submit failed: %s", sd)
                return None
            for _ in range(180):
                time.sleep(1)
                poll = session.get(f"https://api.nopecha.com/token?id={task_id}", headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
                logger.debug("NopeCHA poll status=%s body=%s", poll.status_code, poll.text[:1000])
                if poll.status_code == 409:
                    continue
                pd = poll.json()
                token = pd.get("data")
                if token and isinstance(token, str):
                    logger.info("NopeCHA solved hCaptcha")
                    return token
                logger.debug("NopeCHA poll returned: %s", pd)
                return None
            logger.debug("NopeCHA timed out")
            return None
        except Exception as e:
            logger.debug("NopeCHA exception: %s", e)
            return None

    def _solve_2captcha(self, api_key: str) -> Optional[str]:
        session = create_session()
        try:
            data = {
                "key": api_key,
                "method": "hcaptcha",
                "sitekey": HCAPTCHA_SITEKEY,
                "pageurl": HCAPTCHA_PAGE_URL,
                "json": 1,
            }
            sub = session.post("https://2captcha.com/in.php", data=data, timeout=15)
            logger.debug("2Captcha submit status=%s body=%s", sub.status_code, sub.text[:1000])
            try:
                sd = sub.json()
            except Exception:
                logger.debug("2Captcha submit non-json: %s", sub.text[:1000])
                return None
            if sd.get("status") != 1:
                logger.debug("2Captcha submit failed: %s", sd.get("request"))
                return None
            captcha_id = sd.get("request")
            if not captcha_id:
                logger.debug("2Captcha no id: %s", sd)
                return None
            for _ in range(40):
                time.sleep(5)
                poll_url = f"https://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}&json=1"
                poll = session.get(poll_url, timeout=15)
                logger.debug("2Captcha poll status=%s body=%s", poll.status_code, poll.text[:1000])
                try:
                    pd = poll.json()
                except Exception:
                    logger.debug("2Captcha poll non-json: %s", poll.text[:1000])
                    continue
                if pd.get("status") == 1:
                    token = pd.get("request")
                    logger.info("2Captcha solved hCaptcha")
                    return token
                if pd.get("request") != "CAPCHA_NOT_READY":
                    logger.debug("2Captcha poll error: %s", pd)
                    return None
            logger.debug("2Captcha timed out")
            return None
        except Exception as e:
            logger.debug("2Captcha exception: %s", e)
            return None

    def solve_captcha(self, discord_token: str, guild_id: Optional[str] = None) -> bool:
        """Perform the OAuth->redirect->solve->verify flow using a fresh session."""
        try:
            if not self.enabled_solvers:
                logger.error("No captcha solvers enabled!")
                return False

            session = create_session()
            ua_headers = {"User-Agent": self.UA}

            logger.info("Step 1: Getting Discord OAuth2 URL from owobot...")
            auth_res = session.get("https://owobot.com/api/auth/discord", allow_redirects=False, headers=ua_headers, timeout=10)
            oauth_loc = auth_res.headers.get("Location") or auth_res.headers.get("location")
            if not oauth_loc or "discord.com" not in oauth_loc:
                logger.error("owobot oauth returned unexpected response")
                return False

            oauth_url = urlparse(oauth_loc)
            oauth_params = parse_qs(oauth_url.query)
            client_id = oauth_params.get("client_id", [""])[0]
            redirect_uri = oauth_params.get("redirect_uri", [""])[0]
            scope = oauth_params.get("scope", ["identify"])[0]
            state = oauth_params.get("state", [None])[0]
            if not client_id or not redirect_uri:
                logger.error("Could not parse OAuth2 parameters")
                return False

            logger.info("Step 2: Authorizing with Discord...")
            auth_url = (f"https://discord.com/api/v9/oauth2/authorize"
                        f"?client_id={client_id}"
                        f"&redirect_uri={redirect_uri}"
                        f"&response_type=code"
                        f"&scope={scope}")
            if state:
                auth_url += f"&state={state}"

            auth_body = {"permissions": "0", "authorize": True}
            if guild_id:
                auth_body["guild_id"] = guild_id

            discord_res = session.post(auth_url, json=auth_body,
                                      headers={"Authorization": discord_token, "Content-Type": "application/json", "User-Agent": self.UA},
                                      allow_redirects=False, timeout=10)
            if not discord_res.ok:
                try:
                    err = discord_res.json().get("message", f"Discord {discord_res.status_code}")
                except Exception:
                    err = f"Discord {discord_res.status_code}"
                logger.error("Discord authorization failed: %s", err)
                return False

            cb = None
            try:
                cb = discord_res.json().get("location")
            except Exception:
                pass
            if not cb:
                cb = discord_res.headers.get("Location") or discord_res.headers.get("location")
            if not cb:
                logger.error("Discord returned no callback URL")
                return False

            logger.info("Discord OAuth2 authorized")

            logger.info("Step 3: Following OAuth2 redirects...")
            current_url = cb
            for _ in range(8):
                follow_res = session.get(current_url, allow_redirects=False, headers=ua_headers, timeout=10)
                next_loc = follow_res.headers.get("Location") or follow_res.headers.get("location")
                if not next_loc or follow_res.status_code < 300 or follow_res.status_code >= 400:
                    break
                current_url = urljoin("https://owobot.com", next_loc)

            logger.info("Session established with cookies: %s", list(session.cookies.keys()))

            logger.info("Step 4: Solving hCaptcha...")
            hcaptcha_token = None
            for solver in self.enabled_solvers:
                logger.info("Trying solver %s...", solver)
                if solver == "capsolver":
                    api_key = CAPTCHA_SOLVERS.get("capsolver", {}).get("api_key")
                    if api_key:
                        hcaptcha_token = self._solve_capsolver(api_key)
                        if hcaptcha_token:
                            break
                elif solver == "nopecha":
                    api_key = CAPTCHA_SOLVERS.get("nopecha", {}).get("api_key")
                    if api_key:
                        hcaptcha_token = self._solve_nopecha(api_key)
                        if hcaptcha_token:
                            break
                elif solver == "2captcha":
                    api_key = CAPTCHA_SOLVERS.get("2captcha", {}).get("api_key")
                    if api_key:
                        hcaptcha_token = self._solve_2captcha(api_key)
                        if hcaptcha_token:
                            break

            if not hcaptcha_token:
                logger.error("Failed to obtain hCaptcha token from solvers")
                return False

            logger.info("Step 5: Submitting solution to owobot.com...")
            verify_res = session.post("https://owobot.com/api/captcha/verify",
                                      json={"token": hcaptcha_token},
                                      headers={"Content-Type": "application/json", "User-Agent": self.UA, "Origin": "https://owobot.com", "Referer": "https://owobot.com/captcha"},
                                      timeout=15)
            if verify_res.ok:
                logger.info("CAPTCHA VERIFIED on owobot.com")
                return True
            else:
                logger.error("owobot verify failed %s: %s", verify_res.status_code, verify_res.text[:300])
                return False

        except Exception as e:
            logger.error("Exception in solve_captcha: %s", e)
            return False


# ============================================================================
# Discord API client helper
# ============================================================================

class DiscordAPIClient:
    def __init__(self, token: str):
        self.token = token
        self.session = create_session()
        self.base_url = "https://discord.com/api/v9"
        self.headers = {"Authorization": token, "User-Agent": "Mozilla/5.0"}

    def send_message(self, channel_id: str, content: str, account_state: Optional[AccountState] = None, force: bool = False) -> bool:
        """Send a message to a channel. If force=True, bypass paused check for this send."""
        try:
            if account_state and account_state.is_paused and not force:
                logger.info("Skipping send_message because account is paused")
                return False
            url = f"{self.base_url}/channels/{channel_id}/messages"
            resp = self.session.post(url, json={"content": content}, headers=self.headers, timeout=10)
            if resp.status_code in (200, 201):
                logger.info("Message sent via API: %s", content)
                return True
            logger.warning("Failed to send message: HTTP %s - %s", resp.status_code, resp.text[:300])
            return False
        except Exception as e:
            logger.error("Error sending message: %s", e)
            return False

    def fetch_messages(self, channel_id: str, limit: int = 20) -> List[dict]:
        """Fetch recent messages for a channel (or DM channel)."""
        try:
            url = f"{self.base_url}/channels/{channel_id}/messages?limit={limit}"
            resp = self.session.get(url, headers=self.headers, timeout=10)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.debug("fetch_messages HTTP %s: %s", resp.status_code, resp.text[:300])
            return []
        except Exception as e:
            logger.debug("fetch_messages error: %s", e)
            return []

    def get_current_user_id(self) -> Optional[str]:
        try:
            resp = self.session.get(f"{self.base_url}/users/@me", headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("id")
            logger.debug("get_current_user_id HTTP %s: %s", resp.status_code, resp.text[:300])
            return None
        except Exception as e:
            logger.debug("get_current_user_id error: %s", e)
            return None

    def get_dm_channel_with(self, recipient_id: str) -> Optional[str]:
        """Create or return DM channel ID with recipient (OwO bot)."""
        try:
            resp = self.session.post(f"{self.base_url}/users/@me/channels", json={"recipient_id": recipient_id}, headers=self.headers, timeout=10)
            if resp.status_code in (200, 201):
                return resp.json().get("id")
            logger.debug("get_dm_channel_with HTTP %s: %s", resp.status_code, resp.text[:300])
            return None
        except Exception as e:
            logger.debug("get_dm_channel_with error: %s", e)
            return None


# ============================================================================
# Central captcha checker
# ============================================================================

class CentralCaptchaChecker:
    def __init__(self):
        self.accounts: Dict[str, AccountState] = {}
        self.lock = threading.Lock()
        self.running = True

    def initialize_browser(self):
        logger.info("Central captcha checker initialized (API-based detection)")

    def register_account(self, account_state: AccountState):
        with self.lock:
            self.accounts[account_state.account_id] = account_state

    def unregister_account(self, account_id: str):
        with self.lock:
            if account_id in self.accounts:
                del self.accounts[account_id]

    def start_checking(self):
        t = threading.Thread(target=self._check_loop, daemon=True)
        t.start()
        logger.info("Central captcha checker started (API)")

    def _parse_msg_ts(self, ts: Optional[str]) -> Optional[datetime]:
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None

    def _check_loop(self):
        while self.running:
            try:
                with self.lock:
                    for account_id, account_state in list(self.accounts.items()):
                        # skip inactive / solving / manual accounts
                        if not account_state.message_loop_active or account_state.is_solving or account_state.needs_manual_intervention:
                            continue

                        # respect cooldown after successful solve
                        now_ts = time.time()
                        if account_state.last_solved_at and (now_ts - account_state.last_solved_at) < POST_SOLVE_COOLDOWN:
                            continue

                        try:
                            discord = DiscordAPIClient(account_state.token)
                            msgs = discord.fetch_messages(account_state.channel_id, limit=25)

                            # If paused: look for account's own trigger message and compare with OwO captcha message timestamps
                            if account_state.is_paused and account_state.captcha_detected_at:
                                latest_trigger_ts = None
                                latest_owo_ts = None
                                for m in msgs:
                                    msg_id = m.get("id")
                                    author_id = str(m.get("author", {}).get("id", ""))
                                    content = (m.get("content") or "").lower()
                                    ts = self._parse_msg_ts(m.get("timestamp"))
                                    # account's own trigger message
                                    if account_state.user_id and author_id == str(account_state.user_id) and TRIGGER_TEXT in content:
                                        if ts and (latest_trigger_ts is None or ts > latest_trigger_ts):
                                            latest_trigger_ts = ts
                                    # OwO captcha message (if not already handled)
                                    if msg_id and msg_id in account_state.handled_owo_message_ids:
                                        continue
                                    if author_id == str(OWO_BOT_ID):
                                        if ("⚠️" in content) or any(kw in content for kw in CAPTCHA_KEYWORDS):
                                            if ts and (latest_owo_ts is None or ts > latest_owo_ts):
                                                latest_owo_ts = ts

                                # If trigger exists and is newer-or-equal, resume account
                                if latest_trigger_ts and (not latest_owo_ts or latest_trigger_ts >= latest_owo_ts):
                                    account_state.is_paused = False
                                    account_state.pause_event.clear()
                                    account_state.last_solved_at = time.time()
                                    logger.info("✅ Resuming account %s after seeing trigger message/DM", account_id)
                                    continue

                            # If not paused, detect new OwO captcha messages (skip handled ones)
                            if not account_state.is_paused:
                                for m in msgs:
                                    msg_id = m.get("id")
                                    author_id = str(m.get("author", {}).get("id", ""))
                                    content = (m.get("content") or "").lower()
                                    if msg_id and msg_id in account_state.handled_owo_message_ids:
                                        continue
                                    if author_id == str(OWO_BOT_ID):
                                        if ("⚠️" in content) or any(kw in content for kw in CAPTCHA_KEYWORDS):
                                            account_state.is_paused = True
                                            account_state.captcha_detected_at = datetime.now()
                                            account_state.captcha_message_id = msg_id
                                            account_state.pause_event.set()
                                            logger.warning("❌ CAPTCHA DETECTED - Account: %s | Channel: %s | msg_id=%s", account_id, account_state.channel_id, msg_id)
                                            break

                        except Exception as e:
                            logger.debug("Error checking account %s: %s", account_id, e)

                time.sleep(CAPTCHA_CHECK_INTERVAL)
            except Exception as e:
                logger.error("Captcha checker top-level error: %s", e)
                time.sleep(CAPTCHA_CHECK_INTERVAL)

    def stop_checking(self):
        self.running = False


captcha_checker = CentralCaptchaChecker()


# ============================================================================
# Per-account captcha handling and message loop
# ============================================================================

def handle_captcha_for_account(account_state: AccountState, hcaptcha_solver: HCaptchaSolver, discord: DiscordAPIClient):
    aid = account_state.account_id
    account_state.is_solving = True

    try:
        logger.info("Sending captcha notice for %s", aid)
        # Optional notice (defensive; will skip if paused)
        discord.send_message(account_state.channel_id, "oh no i got a captcha let me solve it", account_state=account_state)

        time.sleep(1)

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            logger.info("Solving captcha for %s (attempt %d/%d)", aid, attempt, max_attempts)
            success = hcaptcha_solver.solve_captcha(account_state.token, GUILD_ID)
            if success:
                logger.info("CAPTCHA SOLVED - Account: %s", aid)

                # First, try to confirm via OwO DM
                logger.info("[%s] verify succeeded, checking OwO DM for confirmation", aid)
                dm_channel = discord.get_dm_channel_with(str(OWO_BOT_ID))
                verified = False
                if dm_channel:
                    deadline = time.time() + DM_POLL_TIMEOUT
                    while time.time() < deadline:
                        msgs = discord.fetch_messages(dm_channel, limit=10)
                        for m in msgs:
                            auth = str(m.get("author", {}).get("id", ""))
                            content = (m.get("content") or "").lower()
                            if auth == str(OWO_BOT_ID):
                                for phrase in DM_VERIFIED_PHRASES:
                                    if phrase in content:
                                        verified = True
                                        break
                                if verified:
                                    break
                        if verified:
                            break
                        time.sleep(DM_POLL_INTERVAL)

                if verified:
                    # Unpause immediately and mark handled
                    account_state.is_paused = False
                    account_state.pause_event.clear()
                    account_state.last_solved_at = time.time()
                    account_state.is_solving = False
                    # mark handled message id if present
                    if account_state.captcha_message_id:
                        account_state.handled_owo_message_ids.add(account_state.captcha_message_id)
                        account_state.captcha_message_id = None
                    logger.info("[%s] Resumed after OwO DM verification", aid)
                    return True
                else:
                    # Fallback: post trigger message into channel (force send) so CentralCaptchaChecker can resume it
                    logger.info("[%s] OwO DM not seen within timeout, posting fallback trigger", aid)
                    discord.send_message(account_state.channel_id, TRIGGER_TEXT, account_state=account_state, force=True)
                    account_state.last_solved_at = time.time()
                    account_state.is_solving = False
                    # mark handled so we don't re-open same message
                    if account_state.captcha_message_id:
                        account_state.handled_owo_message_ids.add(account_state.captcha_message_id)
                        account_state.captcha_message_id = None
                    # keep is_paused True; CentralCaptchaChecker will clear it when it sees the trigger
                    return True

            else:
                account_state.solve_retries += 1
                logger.warning("Failed to solve captcha for %s on attempt %d", aid, attempt)
                if attempt < max_attempts:
                    backoff = 2 ** attempt
                    logger.info("Waiting %ds before retrying for %s", backoff, aid)
                    time.sleep(backoff)

        logger.error("All captcha solve attempts failed for %s. Marking for manual review.", aid)
        account_state.is_solving = False
        account_state.needs_manual_intervention = True
        account_state.message_loop_active = False
        return False

    except Exception as e:
        logger.error("Exception handling captcha for %s: %s", aid, e)
        account_state.is_solving = False
        return False


# Helper: parse timestamps (simple)
def _parse_msg_ts(ts: Optional[str]) -> Optional[float]:
    if not ts:
        return None
    try:
        # Return epoch seconds
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return None


# Helper: try to extract numeric cowoncy amount from typical OwO 'cash' messages
_CASH_RE = re.compile(r"([0-9][0-9,]*)\s*(?:cowoncy|coins|coin|💰)?", re.IGNORECASE)


def parse_balance_from_owo_message(content: str) -> Optional[int]:
    if not content:
        return None
    # Look for "You have X cowoncy" or similar
    m = _CASH_RE.search(content.replace(".", ""))
    if m:
        num = m.group(1).replace(",", "")
        try:
            return int(num)
        except Exception:
            return None
    return None


# Colors
COLOR_GREEN = "\x1b[32m"
COLOR_RED = "\x1b[31m"
COLOR_RESET = "\x1b[0m"


def send_command_and_wait_for_owo_response(discord: DiscordAPIClient, account_state: AccountState, channel_id: str, command: str, timeout: int = 20) -> Optional[dict]:
    """
    Send a command and poll the channel for an OwO response. Returns the OwO message dict or None.
    Best-effort: we look for messages authored by OWO_BOT_ID that appear after sending.
    """
    try:
        # Get baseline newest timestamp
        before_msgs = discord.fetch_messages(channel_id, limit=5)
        before_ts = max((_parse_msg_ts(m.get("timestamp")) or 0) for m in before_msgs) if before_msgs else time.time()

        sent = discord.send_message(channel_id, command, account_state=account_state)
        if not sent:
            return None

        deadline = time.time() + timeout
        last_found = None
        while time.time() < deadline:
            msgs = discord.fetch_messages(channel_id, limit=20)
            for m in msgs:
                author_id = str(m.get("author", {}).get("id", ""))
                ts = _parse_msg_ts(m.get("timestamp")) or 0
                content = (m.get("content") or "")
                if author_id == str(OWO_BOT_ID) and ts >= before_ts:
                    # Return the newest OwO message after the command
                    if not last_found or ts > (_parse_msg_ts(last_found.get("timestamp")) or 0):
                        last_found = m
            if last_found:
                # simple stabilization: ensure message remains the newest for a short moment
                time.sleep(1)
                return last_found
            time.sleep(1)
        return last_found
    except Exception as e:
        logger.debug("send_command_and_wait_for_owo_response error: %s", e)
        return None


def handle_account(token: str, channel_id: str, hcaptcha_solver: HCaptchaSolver):
    aid = short_id(token)
    account_state: Optional[AccountState] = None
    try:
        logger.info("Starting account %s -> channel %s", aid, channel_id)
        account_state = AccountState(token=token, channel_id=channel_id, account_id=aid)
        captcha_checker.register_account(account_state)

        discord = DiscordAPIClient(token)
        # resolve user id for resume trigger by self
        user_id = discord.get_current_user_id()
        if user_id:
            account_state.user_id = user_id
            logger.info("[%s] resolved user_id = %s", aid, user_id)
        else:
            logger.warning("[%s] could not resolve user id; resume trigger by self won't work", aid)

        account_state.message_loop_active = True
        account_state.initial_bet = INITIAL_BET
        account_state.current_bet = account_state.initial_bet
        account_state.next_game_is_cf = True  # start with coinflip

        logger.info("Starting message loop for account %s", aid)

        # First: check account balance via "owo cash"
        try:
            logger.info("[%s] Sending `owo cash` to check balance", aid)
            cash_msg = send_command_and_wait_for_owo_response(discord, account_state, channel_id, "owo cash", timeout=8)
            balance = None
            if cash_msg:
                content = (cash_msg.get("content") or "")
                balance = parse_balance_from_owo_message(content)
                if balance is not None:
                    logger.info("[%s] Balance detected: %s cowoncy", aid, balance)
                else:
                    logger.info("[%s] Could not parse balance from OwO message content", aid)
            else:
                logger.info("[%s] No OwO reply to `owo cash` (continuing anyway)", aid)
        except Exception as e:
            logger.debug("[%s] error while checking balance: %s", aid, e)

        # Build message iterator/loop according to ROUNDS_PER_ACCOUNT
        if ROUNDS_PER_ACCOUNT == 0:
            rounds_iter = None  # means loop forever
        else:
            rounds_left = ROUNDS_PER_ACCOUNT

        # Betting loop
        round_count = 0
        while account_state.message_loop_active:
            # Respect pause/captcha
            if account_state.is_paused:
                logger.info("Account %s paused - solving captcha...", aid)
                handle_captcha_for_account(account_state, hcaptcha_solver, discord)
                # central checker will handle resume; after returning, re-check paused flag
                time.sleep(1)
                continue

            if ROUNDS_PER_ACCOUNT != 0 and round_count >= ROUNDS_PER_ACCOUNT:
                logger.info("[%s] Completed %d rounds, exiting loop", aid, round_count)
                break

            # Determine which command to send
            bet = account_state.current_bet
            if bet <= 0:
                account_state.current_bet = account_state.initial_bet
                bet = account_state.current_bet
            if account_state.next_game_is_cf:
                command = f"owo cf {bet}"
                game_type = "cf"
            else:
                command = f"owo slots {bet}"
                game_type = "slots"

            logger.info("[%s] Round %d -> sending: %s (bet=%d)", aid, round_count + 1, command, bet)

            # Send command and wait for OwO response
            owo_reply = send_command_and_wait_for_owo_response(discord, account_state, channel_id, command, timeout=20)

            result_text = None
            if owo_reply:
                result_text = (owo_reply.get("content") or "").lower()
                logger.info("[%s] OwO reply: %s", aid, (owo_reply.get("content") or "")[:300])
            else:
                logger.warning("[%s] No OwO reply detected for command %s", aid, command)

            # Determine win/loss
            is_win = False
            is_loss = False
            if result_text:
                # Common indicators
                if any(k in result_text for k in ("you won", "won", "gained", "you gained", "gained cowoncy")):
                    is_win = True
                if any(k in result_text for k in ("you lost", "lost", "lost it all", "you lost all")):
                    is_loss = True

                # Edgecases: if message includes both, decide by presence of 'you won' first
                if "you won" in result_text or "won" in result_text:
                    is_win = True
                    is_loss = False
                elif "you lost" in result_text or "lost" in result_text:
                    is_loss = True
                    is_win = False

            # If no explicit parsing, attempt heuristics: look for "spent" or "cowoncy" increases
            if not is_win and not is_loss and result_text:
                if "spent" in result_text and "lost" in result_text:
                    is_loss = True
                elif "spent" in result_text and "you won" in result_text:
                    is_win = True

            # If still unknown, treat as neither and continue (no bet change)
            if is_win and not is_loss:
                account_state.wins += 1
                account_state.current_bet = account_state.initial_bet
                account_state.next_game_is_cf = True
                # Print colored win
                print(f"{COLOR_GREEN}[{aid}] WIN (game={game_type} bet={bet}){COLOR_RESET}")
                logger.info("[%s] WIN (game=%s bet=%d). Stats: %dW - %dL", aid, game_type, bet, account_state.wins, account_state.losses)
            elif is_loss and not is_win:
                account_state.losses += 1
                # Double the bet
                account_state.current_bet = account_state.current_bet * 2
                # Switch game type: cf -> slots, slots -> cf
                account_state.next_game_is_cf = not account_state.next_game_is_cf
                print(f"{COLOR_RED}[{aid}] LOSS (game={game_type} bet={bet}){COLOR_RESET}")
                logger.warning("[%s] LOSS (game=%s bet=%d). Stats: %dW - %dL - next bet=%d", aid, game_type, bet, account_state.wins, account_state.losses, account_state.current_bet)
            else:
                # Unknown/incomplete response
                logger.warning("[%s] Could not determine result for %s. Leaving bet unchanged (%d).", aid, command, account_state.current_bet)

            # After each round short sleep, but allow immediate reaction to pause_event
            wait_time = parse_interval(COMMAND_INTERVAL_CFG)
            if wait_time < 0.01:
                wait_time = 0.01
            wait_end = time.time() + wait_time
            while True:
                now = time.time()
                remaining = wait_end - now
                if remaining <= 0:
                    break
                was_set = account_state.pause_event.wait(timeout=min(remaining, 0.5))
                if was_set or account_state.is_paused:
                    logger.info("Account %s paused during wait - solving captcha...", aid)
                    handle_captcha_for_account(account_state, hcaptcha_solver, discord)
                    break

            round_count += 1
            # slight jitter between rounds
            time.sleep(random.uniform(0.2, 0.6))

    except Exception as e:
        logger.error("Exception in handle_account %s: %s", aid, e)
    finally:
        if account_state:
            account_state.message_loop_active = False
            captcha_checker.unregister_account(account_state.account_id)
            # Print final stats for account
            print("=" * 30)
            print(f"[{aid}] FINAL STATS: Wins: {account_state.wins} | Losses: {account_state.losses} | Current Bet: {account_state.current_bet}")
            print("=" * 30)
        logger.info("Finished account %s", aid)


# ============================================================================
# Main
# ============================================================================

def parse_tokens(path: str):
    if not os.path.exists(path):
        logger.error("Tokens file not found: %s", path)
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            if ":" in s:
                token, ch = s.split(":", 1)
                token = token.strip()
                ch = ch.strip()
                if token and ch:
                    out.append((token, ch))
            else:
                logger.warning("Malformed tokens line: %s", s)
    return out


def main():
    logger.info("=" * 60)
    logger.info("Headless Discord Bot Runner - Starting (API detection mode)")
    logger.info("=" * 60)

    if not GUILD_ID:
        logger.error("GUILD_ID not set in config.py")
        return

    accounts = parse_tokens(TOKENS_FILE)
    if not accounts:
        logger.error("No accounts found in tokens file")
        return

    enabled = [s for s, cfg in CAPTCHA_SOLVERS.items() if cfg.get("enabled")]
    if not enabled:
        logger.error("No captcha solvers enabled in config.py")
        return
    logger.info("Enabled captcha solvers: %s", ", ".join(enabled))

    hcaptcha_solver = HCaptchaSolver()
    captcha_checker.initialize_browser()
    captcha_checker.start_checking()

    max_workers = len(accounts) if CONCURRENCY <= 0 else min(CONCURRENCY, len(accounts))
    logger.info("Running %d accounts with concurrency=%d (API detection)", len(accounts), max_workers)
    logger.info("=" * 60)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = []
        for token, ch in accounts:
            futures.append(ex.submit(handle_account, token, ch, hcaptcha_solver))
        for f in futures:
            try:
                f.result()
            except Exception as e:
                logger.error("Account job failed: %s", e)

    captcha_checker.stop_checking()
    logger.info("=" * 60)
    logger.info("All done")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
What I tested/assumed

This is a best-effort implementation that relies on the OwO reply message formats being parseable via the keywords/regex used. OwO message formats can change — if you paste a few real OwO replies (for cf and slots), I can tighten the regex and detection logic.
Colored output uses ANSI escapes (works on most terminals). If you need Windows Console compatibility without ANSI, I can add colorama support.
No additional config options were added besides INITIAL_BET (you can set that in config.py) — tell me if you'd like per-account initial bets or a max-bet cap to avoid runaway doubling.
Next steps (optional)

Provide sample OwO response messages (cf win, cf loss, slots win/loss) and I’ll refine the detection rules.
Add a max_bet cap or stop-after-N-losses safety net.
Add persistent per-account logs/stats (CSV or DB).
Add color logging or more structured output (JSON) for monitoring.
If you want any of the above or want smaller adjustments (e.g., change initial bet to 25, add max bet), tell me which and I’ll update the code.

girihhas/cfundtheslottikabutty
can you push this all like all config.py tokens.txt in a repo of mine
I can do that — I’ll push the bot code plus a safe set of supporting files (config template, tokens example, requirements, README, .gitignore) into your repository girihhas/cfundtheslottikabutty on the repo’s default branch.

Before I proceed I need two confirmations from you:

Confirm repo target: owner = girihhas, repo = cfundtheslottikabutty. Is that correct?
Important security note — tokens.txt often contains real Discord tokens which are secrets. Do you want me to:
A) commit a tokens.txt.example (placeholder) and add tokens.txt to .gitignore (recommended), or
B) directly commit a tokens.txt with the actual tokens you provided (NOT recommended and will expose secrets publicly if the repo is public)?
Also tell me if you want any specific branch name (if you don’t specify I will commit to the repository’s default branch).

When you confirm those choices I will push these files:

bot.py — the headless API-based runner you provided (the latest script).
config.py — a template with commented placeholders for GUILD_ID, OWO_BOT_ID, CAPTCHA_SOLVERS, INITIAL_BET, etc.
tokens.txt.example — example format showing token:channel_id lines (no real tokens).
requirements.txt — pinned dependencies (requests, urllib3, etc., selenium only if you want).
README.md — short instructions (how to set config, how to run, warning about secrets).
.gitignore — ignores tokens.txt, config local overrides, .env, and common Python artifacts.
Reply with:

confirm target repo OK,
pick A or B for tokens handling,
(optional) branch name.
Once you confirm I’ll push the files and report back with the commit details.

B
I can do that — I won’t push anything until you provide the missing secret content and confirm a couple of details.

What I need from you now

Confirm the repo target: owner = girihhas, repo = cfundtheslottikabutty — is that correct?
You chose option B (commit tokens.txt with real tokens). Paste the exact contents of tokens.txt you want committed (format: token:channel_id per line). If you prefer to upload it instead, paste or attach it here. I will commit exactly what you provide.
Branch: do you want me to commit to the repository’s default branch, or create a new branch? If a branch name, provide it now.
Do you want real config values (GUILD_ID, OWO_BOT_ID, solver API keys, INITIAL_BET, etc.) added to config.py, or should I commit a config.py.template with placeholders and leave secrets only in tokens.txt? (I recommend placeholders in config.py and putting secrets in tokens.txt.)
Security reminder

Committing real tokens/API keys to a public repo is irreversible and will expose those secrets. You confirmed B, so I will follow that — but please double-check that you understand the risk.
What I will push (once you confirm and provide tokens)

bot.py (the full script you gave me, updated with the betting/cf/slots flow)
config.py (either a filled config or a template as you choose)
tokens.txt (the exact content you paste)
tokens.txt.backup (optional: I can keep a copy under a different name if you want)
requirements.txt
README.md with usage and security notes
.gitignore (includes tokens.txt)
If that’s all correct, paste the tokens.txt contents and answer (1) repo confirm (yes/no), (2) branch name or “default”, and (3) whether to populate config.py with real values or use placeholders. Once you reply I’ll push the files and report the commit details.

i will put tokens in the file when i download it as zip and run it locally
