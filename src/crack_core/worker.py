import time
import uuid
import socket
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from crack_core import gpu_hasher, cpu_hasher
from crack_core.queue import CrackQueue
from crack_core.models import Worker as WorkerModel
from crack_core.db import get_session
from crack_core.strategies.brute_force import BruteForceStrategy
from crack_core.strategies.dictionary import DictionaryStrategy
from crack_core.strategies.pattern import PatternStrategy
from crack_core.strategies.rules import RulesetStrategy

logger = logging.getLogger("crack_core.worker")


class CrackWorker:
    """Worker daemon executing candidate generation and GPU-accelerated hashing for assigned chunks."""

    def __init__(
        self,
        worker_id: Optional[str] = None,
        queue: Optional[CrackQueue] = None,
        force_cpu: bool = False
    ):
        self.worker_id = worker_id or f"worker-{socket.gethostname()}-{str(uuid.uuid4())[:6]}"
        self.queue = queue or CrackQueue()
        self.force_cpu = force_cpu
        self.gpu_info = gpu_hasher.get_gpu_info()
        self.hashrate = 0.0
        self.is_running = False
        self.current_job_id = None
        self.current_range = None

        self._register()

    def _register(self):
        """Register worker hardware and capabilities in Redis and DB."""
        gpu_name = self.gpu_info["device_name"] if not self.force_cpu else "CPU (Forced)"
        dev_count = self.gpu_info["device_count"] if not self.force_cpu else 0

        # Benchmark initial baseline hashrate
        t0 = time.time()
        test_cands = [f"bench_cand_{i}" for i in range(1000)]
        gpu_hasher.hash_batch("md5", test_cands, force_cpu=self.force_cpu)
        elapsed = max(0.0001, time.time() - t0)
        self.hashrate = round(len(test_cands) / elapsed, 1)

        worker_dict = {
            "id": self.worker_id,
            "name": f"Worker-{self.worker_id[:12]}",
            "gpu_name": gpu_name,
            "device_count": dev_count,
            "hashrate": self.hashrate,
            "status": "idle",
            "current_job_id": None,
            "current_range": None,
            "temperature_c": self.gpu_info.get("temperature_c"),
            "registered_at": datetime.now(timezone.utc).isoformat()
        }

        self.queue.register_worker(worker_dict)

        with get_session() as session:
            db_w = session.query(WorkerModel).filter(WorkerModel.id == self.worker_id).first()
            if not db_w:
                db_w = WorkerModel(
                    id=self.worker_id,
                    name=worker_dict["name"],
                    gpu_name=gpu_name,
                    device_count=dev_count,
                    hashrate=self.hashrate,
                    status="idle",
                    registered_at=datetime.now(timezone.utc)
                )
                session.add(db_w)
            else:
                db_w.status = "idle"
                db_w.hashrate = self.hashrate
                db_w.last_heartbeat = datetime.now(timezone.utc)

        logger.info(f"Registered Worker '{self.worker_id}' ({gpu_name}) @ ~{self.hashrate:,.0f} H/s")

    def heartbeat(self):
        """Send alive signal with latest GPU telemetry."""
        telemetry = gpu_hasher.get_gpu_info()
        stats = {
            "hashrate": self.hashrate,
            "temperature_c": telemetry.get("temperature_c"),
            "status": "busy" if self.current_job_id else "idle",
            "current_job_id": self.current_job_id,
            "current_range": self.current_range
        }
        self.queue.heartbeat(self.worker_id, stats)

    def process_one_chunk(self, job_id: str) -> Optional[int]:
        """Fetch and execute a single work chunk for the specified job. Returns count of evaluated candidates."""
        chunk = self.queue.pop_chunk(job_id, self.worker_id)
        if not chunk:
            return None

        self.current_job_id = job_id
        chunk_type = chunk.get("type", "brute_force")
        targets = set(h.lower().strip() for h in chunk.get("target_hashes", []))
        algorithm = chunk.get("algorithm", "md5").lower()
        salt = chunk.get("salt", "")

        if chunk_type == "brute_force":
            strategy = BruteForceStrategy(
                charset=chunk.get("charset"),
                min_len=chunk.get("min_len", 1),
                max_len=chunk.get("max_len", 3),
                start_idx=chunk.get("start_idx", 0),
                end_idx=chunk.get("end_idx"),
                batch_size=5000
            )
            self.current_range = f"{chunk.get('start_sample', '')} -> {chunk.get('end_sample', '')}"
        elif chunk_type == "dictionary":
            strategy = DictionaryStrategy(batch_size=5000)
            self.current_range = "demo_wordlist"
        elif chunk_type == "pattern":
            strategy = PatternStrategy(batch_size=5000)
            self.current_range = "templates"
        elif chunk_type == "ruleset":
            strategy = RulesetStrategy(batch_size=5000)
            self.current_range = "mutations"
        else:
            strategy = DictionaryStrategy(batch_size=5000)
            self.current_range = chunk_type

        self.heartbeat()

        t_start = time.time()
        evaluated_in_chunk = 0

        for batch in strategy.generate_batches():
            # Hash candidates using GPU
            t0 = time.time()
            digests = gpu_hasher.hash_batch(algorithm, batch, salt=salt, force_cpu=self.force_cpu)
            t_eval = max(0.0001, time.time() - t0)

            # Update hashrate moving average
            current_speed = len(batch) / t_eval
            self.hashrate = round(self.hashrate * 0.7 + current_speed * 0.3, 1)

            # Check matches
            for cand, digest in zip(batch, digests):
                d_lower = digest.lower()
                if d_lower in targets:
                    elapsed = round(time.time() - t_start, 3)
                    self._record_found(job_id, d_lower, algorithm, cand, elapsed)

            evaluated_in_chunk += len(batch)
            self.queue.record_progress(job_id, len(batch))
            self.heartbeat()

        self.queue.complete_chunk(self.worker_id)
        self.current_job_id = None
        self.current_range = None
        self.heartbeat()

        return evaluated_in_chunk

    def _record_found(self, job_id: str, hash_val: str, algo: str, plaintext: str, elapsed: float):
        found_dict = {
            "job_id": job_id,
            "worker_id": self.worker_id,
            "hash_val": hash_val,
            "algorithm": algo,
            "plaintext": plaintext,
            "time_taken_seconds": elapsed,
            "cracked_at": datetime.now(timezone.utc).isoformat()
        }
        self.queue.record_found(job_id, found_dict)

        with get_session() as session:
            from crack_core.models import RecoveredPassword
            rec = RecoveredPassword(
                job_id=job_id,
                worker_id=self.worker_id,
                hash_val=hash_val,
                algorithm=algo,
                plaintext=plaintext,
                cracked_at=datetime.now(timezone.utc),
                time_taken_seconds=elapsed
            )
            session.add(rec)

        logger.info(f"Worker {self.worker_id} CRACKED: {hash_val[:12]}... -> '{plaintext}'")
