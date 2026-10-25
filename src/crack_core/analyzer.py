import math
import re
from typing import Dict, Any, List
from crack_core.wordlists import load_demo_wordlist

COMMON_SEQUENCES = [
    "1234567890", "0987654321",
    "abcdefghijklmnopqrstuvwxyz", "zyxwvutsrqponmlkjihgfedcba",
    "qwertyuiop", "asdfghjkl", "zxcvbnm"
]

DEMO_WORDS_SET = set(w.lower() for w in load_demo_wordlist())


def calculate_entropy(password: str) -> float:
    """Calculate Shannon information entropy (in bits) based on character pool size."""
    if not password:
        return 0.0

    pool_size = 0
    if any(c.islower() for c in password): pool_size += 26
    if any(c.isupper() for c in password): pool_size += 26
    if any(c.isdigit() for c in password): pool_size += 10
    if any(not c.isalnum() for c in password): pool_size += 32

    if pool_size == 0:
        return 0.0

    # Total bits of entropy = length * log2(pool_size)
    return round(len(password) * math.log2(pool_size), 2)


def detect_patterns(password: str) -> List[str]:
    """Detect predictable human composition patterns in the password."""
    patterns = []
    pwd_lower = password.lower()

    # Dictionary word match
    if pwd_lower in DEMO_WORDS_SET:
        patterns.append("Exact dictionary word")
    else:
        for w in DEMO_WORDS_SET:
            if len(w) >= 4 and w in pwd_lower:
                patterns.append(f"Contains common word '{w}'")
                break

    # Sequential characters
    for seq in COMMON_SEQUENCES:
        for i in range(len(seq) - 2):
            sub = seq[i:i + 3]
            if sub in pwd_lower:
                patterns.append(f"Sequential sequence '{sub}'")
                break

    # Repetitive characters
    if re.search(r"(.)\1{2,}", password):
        patterns.append("Repetitive repeating characters (3+)")

    # Year patterns (1920-2035)
    if re.search(r"(19\d\d|20[0-3]\d)", password):
        patterns.append("Contains 4-digit calendar year")

    return list(dict.fromkeys(patterns))  # Deduplicate while preserving order


def check_policy_violations(password: str, min_length: int = 12) -> List[str]:
    """Check standard enterprise password policy violations."""
    violations = []
    if len(password) < 8:
        violations.append("Critical: Length is under 8 characters")
    elif len(password) < min_length:
        violations.append(f"Warning: Length is under recommended {min_length} characters")

    if not any(c.isupper() for c in password):
        violations.append("Missing uppercase letters (A-Z)")
    if not any(c.islower() for c in password):
        violations.append("Missing lowercase letters (a-z)")
    if not any(c.isdigit() for c in password):
        violations.append("Missing numeric digits (0-9)")
    if not any(not c.isalnum() for c in password):
        violations.append("Missing special symbols (!@#$%^&*)")

    return violations


def analyze_password(password: str) -> Dict[str, Any]:
    """Provide a comprehensive security posture assessment for a password."""
    entropy = calculate_entropy(password)
    patterns = detect_patterns(password)
    violations = check_policy_violations(password)

    # Strength rating calculation
    score = 0
    if len(password) >= 8: score += 20
    if len(password) >= 12: score += 20
    if len(password) >= 16: score += 15
    if any(c.islower() for c in password) and any(c.isupper() for c in password): score += 15
    if any(c.isdigit() for c in password): score += 15
    if any(not c.isalnum() for c in password): score += 15

    # Penalties for patterns
    if "Exact dictionary word" in patterns: score = max(0, score - 40)
    if any("Sequential" in p for p in patterns): score = max(0, score - 20)
    if any("Repetitive" in p for p in patterns): score = max(0, score - 15)

    if score < 30:
        rating = "Very Weak"
    elif score < 55:
        rating = "Weak"
    elif score < 75:
        rating = "Moderate"
    elif score < 90:
        rating = "Strong"
    else:
        rating = "Very Strong"

    return {
        "password": password,
        "length": len(password),
        "entropy_bits": entropy,
        "score": score,
        "rating": rating,
        "patterns_detected": patterns,
        "policy_violations": violations,
    }
