import time
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from crack_core.models import Job, Worker, RecoveredPassword
from crack_core.db import get_session, init_db
from crack_core.queue import CrackQueue
from crack_core.strategies.brute_force import split_keyspace, DEFAULT_CHARSET

logger = logging.getLogger("crack_core.coordinator")


class Coordinator:
    """Central coordinator managing job submission, range splitting, dynamic assignment, and worker health."""

    def __init__(self, queue: Optional[CrackQueue] = None):
        self.queue = queue or CrackQueue()
        init_db()

    def submit_job(
        self,
        name: str,
        algorithm: str,
        target_hashes: List[str],
        attack_type: str = "hybrid",
        priority: int = 5,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Submit a new cracking job, create DB record, and partition keyspace into chunks."""
        job_id = str(uuid.uuid4())[:8]
        params = parameters or {}
        cleaned_targets = [h.strip() for h in target_hashes if h.strip()]

        job_dict = {
            "id": job_id,
            "name": name,
            "algorithm": algorithm.lower().strip(),
            "attack_type": attack_type.lower().strip(),
            "target_hashes": cleaned_targets,
            "priority": int(priority),
            "status": "queued",
            "total_candidates": 0,
            "evaluated_candidates": 0,
            "parameters": params,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Save to DB
        with get_session() as session:
            db_job = Job(
                id=job_id,
                name=name,
                algorithm=job_dict["algorithm"],
                attack_type=job_dict["attack_type"],
                target_hashes=cleaned_targets,
                priority=job_dict["priority"],
                status="queued",
                parameters=params,
                created_at=datetime.now(timezone.utc)
            )
            session.add(db_job)

        # Generate sub-range chunks based on registered workers
        chunks = self._generate_chunks_for_job(job_id, job_dict)
        total_cand = sum(c.get("total", 0) for c in chunks)
        job_dict["total_candidates"] = total_cand

        with get_session() as session:
            db_job = session.query(Job).filter(Job.id == job_id).first()
            if db_job:
                db_job.total_candidates = total_cand

        # Push to Queue
        self.queue.push_job(job_dict)
        self.queue.push_chunks(job_id, chunks)

        logger.info(f"Submitted Job '{name}' (ID: {job_id}) with {len(chunks)} chunks, priority {priority}")
        return job_id

    def _generate_chunks_for_job(self, job_id: str, job_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        attack_type = job_dict["attack_type"]
        params = job_dict.get("parameters", {})
        active_workers = [w for w in self.queue.get_workers() if w.get("status") != "offline"]

        # Number of chunks: scale by active worker count or default to 4 chunks per job
        worker_count = max(1, len(active_workers))
        num_chunks = worker_count * 2

        # Extract worker hashrate weights if available
        weights = [max(1.0, float(w.get("hashrate", 1.0))) for w in active_workers] if active_workers else None
        if weights and len(weights) < num_chunks:
            weights = weights * (num_chunks // len(weights) + 1)
            weights = weights[:num_chunks]

        chunks = []

        if attack_type in ["brute_force", "hybrid"]:
            charset = params.get("charset", DEFAULT_CHARSET)
            min_len = int(params.get("min_len", 1))
            max_len = int(params.get("max_len", 3))

            raw_chunks = split_keyspace(charset, min_len, max_len, num_chunks, weights=weights)
            for rc in raw_chunks:
                rc["job_id"] = job_id
                rc["type"] = "brute_force"
                rc["algorithm"] = job_dict["algorithm"]
                rc["target_hashes"] = job_dict["target_hashes"]
                rc["salt"] = params.get("salt", "")
                chunks.append(rc)

        if attack_type in ["dictionary", "hybrid"]:
            chunks.append({
                "job_id": job_id,
                "type": "dictionary",
                "chunk_idx": 0,
                "algorithm": job_dict["algorithm"],
                "target_hashes": job_dict["target_hashes"],
                "salt": params.get("salt", ""),
                "total": 100
            })

        if attack_type in ["pattern", "hybrid"]:
            chunks.append({
                "job_id": job_id,
                "type": "pattern",
                "chunk_idx": 0,
                "algorithm": job_dict["algorithm"],
                "target_hashes": job_dict["target_hashes"],
                "salt": params.get("salt", ""),
                "total": 500
            })

        if attack_type in ["ruleset", "hybrid"]:
            chunks.append({
                "job_id": job_id,
                "type": "ruleset",
                "chunk_idx": 0,
                "algorithm": job_dict["algorithm"],
                "target_hashes": job_dict["target_hashes"],
                "salt": params.get("salt", ""),
                "total": 2000
            })

        return chunks

    def check_worker_health(self, timeout_seconds: float = 15.0) -> List[str]:
        """Detect stale worker heartbeats, mark them offline, and requeue any lost in-flight work."""
        dead_workers = []
        now = time.time()
        workers = self.queue.get_workers()

        for w in workers:
            w_id = w["id"]
            last_hb = float(w.get("last_heartbeat", 0))
            if now - last_hb > timeout_seconds:
                if w.get("status") != "offline":
                    w["status"] = "offline"
                    self.queue.update_worker_status(w_id, "offline")
                    dead_workers.append(w_id)
                    logger.warning(f"Worker {w_id} is unresponsive (last seen {int(now - last_hb)}s ago). Marking offline.")

                    # Update in DB
                    with get_session() as session:
                        db_w = session.query(Worker).filter(Worker.id == w_id).first()
                        if db_w:
                            db_w.status = "offline"

                    # Requeue any chunk assigned to this dead worker
                    requeued = self.queue.requeue_active_chunk(w_id)
                    if requeued:
                        logger.info(f"Successfully recovered and requeued chunk from dead worker {w_id}")

        return dead_workers

    def record_crack_result(
        self,
        job_id: str,
        worker_id: str,
        hash_val: str,
        algorithm: str,
        plaintext: str,
        elapsed_seconds: float = 0.0
    ):
        """Record cracked credential in DB, queue, and check if job is finished."""
        with get_session() as session:
            rec = RecoveredPassword(
                job_id=job_id,
                worker_id=worker_id,
                hash_val=hash_val,
                algorithm=algorithm,
                plaintext=plaintext,
                cracked_at=datetime.now(timezone.utc),
                time_taken_seconds=elapsed_seconds
            )
            session.add(rec)

        res_dict = {
            "job_id": job_id,
            "worker_id": worker_id,
            "hash_val": hash_val,
            "algorithm": algorithm,
            "plaintext": plaintext,
            "time_taken_seconds": elapsed_seconds,
            "cracked_at": datetime.now(timezone.utc).isoformat()
        }
        self.queue.record_found(job_id, res_dict)
        logger.info(f"Recorded cracked hash {hash_val[:12]}... -> '{plaintext}' for Job {job_id}")

        # Check completion
        job = self.queue.get_job(job_id)
        if job:
            found_count = len(self.queue.get_found(job_id))
            target_count = len(job.get("target_hashes", []))
            if found_count >= target_count and target_count > 0:
                self.queue.update_job_status(job_id, "completed")
                with get_session() as session:
                    db_job = session.query(Job).filter(Job.id == job_id).first()
                    if db_job:
                        db_job.status = "completed"
                        db_job.completed_at = datetime.now(timezone.utc)
                logger.info(f"Job {job_id} fully completed ({found_count}/{target_count} cracked).")
