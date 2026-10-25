from typing import Generator, List, Optional
from crack_core.strategies.base import BaseStrategy
from crack_core.wordlists import load_demo_wordlist


class DictionaryStrategy(BaseStrategy):
    """Dictionary attack strategy generating candidate passwords from wordlists."""

    def __init__(self, wordlist: Optional[List[str]] = None, batch_size: int = 5000):
        super().__init__(batch_size=batch_size)
        if wordlist is not None:
            self.words = list(wordlist)
        else:
            self.words = load_demo_wordlist()

    def estimate_total(self) -> int:
        return len(self.words)

    def generate_batches(self) -> Generator[List[str], None, None]:
        batch = []
        for word in self.words:
            batch.append(word)
            if len(batch) >= self.batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
