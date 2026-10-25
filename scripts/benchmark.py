import time
import argparse
from typing import List
from crack_core import cpu_hasher, gpu_hasher


def run_benchmark(algorithms: List[str] = None):
    if algorithms is None:
        algorithms = ["md5", "sha1", "sha256", "bcrypt"]

    print("=" * 88)
    print("      REAL GPU VS CPU THROUGHPUT BENCHMARK (RTX 4050 vs CPU Reference)")
    print("=" * 88)

    gpu_info = gpu_hasher.get_gpu_info()
    print(f"CUDA Available : {gpu_info['available']}")
    print(f"Device Name    : {gpu_info['device_name']}")
    if gpu_info.get("temperature_c"):
        print(f"GPU Temperature: {gpu_info['temperature_c']} °C")
    print("-" * 88)
    print(f"{'Algorithm':<10} | {'Count':<7} | {'CPU Time':<10} | {'CPU Hashrate':<14} | {'GPU Time':<10} | {'GPU Hashrate':<14} | {'Speedup':<8}")
    print("-" * 88)

    for algo in algorithms:
        algo = algo.lower().strip()
        # For fast algorithms use 100,000 candidates; for bcrypt use 100 candidates (computationally heavy)
        count = 100 if algo == "bcrypt" else 100000
        candidates = [f"candidate_pass_{i}" for i in range(count)]

        # --- CPU Benchmark ---
        t0_cpu = time.perf_counter()
        cpu_results = cpu_hasher.hash_batch(algo, candidates)
        t_cpu = max(0.00001, time.perf_counter() - t0_cpu)
        cpu_rate = count / t_cpu

        # --- GPU Benchmark ---
        # Warmup
        gpu_hasher.hash_batch(algo, candidates[:min(count, 1000)], force_cpu=False)

        t0_gpu = time.perf_counter()
        gpu_results = gpu_hasher.hash_batch(algo, candidates, force_cpu=False)
        t_gpu = max(0.00001, time.perf_counter() - t0_gpu)
        gpu_rate = count / t_gpu

        speedup = gpu_rate / cpu_rate if cpu_rate > 0 else 1.0

        # Verify sample correctness between CPU and GPU
        if algo != "bcrypt":
            assert cpu_results[0] == gpu_results[0], f"Hash mismatch on {algo}: {cpu_results[0]} != {gpu_results[0]}"

        # Formatting
        cpu_rate_str = f"{cpu_rate:,.0f} H/s" if cpu_rate < 1e6 else f"{cpu_rate/1e6:.2f} MH/s"
        gpu_rate_str = f"{gpu_rate:,.0f} H/s" if gpu_rate < 1e6 else f"{gpu_rate/1e6:.2f} MH/s"

        print(
            f"{algo.upper():<10} | {count:<7} | {t_cpu:<9.4f}s | {cpu_rate_str:<14} | {t_gpu:<9.4f}s | {gpu_rate_str:<14} | {speedup:<7.1f}x"
        )

    print("=" * 88)
    print("Benchmark completed. Measured actual runtime execution on host hardware.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real GPU vs CPU Throughput Benchmark")
    parser.add_argument("--algo", type=str, default=None, help="Specific algorithm (md5, sha1, sha256, bcrypt)")
    args = parser.parse_args()

    algos = [args.algo] if args.algo else ["md5", "sha1", "sha256", "bcrypt"]
    run_benchmark(algos)
