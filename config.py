"""
Configuration file for Discord OwO Bot Betting Strategy
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# DISCORD & CHANNEL SETTINGS
# ============================================================================
GUILD_ID = os.getenv("GUILD_ID", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")  # Required! Set in .env file
OWO_BOT_ID = os.getenv("OWO_BOT_ID", "432610292342587392")  # OwO bot official ID

# Print channel ID on import (helpful for debugging)
if CHANNEL_ID:
    print(f"[CONFIG] Channel ID: {CHANNEL_ID}")
else:
    print(f"[CONFIG] WARNING: CHANNEL_ID not set! Set it in .env file")

# ============================================================================
# TOKENS & PROFILES
# ============================================================================
TOKENS_FILE = "tokens.txt"  # One token per line
PROFILES_DIR = "profiles"  # Directory to store per-account data

# ============================================================================
# BETTING STRATEGY
# ============================================================================
INITIAL_BET = 50  # Starting bet amount
BET_MULTIPLIER = 2  # Double on loss (Martingale)
ROUNDS_PER_ACCOUNT = float('inf')  # Infinite until balance = 0
STOP_ON_ZERO_BALANCE = True  # Stop when account runs out

# Game commands
GAMES = {
    "cf": "owo cf",      # Coin flip
    "slots": "owo slots"  # Slots
}

BALANCE_CHECK_COMMAND = "owo cash"  # Check balance

# ============================================================================
# CONCURRENCY & TIMING
# ============================================================================
CONCURRENCY = 5  # Number of parallel accounts
COMMAND_INTERVAL = 2  # Seconds between commands per account (human-like)
MESSAGE_WAIT_TIMEOUT = 10  # Seconds to wait for bot response
BALANCE_CHECK_DELAY = 0.5  # Seconds to wait before checking balance after bet

# ============================================================================
# CAPTCHA SETTINGS (hCaptcha)
# ============================================================================
HCAPTCHA_SITEKEY = "a6a1d5ce-612d-472d-8e37-7601408fbc09"
HCAPTCHA_PAGE_URL = "https://owobot.com/captcha"

CAPTCHA_CHECK_INTERVAL = 8  # Seconds between captcha checks
CAPTCHA_SOLVE_TIMEOUT = 120  # Max seconds to wait for captcha solve
CAPTCHA_KEYWORDS = ["captcha", "verify", "human", "bot check"]  # Detection keywords

# Captcha solver configuration
CAPTCHA_SOLVERS = {
    "capsolver": {
        "enabled": bool(os.getenv("CAPSOLVER_ENABLED", "false").lower() == "true"),
        "api_key": os.getenv("CAPSOLVER_API_KEY", "")
    },
    "nopecha": {
        "enabled": bool(os.getenv("NOPECHA_ENABLED", "false").lower() == "true"),
        "api_key": os.getenv("NOPECHA_API_KEY", "")
    },
    "2captcha": {
        "enabled": bool(os.getenv("2CAPTCHA_ENABLED", "false").lower() == "true"),
        "api_key": os.getenv("2CAPTCHA_API_KEY", "")
    }
}

CAPTCHA_SOLVER_ORDER = ["capsolver", "nopecha", "2captcha"]  # Try solvers in this order
POST_SOLVE_COOLDOWN = 12  # Seconds to wait after solving captcha

# ============================================================================
# DM POLLING (for captcha verification)
# ============================================================================
DM_POLL_TIMEOUT = 30  # Max seconds to wait for DM
DM_POLL_INTERVAL = 2  # Seconds between DM checks
DM_VERIFIED_PHRASES = [
    "i have verified that you are human",
    "you're free to go",
    "you are human",
    "verified"
]

# ============================================================================
# LOGGING & OUTPUT
# ============================================================================
LOG_FILE = "bot_activity.log"
LOG_LEVEL = "INFO"

# Color output settings
USE_COLOR_OUTPUT = True  # Enable colored terminal output

# ============================================================================
# DATA STORAGE
# ============================================================================
STATS_FILE = "bot_stats.json"  # Store account statistics
SAVE_STATS_INTERVAL = 60  # Save stats every N seconds
