# Distributed GPU Password Cracker — Project Writeup for Resume

## 1. One-line pitch
Built a distributed, GPU-accelerated password-audit framework that cracks demo hashes across multiple worker nodes with CUDA, Redis/RabbitMQ, PostgreSQL, and a live FastAPI dashboard.

## 2. Copy-paste resume bullets

**Short version (1 line):**
- Built distributed GPU password-auditing system with CUDA kernels, Redis/RabbitMQ job queue, and FastAPI live dashboard; 24/24 tests passing on RTX 4050.

**Standard version (3 bullets):**
- Implemented custom CUDA C++17 kernels (MD5, SHA-1, SHA-256, bcrypt) with pybind11 Python bindings (`crack_gpu.hash_batch`) and CPU fallback for correctness; compiled for sm_89 (RTX 4050 Laptop, CUDA 13.2).
- Built distributed backend with Docker Compose (Redis, RabbitMQ, PostgreSQL): priority job queue, keyspace sub-range splitting, worker registration/heartbeats, stale-worker failover, SQLAlchemy results store with entropy + policy-violation analysis.
- Shipped 5-theme FastAPI dashboard (Mono/Amber/Teal/Rose/Indigo) with live hashrate, GPU temp/VRAM, job progress, ETA, worker status, and recovered-credentials table; verified end-to-end demo recovers 3/3 test hashes.

**Detailed version for portfolio:**
- Designed coordinator/worker architecture: coordinator splits dictionary/brute-force/pattern/ruleset work into chunks, workers pull chunks, hash batches on GPU, report progress to Redis and results to PostgreSQL.
- Attack strategies: dictionary (top-100 demo list), brute-force generator with start/end indices, pattern templates (SeasonYear, Password123-style), rulesets (l33t, capitalization toggles, affixes), hybrid fast-to-slow pipeline.
- Measured performance with `scripts/benchmark.py` on RTX 4050 Laptop GPU: ~3.4 MH/s MD5/SHA-1/SHA-256, ~1.8 kH/s bcrypt (demo cost), ~1.4–1.5x vs CPU reference in that test harness.

## 3. Tech stack
- Languages: Python, C++17, CUDA, JavaScript, HTML/CSS
- GPU: CUDA 13.2, nvcc, pybind11, NVIDIA RTX 4050 Laptop 6GB (sm_89)
- Backend: FastAPI, Uvicorn, Jinja2, Redis (queue/heartbeats), RabbitMQ, PostgreSQL + SQLAlchemy, Pydantic
- Infra: Docker Compose, pytest (24 tests), Playwright (UI screenshots)
- Concepts: distributed job queuing, load balancing, health checks, keyspace partitioning, hash algorithms, password entropy analysis

## 4. Architecture
```
FastAPI Dashboard (live telemetry, jobs, ETA, results)
        |
Python Coordinator (splitting, priority, health checks)
      /       \
Redis Queue   PostgreSQL (jobs, workers, recovered passwords)
  /     \
GPU Worker (crack_gpu CUDA)  CPU Worker (reference hasher)
```

## 5. What was actually verified
- `pytest tests/` — 24 passed (hash correctness, job splitting, worker health, strategies, DB/reporting, dashboard API)
- `python setup.py build_ext --inplace` — CUDA extension built: `crack_gpu.cpython-314-x86_64-linux-gnu.so`
- `python scripts/demo.py` — 3/3 demo MD5 hashes recovered (`admin`, `summer`, `dragon`), audit report generated
- `python scripts/benchmark.py` — real runtime GPU vs CPU throughput measured (see numbers above)
- `python -m crack_dashboard` — serves on `http://localhost:8000`, `/api/status` returns live GPU telemetry
- Screenshots captured for all 5 themes with Playwright headless Chromium

## 6. Project location and run commands
- Repo: `/home/honeysh/Projects/distributed-password-cracker`
- Infra: `docker compose up -d redis rabbitmq db`
- Install: `python -m pip install -e .`
- Build: `python setup.py build_ext --inplace`
- Test: `pytest tests/ -q`
- Demo: `python scripts/demo.py`
- Dashboard: `python -m crack_dashboard --host 0.0.0.0 --port 8000`
- Stop: dashboard process killed, `docker compose down` (all containers removed)

## 7. Ethics note (important for resume/interviews)
Authorized-audit-only tool for education and defensive security on owned systems. Includes `docs/ETHICS_AND_LEGAL.md`, demo-only wordlist, and defensive recommendations (Argon2id/bcrypt, salting, MFA, password policy). Say this explicitly in interviews.

## 8. Interview talking points
- Why GPU batching matters: minimize CPU↔GPU transfers, hash large candidate buffers in parallel.
- Why bcrypt/Argon2 resist cracking: memory-hard, tunable cost; distribution helps less.
- How failover works: heartbeat timeout → stale chunk requeue → another worker picks it up.
- How ETA is computed: remaining candidates / active aggregate hashrate.
- What I would do next: multi-GPU scheduling, Hashcat integration comparison, Argon2 support, Kubernetes workers.

## 9. Skills this demonstrates
Distributed systems, GPU programming, backend API design, Dockerized infra, realtime dashboards, testing/benchmarking, security fundamentals.
