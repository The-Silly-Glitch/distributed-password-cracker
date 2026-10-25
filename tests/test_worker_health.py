import time
from crack_core.queue import CrackQueue
from crack_core.coordinator import Coordinator


def test_worker_registration_and_heartbeat():
    queue = CrackQueue()
    worker_id = "test-worker-node-1"
    worker_data = {
        "id": worker_id,
        "name": "Node 1",
        "gpu_name": "Test GPU",
        "device_count": 1,
        "hashrate": 50000.0,
        "status": "idle"
    }

    queue.register_worker(worker_data)
    workers = queue.get_workers()
    found = next((w for w in workers if w["id"] == worker_id), None)
    assert found is not None
    assert found["hashrate"] == 50000.0

    # Heartbeat
    queue.heartbeat(worker_id, {"hashrate": 55000.0, "status": "busy"})
    updated = next((w for w in queue.get_workers() if w["id"] == worker_id), None)
    assert updated["hashrate"] == 55000.0
    assert updated["status"] == "busy"


def test_stale_worker_detection_and_requeue():
    queue = CrackQueue()
    coordinator = Coordinator(queue=queue)
    worker_id = "test-stale-worker"

    # Register worker with an old heartbeat timestamp
    worker_data = {
        "id": worker_id,
        "name": "Stale Node",
        "gpu_name": "Old GPU",
        "device_count": 1,
        "hashrate": 1000.0,
        "status": "busy"
    }
    queue.register_worker(worker_data)

    # Artificially set heartbeat to 30 seconds in the past
    if queue.is_connected:
        import json
        raw = queue.client.hget("crack:workers", worker_id)
        if raw:
            w_obj = json.loads(raw)
            w_obj["last_heartbeat"] = time.time() - 30.0
            queue.client.hset("crack:workers", worker_id, json.dumps(w_obj))
    else:
        queue._mem_workers[worker_id]["last_heartbeat"] = time.time() - 30.0

    # Assign an active chunk to this worker
    chunk = {
        "job_id": "job-test-failover",
        "chunk_idx": 1,
        "start_idx": 0,
        "end_idx": 500
    }
    if queue.is_connected:
        import json
        queue.client.set(f"crack:active:{worker_id}", json.dumps(chunk))
    else:
        queue._mem_active_work[worker_id] = chunk

    # Health check with 10s timeout
    dead = coordinator.check_worker_health(timeout_seconds=10.0)
    assert worker_id in dead

    # Verify worker status is now offline
    w_after = next((w for w in queue.get_workers() if w["id"] == worker_id), None)
    assert w_after["status"] == "offline"

    # Verify the chunk was requeued
    requeued_chunk = queue.pop_chunk("job-test-failover", "new-worker")
    assert requeued_chunk is not None
    assert requeued_chunk["chunk_idx"] == 1
