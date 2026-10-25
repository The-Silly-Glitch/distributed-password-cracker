import time
import hashlib
from crack_core.coordinator import Coordinator
from crack_core.worker import CrackWorker
from crack_core.queue import CrackQueue
from crack_core.reporter import generate_report
from crack_core.db import init_db


def main():
    print("=" * 86)
    print("      DISTRIBUTED GPU PASSWORD CRACKING DEMO — END-TO-END VERIFICATION")
    print("=" * 86)
    print("Notice: Cracking authorized demonstration target hashes only.")
    print("-" * 86)

    # Initialize environment
    init_db()
    queue = CrackQueue()
    coordinator = Coordinator(queue=queue)

    # Define demo targets (common passwords in wordlists/rules)
    demo_targets = [
        {"password": "admin", "hash": hashlib.md5(b"admin").hexdigest(), "algo": "md5"},
        {"password": "summer", "hash": hashlib.md5(b"summer").hexdigest(), "algo": "md5"},
        {"password": "dragon", "hash": hashlib.md5(b"dragon").hexdigest(), "algo": "md5"},
    ]

    print("\n[+] Target Hashes for Demo:")
    target_hashes = []
    for dt in demo_targets:
        print(f"  * Plaintext: '{dt['password']}' -> MD5: {dt['hash']}")
        target_hashes.append(dt["hash"])

    # Register two simulated distributed workers
    print("\n[+] Initializing Distributed Workers:")
    worker1 = CrackWorker(worker_id="worker-node-gpu-rtx4050", queue=queue, force_cpu=False)
    worker2 = CrackWorker(worker_id="worker-node-cpu-fallback", queue=queue, force_cpu=True)
    print(f"  * Node 1: {worker1.worker_id} ({worker1.gpu_info['device_name']}) @ {worker1.hashrate:,.0f} H/s")
    print(f"  * Node 2: {worker2.worker_id} (CPU Reference Node) @ {worker2.hashrate:,.0f} H/s")

    # Submit job to coordinator
    job_id = coordinator.submit_job(
        name="Demo End-to-End Crack Job",
        algorithm="md5",
        target_hashes=target_hashes,
        attack_type="hybrid",
        priority=10
    )
    print(f"\n[+] Job Dispatched: ID={job_id} (Priority=10, Algorithm=MD5)")

    # Execute distributed work chunks
    print("\n[+] Distributed Workers Pulling Chunks & Cracking...")
    workers = [worker1, worker2]
    all_done = False
    max_rounds = 20

    for rnd in range(max_rounds):
        chunks_processed_this_round = 0
        for w in workers:
            w.heartbeat()
            eval_count = w.process_one_chunk(job_id)
            if eval_count is not None:
                chunks_processed_this_round += 1
                progress = queue.get_progress(job_id)
                found = queue.get_found(job_id)
                print(f"  [{w.worker_id[:18]}] Evaluated {eval_count} candidates | Total Job Progress: {progress} | Cracked: {len(found)}/{len(target_hashes)}")

        # Check if all target hashes found
        found_now = queue.get_found(job_id)
        if len(found_now) >= len(target_hashes):
            queue.update_job_status(job_id, "completed")
            all_done = True
            break

        if chunks_processed_this_round == 0:
            break

    print(f"\n[+] Cracking Run Finished! Checking Results...")
    found_final = queue.get_found(job_id)
    print(f"Successfully Recovered {len(found_final)} / {len(target_hashes)} Target Hashes:\n")

    for f in found_final:
        if f.get("plaintext"):
            print(f"  * Hash: {f['hash_val']} -> Plaintext: '{f['plaintext']}' (Worker: {f['worker_id']})")

    # Print formatted security audit report
    print("\n" + generate_report(job_id=job_id))


if __name__ == "__main__":
    main()
