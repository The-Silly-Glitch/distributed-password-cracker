import os
import time
import json
import logging
from typing import List, Dict, Any, Optional
import redis

logger = logging.getLogger("crack_core.queue")

DEFAULT_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class CrackQueue:
    def __init__(self, redis_url: str = DEFAULT_REDIS_URL):
        self.redis_url = redis_url
        try:
            self.client = redis.Redis.from_url(redis_url, decode_responses=True)
            self.client.ping()
            self.is_connected = True
        except Exception as e:
            logger.warning(f"Could not connect to Redis at {redis_url}: {e}. Memory queue will be used.")
            self.client = None
            self.is_connected = False
            self._mem_jobs: Dict[str, Dict[str, Any]] = {}
            self._mem_queue: List[str] = []
            self._mem_chunks: Dict[str, List[Dict[str, Any]]] = {}
            self._mem_workers: Dict[str, Dict[str, Any]] = {}
            self._mem_active_work: Dict[str, Dict[str, Any]] = {}
            self._mem_found: Dict[str, List[Dict[str, Any]]] = {}

    # --- Priority Job Management ---

    def push_job(self, job_dict: Dict[str, Any]) -> str:
        job_id = job_dict["id"]
        priority = job_dict.get("priority", 5)
        payload = json.dumps(job_dict)

        if self.is_connected:
            self.client.hset("crack:jobs:data", job_id, payload)
            # Store job in sorted set by priority score (higher score = popped first)
            self.client.zadd("crack:jobs:priority", {job_id: float(priority)})
            self.publish_event("job_submitted", job_dict)
        else:
            self._mem_jobs[job_id] = job_dict
            self._mem_queue.append(job_id)
            self._mem_queue.sort(key=lambda jid: self._mem_jobs[jid].get("priority", 5), reverse=True)
        return job_id

    def pop_next_job(self) -> Optional[Dict[str, Any]]:
        """Pop the highest priority job from the queue."""
        if self.is_connected:
            res = self.client.zpopmax("crack:jobs:priority")
            if not res:
                return None
            job_id, _ = res[0]
            data = self.client.hget("crack:jobs:data", job_id)
            if not data:
                return None
            return json.loads(data)
        else:
            if not self._mem_queue:
                return None
            job_id = self._mem_queue.pop(0)
            return self._mem_jobs.get(job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        if self.is_connected:
            data = self.client.hget("crack:jobs:data", job_id)
            return json.loads(data) if data else None
        return self._mem_jobs.get(job_id)

    def list_all_jobs(self) -> List[Dict[str, Any]]:
        if self.is_connected:
            all_data = self.client.hgetall("crack:jobs:data")
            return [json.loads(v) for v in all_data.values()]
        return list(self._mem_jobs.values())

    def update_job_status(self, job_id: str, status: str):
        job = self.get_job(job_id)
        if job:
            job["status"] = status
            if self.is_connected:
                self.client.hset("crack:jobs:data", job_id, json.dumps(job))
                self.publish_event("job_status_changed", {"job_id": job_id, "status": status})
            else:
                self._mem_jobs[job_id]["status"] = status

    # --- Sub-range Chunks Queue ---

    def push_chunks(self, job_id: str, chunks: List[Dict[str, Any]]):
        if not chunks:
            return
        if self.is_connected:
            pipe = self.client.pipeline()
            for chunk in chunks:
                pipe.rpush(f"crack:job:{job_id}:chunks", json.dumps(chunk))
            pipe.execute()
        else:
            if job_id not in self._mem_chunks:
                self._mem_chunks[job_id] = []
            self._mem_chunks[job_id].extend(chunks)

    def pop_chunk(self, job_id: str, worker_id: str) -> Optional[Dict[str, Any]]:
        """Pop a sub-range chunk and record it as actively assigned to worker."""
        if self.is_connected:
            chunk_data = self.client.lpop(f"crack:job:{job_id}:chunks")
            if not chunk_data:
                return None
            chunk = json.loads(chunk_data)
            # Record active assignment for failover
            self.client.set(f"crack:active:{worker_id}", json.dumps(chunk))
            return chunk
        else:
            if job_id not in self._mem_chunks or not self._mem_chunks[job_id]:
                return None
            chunk = self._mem_chunks[job_id].pop(0)
            self._mem_active_work[worker_id] = chunk
            return chunk

    def complete_chunk(self, worker_id: str):
        if self.is_connected:
            self.client.delete(f"crack:active:{worker_id}")
        else:
            self._mem_active_work.pop(worker_id, None)

    def requeue_active_chunk(self, worker_id: str) -> bool:
        """Requeue chunk if worker died mid-flight."""
        if self.is_connected:
            chunk_data = self.client.get(f"crack:active:{worker_id}")
            if chunk_data:
                chunk = json.loads(chunk_data)
                job_id = chunk["job_id"]
                self.client.lpush(f"crack:job:{job_id}:chunks", chunk_data)
                self.client.delete(f"crack:active:{worker_id}")
                logger.info(f"Requeued stale chunk for dead worker {worker_id}")
                return True
            return False
        else:
            chunk = self._mem_active_work.pop(worker_id, None)
            if chunk:
                job_id = chunk["job_id"]
                self._mem_chunks.setdefault(job_id, []).insert(0, chunk)
                return True
            return False

    # --- Worker Management & Heartbeats ---

    def register_worker(self, worker_dict: Dict[str, Any]):
        worker_id = worker_dict["id"]
        worker_dict["last_heartbeat"] = time.time()
        payload = json.dumps(worker_dict)
        if self.is_connected:
            self.client.hset("crack:workers", worker_id, payload)
            self.publish_event("worker_registered", worker_dict)
        else:
            self._mem_workers[worker_id] = worker_dict

    def update_worker_status(self, worker_id: str, status: str):
        if self.is_connected:
            data = self.client.hget("crack:workers", worker_id)
            if data:
                worker = json.loads(data)
                worker["status"] = status
                self.client.hset("crack:workers", worker_id, json.dumps(worker))
        else:
            if worker_id in self._mem_workers:
                self._mem_workers[worker_id]["status"] = status

    def heartbeat(self, worker_id: str, stats: Optional[Dict[str, Any]] = None):
        if self.is_connected:
            data = self.client.hget("crack:workers", worker_id)
            if data:
                worker = json.loads(data)
                worker["last_heartbeat"] = time.time()
                if stats:
                    worker.update(stats)
                self.client.hset("crack:workers", worker_id, json.dumps(worker))
        else:
            if worker_id in self._mem_workers:
                self._mem_workers[worker_id]["last_heartbeat"] = time.time()
                if stats:
                    self._mem_workers[worker_id].update(stats)

    def get_workers(self) -> List[Dict[str, Any]]:
        if self.is_connected:
            raw = self.client.hgetall("crack:workers")
            return [json.loads(v) for v in raw.values()]
        return list(self._mem_workers.values())

    def remove_worker(self, worker_id: str):
        if self.is_connected:
            self.client.hdel("crack:workers", worker_id)
        else:
            self._mem_workers.pop(worker_id, None)

    # --- Progress & Results ---

    def record_progress(self, job_id: str, count: int):
        if self.is_connected:
            self.client.hincrby("crack:job:progress", job_id, count)
        else:
            job = self._mem_jobs.get(job_id)
            if job:
                job["evaluated_candidates"] = job.get("evaluated_candidates", 0) + count

    def get_progress(self, job_id: str) -> int:
        if self.is_connected:
            val = self.client.hget("crack:job:progress", job_id)
            return int(val) if val else 0
        job = self._mem_jobs.get(job_id)
        return job.get("evaluated_candidates", 0) if job else 0

    def record_found(self, job_id: str, found_dict: Dict[str, Any]):
        payload = json.dumps(found_dict)
        if self.is_connected:
            self.client.rpush(f"crack:job:{job_id}:found", payload)
            self.publish_event("password_found", found_dict)
        else:
            self._mem_found.setdefault(job_id, []).append(found_dict)

    def get_found(self, job_id: str) -> List[Dict[str, Any]]:
        if self.is_connected:
            items = self.client.lrange(f"crack:job:{job_id}:found", 0, -1)
            return [json.loads(i) for i in items]
        return self._mem_found.get(job_id, [])

    # --- Real-Time Events Pub/Sub ---

    def publish_event(self, event_type: str, data: Dict[str, Any]):
        msg = json.dumps({"type": event_type, "timestamp": time.time(), "data": data})
        if self.is_connected:
            try:
                self.client.publish("crack:events", msg)
            except Exception:
                pass
