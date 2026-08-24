#!/usr/bin/env python3
"""
Discord OwO Bot - Multi-Token Betting Strategy

Features:
- Multi-token support with parallel account execution
- Balance-based win/loss detection (smart balance checking)
- Alternating betting strategy (CF <-> Slots)
- Martingale-style bet doubling on losses
- Color-coded statistics (Green=Win, Red=Loss, Yellow=Break-even)
- hCaptcha solving support
- Per-account statistics tracking
"""

import os
import sys
import time
import logging
import requests
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict, field
from urllib.parse import urljoin, urlparse, parse_qs
from threading import Lock

try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""

import config

# ============================================================================
# LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# COLOR UTILITIES
# ============================================================================
def colorize(text: str, color: str) -> str:
    """Apply color to text if colors are enabled"""
    if not config.USE_COLOR_OUTPUT or not HAS_COLOR:
        return text
    return f"{color}{text}{Style.RESET_ALL}"

def green(text: str) -> str:
    return colorize(text, Fore.GREEN + Style.BRIGHT)

def red(text: str) -> str:
    return colorize(text, Fore.RED + Style.BRIGHT)

def yellow(text: str) -> str:
    return colorize(text, Fore.YELLOW + Style.BRIGHT)

def cyan(text: str) -> str:
    return colorize(text, Fore.CYAN)

def magenta(text: str) -> str:
    return colorize(text, Fore.MAGENTA)

# ============================================================================
# ACCOUNT STATE & STATISTICS
# ============================================================================
@dataclass
class AccountStats:
    """Per-account statistics"""
    token: str
    user_id: Optional[str] = None
    total_wins: int = 0
    total_losses: int = 0
    total_breakeven: int = 0
    current_balance: int = 0
    initial_balance: int = 0
    total_profit: int = 0
    current_bet: int = config.INITIAL_BET
    current_game: str = "cf"  # "cf" or "slots"
    is_running: bool = True
    last_error: Optional[str] = None
    games_played: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    
    @property
    def win_rate(self) -> float:
        total = self.total_wins + self.total_losses + self.total_breakeven
        if total == 0:
            return 0.0
        return (self.total_wins / total) * 100
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['win_rate'] = self.win_rate
        return data


@dataclass
class AccountState:
    """Track per-account runtime state"""
    token: str
    user_id: Optional[str] = None
    stats: AccountStats = field(default_factory=lambda: AccountStats(token=""))
    previous_balance: int = 0
    session: Optional[requests.Session] = None
    is_paused: bool = False
    captcha_detected: bool = False


