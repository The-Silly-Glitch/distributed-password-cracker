import time
import logging
from typing import List, Dict, Set, Optional, Callable, Generator
from crack_core.strategies.base import BaseStrategy
from crack_core.strategies.dictionary import DictionaryStrategy
from crack_core.strategies.pattern import PatternStrategy
from crack_core.strategies.rules import RulesetStrategy
from crack_core.strategies.brute_force import BruteForceStrategy, split_keyspace
from crack_core import gpu_hasher

logger = logging.getLogger("crack_core.strategies.pipeline")


class AttackPipeline:
    """Multi-stage coordinated attack pipeline executing fast strategies first, then brute-force."""

    def __init__(
        self,
        algorithm: str,
        target_hashes: List[str],
        salt: str = "",
        batch_size: int = 5000,
        enable_brute_force: bool = True,
        brute_force_max_len: int = 4
    ):
        self.algorithm = algorithm.lower().strip()
        self.target_hashes = set(h.lower().strip() for h in target_hashes)
        self.salt = salt
        self.batch_size = batch_size
        self.enable_brute_force = enable_brute_force
        self.brute_force_max_len = brute_force_max_len
        self.recovered: Dict[str, str] = {}  # target_hash -> plaintext

    def get_stages(self) -> List[Tuple_Stage]:
        stages = [
            ("dictionary", DictionaryStrategy(batch_size=self.batch_size)),
            ("pattern", PatternStrategy(batch_size=self.batch_size)),
            ("ruleset", RulesetStrategy(batch_size=self.batch_size)),
        ]
        if self.enable_brute_force:
            stages.append((
                "brute_force",
                BruteForceStrategy(min_len=1, max_len=self.brute_force_max_len, batch_size=self.batch_size)
            ))
        return stages

    def execute(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        force_cpu: bool = False
    ) -> Dict[str, str]:
        """Execute the pipeline stages sequentially against active targets.
        
        Args:
            progress_callback: function(stage_name, evaluated_in_stage, total_in_stage)
            force_cpu: force CPU calculation
        """
        active_targets = set(self.target_hashes)

        for stage_name, strategy in self.get_stages():
            if not active_targets:
                break  # All targets cracked

            total_stage = strategy.estimate_total()
            stage_evaluated = 0

            for batch in strategy.generate_batches():
                if not active_targets:
                    break

                # Batch hash candidates
                digests = gpu_hasher.hash_batch(self.algorithm, batch, salt=self.salt, force_cpu=force_cpu)

                # Check matches
                for cand, digest in zip(batch, digests):
                    d_lower = digest.lower()
                    if d_lower in active_targets:
                        self.recovered[d_lower] = cand
                        active_targets.remove(d_lower)
                        logger.info(f"[{stage_name}] Cracked target {d_lower[:12]}... -> '{cand}'")

                stage_evaluated += len(batch)
                if progress_callback:
                    progress_callback(stage_name, stage_evaluated, total_stage)

        return self.recovered


Tuple_Stage = tuple[str, BaseStrategy]
