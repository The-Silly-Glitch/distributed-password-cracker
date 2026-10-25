import os
from typing import List

_WORDLIST_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_WORDLIST_PATH = os.path.join(_WORDLIST_DIR, "top100.txt")


def load_demo_wordlist() -> List[str]:
    """Load the bundled demo wordlist (top 100 common passwords).
    
    Notice: Real-world password audits often utilize larger dictionaries such as
    SecLists (https://github.com/danielmiessler/SecLists) or RockYou, which must only
    be sourced and used in compliance with organizational policies and applicable laws.
    """
    if not os.path.exists(DEMO_WORDLIST_PATH):
        return []
    with open(DEMO_WORDLIST_PATH, "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]