# ============================================================================
# DISCORD API WRAPPER
# ============================================================================
class DiscordAPI:
    """Simple Discord REST API wrapper"""
    
    BASE_URL = "https://discord.com/api/v9"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def __init__(self, token: str):
        self.token = token
        self.session = self._create_session()
        self.user_id = None
    
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "Authorization": self.token,
            "User-Agent": self.UA,
            "Content-Type": "application/json"
        })
        return session
    
    def send_message(self, channel_id: str, content: str) -> bool:
        """Send a message to a Discord channel"""
        try:
            url = f"{self.BASE_URL}/channels/{channel_id}/messages"
            data = {"content": content}
            resp = self.session.post(url, json=data, timeout=10)
            
            if resp.status_code == 200:
                return True
            else:
                logger.warning(f"Failed to send message: {resp.status_code} - {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def get_messages(self, channel_id: str, limit: int = 10) -> List[Dict]:
        """Fetch recent messages from a channel"""
        try:
            url = f"{self.BASE_URL}/channels/{channel_id}/messages?limit={limit}"
            resp = self.session.get(url, timeout=10)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"Failed to fetch messages: {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
    
    def get_me(self) -> Optional[str]:
        """Get current user ID"""
        try:
            url = f"{self.BASE_URL}/users/@me"
            resp = self.session.get(url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                self.user_id = data.get('id')
                return self.user_id
            else:
                logger.warning(f"Failed to get user info: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None


# ============================================================================
# BALANCE PARSER
# ============================================================================
def parse_balance(message_text: str) -> Optional[int]:
    """
    Extract balance amount from bot's response
    Expected formats:
    - "Itachi hu, you currently have 188,784 cowoncy!"
    - "you have 5000 cowoncy"
    - "5000 cowoncy"
    - "1234"
    """
    try:
        import re
        # Look for "have XXXX" or "XXXX cowoncy/coins"
        patterns = [
            r'have\s+([0-9,]+)',  # "have 188,784"
            r'([0-9,]+)\s+cowoncy',  # "188,784 cowoncy"
            r'([0-9,]+)\s+coins?',  # "1000 coin" or "1000 coins"
            r'^([0-9,]+)$',  # Just a number
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                balance = int(amount_str)
                logger.debug(f"Parsed balance: {balance} from '{message_text}'")
                return balance
    
    except Exception as e:
        logger.debug(f"Failed to parse balance from '{message_text}': {e}")
    
    return None


# ============================================================================
# MAIN BETTING BOT
# ============================================================================
class OwOBettingBot:
    def __init__(self):
        self.stats_lock = Lock()
        self.account_states: Dict[str, AccountState] = {}
        self.stats_history: Dict[str, List[Dict]] = {}
    
    def load_tokens(self) -> List[str]:
        """Load tokens from tokens.txt"""
        if not os.path.exists(config.TOKENS_FILE):
            logger.error(f"{config.TOKENS_FILE} not found!")
            return []
        
        tokens = []
        try:
            with open(config.TOKENS_FILE, 'r') as f:
                for line in f:
                    token = line.strip()
                    if token and not token.startswith('#'):
                        tokens.append(token)
        except Exception as e:
            logger.error(f"Error reading tokens: {e}")
            return []
        
        logger.info(f"Loaded {len(tokens)} token(s)")
        return tokens
    
    def initialize_account(self, token: str) -> Optional[AccountState]:
        """Initialize a new account"""
        try:
            api = DiscordAPI(token)
            user_id = api.get_me()
            
            if not user_id:
                logger.error(f"Failed to authenticate token")
                return None
            
            stats = AccountStats(
                token=token,
                user_id=user_id,
                current_balance=0,
                current_bet=config.INITIAL_BET,
                current_game="cf"
            )
            
            state = AccountState(
                token=token,
                user_id=user_id,
                stats=stats,
                session=api
            )
            
            logger.info(f"{cyan(f'[{user_id}]')} Account initialized")
            return state
        
        except Exception as e:
            logger.error(f"Failed to initialize account: {e}")
            return None
    
    def check_balance(self, state: AccountState) -> Optional[int]:
        """Check account balance using 'owo cash' command"""
        try:
            api = state.session
            
            # Send balance check command
            if not api.send_message(config.CHANNEL_ID, config.BALANCE_CHECK_COMMAND):
                return None
            
            # Wait for bot to respond
            time.sleep(config.MESSAGE_WAIT_TIMEOUT)
            messages = api.get_messages(config.CHANNEL_ID, limit=10)
            
            logger.info(f"{cyan(f'[{state.user_id}]')} Fetched {len(messages)} messages from channel")
            
            # Find response from OwO bot (most recent message)
            if not messages:
                logger.warning(f"{cyan(f'[{state.user_id}]')} No messages found in channel")
                return None
            
            logger.info(f"{cyan(f'[{state.user_id}]')} Expected OWO_BOT_ID: {config.OWO_BOT_ID}")
            
            for i, msg in enumerate(messages):
                author_id = msg.get('author', {}).get('id')
                author_name = msg.get('author', {}).get('username', 'Unknown')
                content = msg.get('content', '')
                logger.info(f"{cyan(f'[{state.user_id}]')} Message {i}: Author ID={author_id} ({author_name}), Content: {content[:80]}")
                
                # Check if this is from OwO bot
                if str(author_id) == str(config.OWO_BOT_ID):
                    logger.info(f"{cyan(f'[{state.user_id}]')} Found OwO bot message!")
                    balance = parse_balance(content)
                    if balance is not None:
                        logger.info(f"{cyan(f'[{state.user_id}]')} Successfully parsed balance: {balance}")
                        return balance
                    else:
                        logger.warning(f"{cyan(f'[{state.user_id}]')} Could not parse balance from: {content}")
            
            logger.warning(f"{cyan(f'[{state.user_id}]')} No message found from bot ID {config.OWO_BOT_ID}")
            return None
        
        except Exception as e:
            logger.error(f"{cyan(f'[{state.user_id}]')} Error checking balance: {e}", exc_info=True)
            return None
    
    def place_bet(self, state: AccountState, game: str, amount: int) -> bool:
        """Place a bet using specified game and amount"""
        try:
            api = state.session
            command = f"{config.GAMES[game]} {amount}"
            
            logger.debug(f"{cyan(f'[{state.user_id}]')} Betting: {command}")
            return api.send_message(config.CHANNEL_ID, command)
        
        except Exception as e:
            logger.error(f"{cyan(f'[{state.user_id}]')} Error placing bet: {e}")
            return False
    
    def process_bet_result(self, state: AccountState, new_balance: int) -> Tuple[str, int, str, int]:
        """
        Determine win/loss based on balance change
        Returns: (result_type, next_bet_amount, next_game, profit)
        result_type: "win", "loss", or "breakeven"
        """
        previous = state.previous_balance
        current_game = state.stats.current_game
        current_bet = state.stats.current_bet
        
        if new_balance > previous:
            # WIN: Reset bet to initial and switch to CF
            result = "win"
            next_bet = config.INITIAL_BET
            next_game = "cf"
            profit = new_balance - previous
        elif new_balance < previous:
            # LOSS: Double bet and switch game
            result = "loss"
            next_bet = current_bet * config.BET_MULTIPLIER
            next_game = "slots" if current_game == "cf" else "cf"
            profit = new_balance - previous  # Negative
        else:
            # BREAKEVEN (1x on slots): Keep bet amount but switch to CF
            result = "breakeven"
            next_bet = current_bet  # Don't reset, keep the doubled amount
            next_game = "cf"
            profit = 0
        
        return result, next_bet, next_game, profit
    
    def update_stats(self, state: AccountState, result: str, profit: int):
        """Update account statistics"""
        with self.stats_lock:
            if result == "win":
                state.stats.total_wins += 1
                color_result = green("✓ WIN")
            elif result == "loss":
                state.stats.total_losses += 1
                color_result = red("✗ LOSS")
            else:  # breakeven
                state.stats.total_breakeven += 1
                color_result = yellow("⊙ BREAK-EVEN")
            
            state.stats.total_profit += profit
            state.stats.games_played += 1
            
            logger.info(
                f"{cyan(f'[{state.user_id}]')} {color_result} | "
                f"Bet: {state.stats.current_bet} | "
                f"Balance: {state.stats.current_balance} | "
                f"Profit: {profit:+d} | "
                f"W: {green(str(state.stats.total_wins))} | "
                f"L: {red(str(state.stats.total_losses))} | "
                f"Rate: {magenta(f'{state.stats.win_rate:.1f}%')}"
            )
    
    def run_betting_cycle(self, state: AccountState) -> bool:
        """
        Execute one complete betting cycle:
        1. Place bet
        2. Wait for result
        3. Check balance
        4. Update stats
        5. Prepare next bet
        
        Returns True if should continue, False if should stop
        """
        try:
            # Place bet
            game = state.stats.current_game
            bet = state.stats.current_bet
            
            if not self.place_bet(state, game, bet):
                logger.error(f"{cyan(f'[{state.user_id}]')} Failed to place bet")
                return True  # Continue trying
            
            # Wait for bot to process
            time.sleep(config.MESSAGE_WAIT_TIMEOUT)
            
            # Check new balance
            new_balance = self.check_balance(state)
            if new_balance is None:
                logger.warning(f"{cyan(f'[{state.user_id}]')} Could not verify balance, skipping")
                return True
            
            # Process result
            result, next_bet, next_game, profit = self.process_bet_result(state, new_balance)
            
            # Update stats
            state.stats.current_balance = new_balance
            state.stats.total_profit += profit
            self.update_stats(state, result, profit)
            
            # Prepare next bet
            state.stats.current_bet = next_bet
            state.stats.current_game = next_game
            state.previous_balance = new_balance
            
            # Check stop condition
            if config.STOP_ON_ZERO_BALANCE and new_balance <= 0:
                logger.info(f"{cyan(f'[{state.user_id}]')} {red('BALANCE REACHED ZERO - STOPPING')}") 
                state.stats.is_running = False
                return False
            
            # Human-like delay before next bet
            time.sleep(config.COMMAND_INTERVAL + (0 if config.COMMAND_INTERVAL > 0 else 1))
            return True
        
        except Exception as e:
            logger.error(f"{cyan(f'[{state.user_id}]')} Error in betting cycle: {e}")
            state.stats.last_error = str(e)
            return True  # Continue
    
    def run_account(self, token: str):
        """
        Main loop for a single account
        """
        # Initialize
        state = self.initialize_account(token)
        if not state:
            return
        
        self.account_states[token] = state
        
        # Check initial balance
        initial_balance = self.check_balance(state)
        if initial_balance is None:
            logger.error(f"{cyan(f'[{state.user_id}]')} Could not get initial balance")
            return
        
        state.stats.current_balance = initial_balance
        state.stats.initial_balance = initial_balance
        state.previous_balance = initial_balance
        
        logger.info(
            f"{cyan(f'[{state.user_id}]')} Starting with balance: "
            f"{magenta(str(initial_balance))} | "
            f"Initial bet: {config.INITIAL_BET}"
        )
        
        # Betting loop
        while state.stats.is_running:
            if not self.run_betting_cycle(state):
                break
        
        # Print final stats
        self.print_account_stats(state)
    
    def print_account_stats(self, state: AccountState):
        """Print final statistics for an account"""
        stats = state.stats
        duration = datetime.now() - stats.start_time
        
        print(
            f"\n{'='*70}\n"
            f"{cyan(f'Account: {state.user_id}')}\n"
            f"{'='*70}\n"
            f"  Wins:          {green(str(stats.total_wins))}\n"
            f"  Losses:        {red(str(stats.total_losses))}\n"
            f"  Break-evens:   {yellow(str(stats.total_breakeven))}\n"
            f"  Win Rate:      {magenta(f'{stats.win_rate:.2f}%')}\n"
            f"  Games Played:  {stats.games_played}\n"
            f"  Initial Bal:   {stats.initial_balance}\n"
            f"  Final Bal:     {stats.current_balance}\n"
            f"  Total Profit:  {green(str(stats.total_profit)) if stats.total_profit > 0 else red(str(stats.total_profit))}\n"
            f"  Duration:      {duration}\n"
            f"{'='*70}\n"
        )
    
    def run(self):
        """Main entry point"""
        tokens = self.load_tokens()
        if not tokens:
            logger.error("No tokens to run!")
            return
        
        # Validate config
        if not config.CHANNEL_ID:
            logger.error("CHANNEL_ID not set in config!")
            return
        
        logger.info(f"\n{cyan('='*70)}")
        logger.info(f"{cyan('Discord OwO Bot - Multi-Token Betting Strategy')}")
        logger.info(f"{cyan(f'Starting {len(tokens)} account(s)...')}")
        logger.info(f"{cyan('='*70)}\n")
        
        # Run all accounts in parallel
        with ThreadPoolExecutor(max_workers=config.CONCURRENCY) as executor:
            futures = {
                executor.submit(self.run_account, token): token 
                for token in tokens
            }
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Account thread error: {e}")
        
        logger.info(f"\n{cyan('All accounts finished!')}")
        self.print_summary()
    
    def print_summary(self):
        """Print summary for all accounts"""
        print(f"\n{cyan('='*70)}")
        print(f"{cyan('FINAL SUMMARY')}")
        print(f"{cyan('='*70)}\n")
        
        total_wins = 0
        total_losses = 0
        total_profit = 0
        
        for state in self.account_states.values():
            stats = state.stats
            total_wins += stats.total_wins
            total_losses += stats.total_losses
            total_profit += stats.total_profit
            
            status = green("✓") if stats.total_profit > 0 else red("✗")
            print(
                f"  {status} {cyan(stats.user_id)}: "
                f"W={green(stats.total_wins)} L={red(stats.total_losses)} "
                f"Profit={magenta(f'{stats.total_profit:+d}')}"
            )
        
        total_games = total_wins + total_losses
        overall_rate = (total_wins / total_games * 100) if total_games > 0 else 0
        
        print(
            f"\n  {cyan('Overall')}:\n"
            f"    Total Wins:   {green(str(total_wins))}\n"
            f"    Total Losses: {red(str(total_losses))}\n"
            f"    Win Rate:     {magenta(f'{overall_rate:.2f}%')}\n"
            f"    Total Profit: {green(str(total_profit)) if total_profit > 0 else red(str(total_profit))}\n"
        )
        print(f"{cyan('='*70)}\n")


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    try:
        bot = OwOBettingBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("\nBot interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
