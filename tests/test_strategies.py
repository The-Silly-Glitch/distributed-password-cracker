import hashlib
from crack_core.strategies.dictionary import DictionaryStrategy
from crack_core.strategies.brute_force import BruteForceStrategy
from crack_core.strategies.pattern import PatternStrategy
from crack_core.strategies.rules import RulesetStrategy, apply_rules_to_word
from crack_core.strategies.pipeline import AttackPipeline


def test_dictionary_strategy():
    words = ["apple", "banana", "cherry"]
    strat = DictionaryStrategy(wordlist=words, batch_size=2)
    assert strat.estimate_total() == 3
    batches = list(strat.generate_batches())
    assert len(batches) == 2
    assert batches[0] == ["apple", "banana"]
    assert batches[1] == ["cherry"]


def test_brute_force_strategy():
    strat = BruteForceStrategy(charset="abc", min_len=1, max_len=2, batch_size=5)
    assert strat.estimate_total() == 12
    batches = list(strat.generate_batches())
    all_cands = [c for b in batches for c in b]
    assert len(all_cands) == 12
    assert "a" in all_cands
    assert "bb" in all_cands


def test_pattern_strategy():
    strat = PatternStrategy(custom_words=["Demo"])
    assert strat.estimate_total() > 50
    batches = list(strat.generate_batches())
    all_cands = [c for b in batches for c in b]
    assert "Spring2024" in all_cands
    assert "Winter2025!" in all_cands


def test_ruleset_strategy():
    mutations = apply_rules_to_word("password")
    assert "Password" in mutations
    assert "PASSWORD" in mutations
    assert "p@$$w0rd" in mutations or "p4$$w0rd" in mutations
    assert "password123" in mutations
    assert "drowssap" in mutations


def test_pipeline_attack_dictionary():
    target_pwd = "dragon"
    target_hash = hashlib.md5(target_pwd.encode("utf-8")).hexdigest()

    pipeline = AttackPipeline(
        algorithm="md5",
        target_hashes=[target_hash],
        enable_brute_force=False
    )
    recovered = pipeline.execute(force_cpu=True)
    assert target_hash in recovered
    assert recovered[target_hash] == target_pwd


def test_pipeline_attack_brute_force():
    target_pwd = "ab"
    target_hash = hashlib.md5(target_pwd.encode("utf-8")).hexdigest()

    pipeline = AttackPipeline(
        algorithm="md5",
        target_hashes=[target_hash],
        enable_brute_force=True,
        brute_force_max_len=2
    )
    recovered = pipeline.execute(force_cpu=True)
    assert target_hash in recovered
    assert recovered[target_hash] == target_pwd
