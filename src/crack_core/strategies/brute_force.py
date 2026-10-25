import string
from typing import Generator, List, Optional, Tuple, Dict, Any
from crack_core.strategies.base import BaseStrategy

DEFAULT_CHARSET = string.ascii_lowercase + string.digits


def index_to_candidate(idx: int, charset: str, min_len: int, max_len: int) -> str:
    """Bijectively map a discrete integer index to a string in the search space."""
    b = len(charset)
    current_idx = idx

    for length in range(min_len, max_len + 1):
        count_at_len = b ** length
        if current_idx < count_at_len:
            # Belongs to this length
            chars = []
            rem = current_idx
            for _ in range(length):
                chars.append(charset[rem % b])
                rem //= b
            return "".join(reversed(chars))
        current_idx -= count_at_len

    raise IndexError(f"Index {idx} out of range for min_len={min_len}, max_len={max_len}")


def calculate_keyspace_size(charset: str, min_len: int, max_len: int) -> int:
    """Calculate total candidate count across lengths."""
    b = len(charset)
    return sum(b ** length for length in range(min_len, max_len + 1))


def split_keyspace(
    charset: str,
    min_len: int,
    max_len: int,
    num_chunks: int,
    weights: Optional[List[float]] = None
) -> List[Dict[str, Any]]:
    """Split brute-force search space into discrete non-overlapping sub-ranges.
    
    Prevents duplicate work across distributed workers while supporting
    hashrate-weighted assignment.
    """
    total = calculate_keyspace_size(charset, min_len, max_len)
    if num_chunks <= 0:
        return []
    if num_chunks == 1 or total <= num_chunks:
        return [{
            "chunk_idx": 0,
            "start_idx": 0,
            "end_idx": total,
            "total": total,
            "charset": charset,
            "min_len": min_len,
            "max_len": max_len,
            "start_sample": index_to_candidate(0, charset, min_len, max_len) if total > 0 else "",
            "end_sample": index_to_candidate(total - 1, charset, min_len, max_len) if total > 0 else ""
        }]

    if weights is None or len(weights) != num_chunks:
        weights = [1.0] * num_chunks

    total_weight = sum(weights)
    if total_weight <= 0:
        weights = [1.0] * num_chunks
        total_weight = float(num_chunks)

    chunks = []
    current_start = 0

    for i in range(num_chunks):
        if i == num_chunks - 1:
            chunk_end = total
        else:
            proportion = weights[i] / total_weight
            chunk_size = int(round(total * proportion))
            chunk_end = min(current_start + chunk_size, total)

        if current_start < chunk_end:
            chunks.append({
                "chunk_idx": i,
                "start_idx": current_start,
                "end_idx": chunk_end,
                "total": chunk_end - current_start,
                "charset": charset,
                "min_len": min_len,
                "max_len": max_len,
                "start_sample": index_to_candidate(current_start, charset, min_len, max_len),
                "end_sample": index_to_candidate(chunk_end - 1, charset, min_len, max_len)
            })
            current_start = chunk_end

    return chunks


class BruteForceStrategy(BaseStrategy):
    """Sub-range brute-force strategy generating candidates for a specific slice."""

    def __init__(
        self,
        charset: str = DEFAULT_CHARSET,
        min_len: int = 1,
        max_len: int = 4,
        start_idx: int = 0,
        end_idx: Optional[int] = None,
        batch_size: int = 5000
    ):
        super().__init__(batch_size=batch_size)
        self.charset = charset
        self.min_len = min_len
        self.max_len = max_len
        self.total_keyspace = calculate_keyspace_size(charset, min_len, max_len)
        self.start_idx = max(0, start_idx)
        self.end_idx = min(self.total_keyspace, end_idx if end_idx is not None else self.total_keyspace)

    def estimate_total(self) -> int:
        return max(0, self.end_idx - self.start_idx)

    def generate_batches(self) -> Generator[List[str], None, None]:
        batch = []
        for idx in range(self.start_idx, self.end_idx):
            batch.append(index_to_candidate(idx, self.charset, self.min_len, self.max_len))
            if len(batch) >= self.batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
