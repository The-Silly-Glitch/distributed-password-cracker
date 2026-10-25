from typing import Generator, List, Optional
from crack_core.strategies.base import BaseStrategy

SEASONS = ["Spring", "Summer", "Autumn", "Fall", "Winter"]
YEARS = [str(y) for y in range(2018, 2028)]
COMMON_SYMBOLS = ["!", "@", "#", "$", "?", "123", "1"]
BASE_NAMES = ["Admin", "User", "Root", "Test", "Manager", "Guest", "Password", "Secure"]


class PatternStrategy(BaseStrategy):
    """Pattern / mask attack strategy producing candidates based on behavioral templates."""

    def __init__(self, custom_words: Optional[List[str]] = None, batch_size: int = 5000):
        super().__init__(batch_size=batch_size)
        self.custom_words = custom_words or []
        self._candidates = self._precompute_patterns()

    def _precompute_patterns(self) -> List[str]:
        candidates = set()

        # Season + Year (+ Symbol) templates: e.g. Spring2024, Winter2025!
        for season in SEASONS:
            for year in YEARS:
                candidates.add(f"{season}{year}")
                candidates.add(f"{season.lower()}{year}")
                candidates.add(f"{season}{year}!")
                candidates.add(f"{season}{year}@")
                candidates.add(f"{season}{year}#")
                candidates.add(f"{season}@{year}")

        # Name / Word + Number templates: e.g. Admin123, Password2024, root1
        bases = BASE_NAMES + self.custom_words
        num_suffixes = ["1", "12", "123", "1234", "01", "2024", "2025", "2026", "007", "777", "99"]
        for base in bases:
            for num in num_suffixes:
                candidates.add(f"{base}{num}")
                candidates.add(f"{base.lower()}{num}")
                candidates.add(f"{base.capitalize()}{num}!")
                candidates.add(f"{base}@{num}")
                candidates.add(f"{num}{base}")

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
