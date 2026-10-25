import pytest
import hashlib
from crack_core import cpu_hasher, gpu_hasher

TEST_STRINGS = [
    "",
    "a",
    "abc",
    "password",
    "123456",
    "Admin@2024!",
    "The quick brown fox jumps over the lazy dog",
    "Special_Chars_!@#$%^&*()_+{}[]:;<>?"
]


def test_cpu_md5_correctness():
    for s in TEST_STRINGS:
        expected = hashlib.md5(s.encode("utf-8")).hexdigest()
        actual = cpu_hasher.hash_single("md5", s)
        assert actual == expected


def test_cpu_sha1_correctness():
    for s in TEST_STRINGS:
        expected = hashlib.sha1(s.encode("utf-8")).hexdigest()
        actual = cpu_hasher.hash_single("sha1", s)
        assert actual == expected


def test_cpu_sha256_correctness():
    for s in TEST_STRINGS:
        expected = hashlib.sha256(s.encode("utf-8")).hexdigest()
        actual = cpu_hasher.hash_single("sha256", s)
        assert actual == expected


def test_cpu_bcrypt_verification():
    import bcrypt
    pw = "mysecretpassword"
    salt = bcrypt.gensalt(rounds=4).decode("utf-8")
    hashed = cpu_hasher.hash_single("bcrypt", pw, salt=salt)
    assert cpu_hasher.check_candidate_match("bcrypt", pw, hashed) is True
    assert cpu_hasher.check_candidate_match("bcrypt", "wrongpw", hashed) is False


def test_gpu_vs_cpu_hash_match():
    if not gpu_hasher.is_cuda_available():
        pytest.skip("CUDA GPU not available in test environment")

    for algo in ["md5", "sha1", "sha256"]:
        cpu_hashes = cpu_hasher.hash_batch(algo, TEST_STRINGS)
        gpu_hashes = gpu_hasher.hash_batch(algo, TEST_STRINGS, force_cpu=False)
        assert len(gpu_hashes) == len(cpu_hashes)
        for s, h_cpu, h_gpu in zip(TEST_STRINGS, cpu_hashes, gpu_hashes):
            assert h_gpu == h_cpu, f"Mismatch for string '{s}' on {algo}: GPU={h_gpu} vs CPU={h_cpu}"


def test_gpu_bcrypt_batch():
    if not gpu_hasher.is_cuda_available():
        pytest.skip("CUDA GPU not available in test environment")

    candidates = ["pass1", "pass2", "pass3"]
    gpu_hashes = gpu_hasher.hash_batch("bcrypt", candidates, force_cpu=False)
    assert len(gpu_hashes) == 3
    for h in gpu_hashes:
        assert h.startswith("$2b$04$"), f"Invalid bcrypt hash format: {h}"
