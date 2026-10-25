import pytest
from crack_core.strategies.brute_force import (
    calculate_keyspace_size,
    index_to_candidate,
    split_keyspace,
    BruteForceStrategy
)


def test_keyspace_size_calculation():
    charset = "abc"  # len 3
    # min_len 1, max_len 2 -> 3^1 + 3^2 = 3 + 9 = 12
    total = calculate_keyspace_size(charset, 1, 2)
    assert total == 12


def test_index_to_candidate_bijection():
    charset = "ab"
    # min_len=1, max_len=2 -> keyspace:
    # 0: "a", 1: "b", 2: "aa", 3: "ab", 4: "ba", 5: "bb"
    expected = ["a", "b", "aa", "ab", "ba", "bb"]
    actual = [index_to_candidate(i, charset, 1, 2) for i in range(6)]
    assert actual == expected


def test_split_keyspace_no_overlap_and_full_coverage():
    charset = "abcdef0123"
    min_len = 1
    max_len = 3
    total = calculate_keyspace_size(charset, min_len, max_len)

    for num_chunks in [1, 2, 4, 7]:
        chunks = split_keyspace(charset, min_len, max_len, num_chunks)
        assert len(chunks) == num_chunks

        # Check contiguous non-overlapping coverage
        covered = 0
        expected_start = 0
        for c in chunks:
            assert c["start_idx"] == expected_start
            assert c["end_idx"] > c["start_idx"]
            covered += c["total"]
            expected_start = c["end_idx"]

        assert expected_start == total
        assert covered == total


def test_hashrate_weighted_split():
    charset = "0123456789"
    min_len = 2
    max_len = 2  # Total = 100
    # Weights 1 to 3 -> 25% and 75%
    chunks = split_keyspace(charset, min_len, max_len, 2, weights=[25.0, 75.0])
    assert len(chunks) == 2
    assert chunks[0]["total"] == 25
    assert chunks[1]["total"] == 75
    assert chunks[0]["start_idx"] == 0
    assert chunks[0]["end_idx"] == 25
    assert chunks[1]["start_idx"] == 25
    assert chunks[1]["end_idx"] == 100
