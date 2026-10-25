from typing import Generator, List, Set, Optional
from crack_core.strategies.base import BaseStrategy
from crack_core.wordlists import load_demo_wordlist

LEET_MAPS = [
    {"a": "@", "e": "3", "i": "1", "o": "0", "s": "$", "t": "7"},
    {"a": "4", "e": "3", "i": "!", "o": "0", "s": "5", "t": "7"},
]

COMMON_AFFIXES = ["1", "12", "123", "!", "@", "#", "2024", "2025", "2026", "99", "?"]


def apply_rules_to_word(word: str) -> Set[str]:
    """Generate rule-based mutations for a given base word."""
    results = set()
    w = word.strip()
    if not w:
        return results

    # Case variations
    results.add(w.lower())
    results.add(w.upper())
    results.add(w.capitalize())
    # Alternating case
    results.add("".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(w)))
    results.add("".join(c.lower() if i % 2 == 0 else c.upper() for i, c in enumerate(w)))

    # Reversal and duplication
    results.add(w[::-1])
    results.add(w + w)

    # Affixes (append / prepend)
    for base in [w, w.capitalize()]:
        for affix in COMMON_AFFIXES:
            results.add(f"{base}{affix}")
            results.add(f"{affix}{base}")
            results.add(f"{base}{affix}!")

    # Leet speak substitutions
    for leet in LEET_MAPS:
        mutated = w.lower()
        for k, v in leet.items():
            mutated = mutated.replace(k, v)
        results.add(mutated)
        results.add(mutated.capitalize())
        results.add(f"{mutated}1")
        results.add(f"{mutated}!")

    return results


class RulesetStrategy(BaseStrategy):
    """Ruleset attack strategy mutating words with common password composition patterns."""

    def __init__(self, base_words: Optional[List[str]] = None, batch_size: int = 5000):
        super().__init__(batch_size=batch_size)
        words = base_words if base_words is not None else load_demo_wordlist()
        self._candidates = self._precompute_candidates(words)

    def _precompute_candidates(self, words: List[str]) -> List[str]:
        candidates: Set[str] = set()
        for word in words:
            candidates.update(apply_rules_to_word(word))
        return sorted(list(candidates))

    def estimate_total(self) -> int:
        return len(self._candidates)

    def generate_batches(self) -> Generator[List[str], None, None]:
        batch = []
        for cand in self._candidates:
            batch.append(cand)
            if len(batch) >= self.batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
