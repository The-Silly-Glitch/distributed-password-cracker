from abc import ABC, abstractmethod
from typing import Generator, List


class BaseStrategy(ABC):
    """Abstract base class for password cracking candidate generation strategies."""

    def __init__(self, batch_size: int = 5000):
        self.batch_size = batch_size

    @abstractmethod
    def generate_batches(self) -> Generator[List[str], None, None]:
        """Yield candidate batches as lists of strings."""
        pass

    @abstractmethod
    def estimate_total(self) -> int:
        """Return the estimated total number of candidate passwords generated."""
        pass
