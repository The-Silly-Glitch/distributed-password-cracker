# Distributed Password Cracker — Build Spec

Repository: `/home/honeysh/Projects/distributed-password-cracker`

## Context

Build a distributed password cracking system coordinating GPU-accelerated cracking across multiple machines. The host machine has an NVIDIA GeForce RTX 4050 Laptop GPU, CUDA 13.2 (`/usr/local/cuda-12/bin/nvcc`), and Docker Compose. Redis and RabbitMQ should be provided via Docker Compose so the queue layer is self-contained. No Redis/RabbitMQ native daemons are running.

The project must be educational, legal, and self-contained: cracking only works against hashes the user explicitly supplies (demo/test mode). It must include clear ethical/legal warnings and only support authorized/owned targets.

## Deliverables / Goals

### Goal 1 — GPU-accelerated hash kernels
- CUDA kernels for MD5, SHA1, SHA256, and bcrypt candidate hashing.
- Batch hash API in C++/CUDA with pybind11 Python bindings: `crack_gpu.hash_batch(algorithm, candidates) -> list[str]`.
- Minimize CPU↔GPU transfers: accept a large candidate buffer, hash on GPU, return hex digests.
- CPU fallback/reference implementation for correctness comparison.
- Benchmark script that compares GPU vs CPU throughput for each algorithm.

### Goal 2 — Distributed job queue
- Docker Compose file with Redis (queue/state) and RabbitMQ (optional broker) services.
- Python coordinator service using Redis lists/streams for jobs and a PostgreSQL/SQLite results DB.
- Job API: submit job with target hashes, algorithm, attack type (dictionary/brute-force/pattern/ruleset), priority.
- Workers pull jobs, report progress, write results back to Redis and the DB.
- Sub-range splitting for brute-force: e.g. worker 1 gets AAA-AAZ, worker 2 gets ABA-ABZ, preventing duplicate work.

### Goal 3 — Worker management, load balancing, health checks
- Worker registration: GPU type, hashrate, availability, heartbeat.
- Dynamic job assignment weighted by worker hashrate/GPU availability.
- Health checking: detect missing heartbeats, requeue stale work.
- Priority queue: higher-priority jobs processed first.

### Goal 4 — Attack strategies
- Dictionary attack: hash a wordlist and compare against targets.
- Brute-force attack: generate character-space combinations over a sub-range.
- Pattern attack: common templates like `Password123`, `SeasonYear`, `Name+Number`.
- Rulesets: l33t speak, capitalization toggles, append/prepend numbers/symbols.
- Strategy combination: fast strategies first, then brute-force.

### Goal 5 — Real-time dashboard and progress monitoring
- Web dashboard (FastAPI + vanilla JS or Streamlit) showing:
  - job status (queued/in-progress/completed)
  - worker stats: hashes/sec, current assignment, GPU temp if available
  - found passwords with timestamps and worker IDs
  - ETA / progress bars
- Logging of all cracked hashes, timestamps, worker info (only user-supplied demo hashes).

### Goal 6 — Results database and reporting
- SQLite/PostgreSQL schema for jobs, workers, recovered passwords, hash metadata.
- Post-processing analysis: password strength scoring, common pattern detection, policy violation flags.
- CLI report generator: table of recovered passwords, strength distribution, recommendations.

### Goal 7 — Documentation and ethics
- `README.md` with setup, build, run instructions.
- `docs/GPU_CRACKING_BASICS.md` brief CUDA/OpenCL primer.
- `docs/ETHICS_AND_LEGAL.md` clear statement that cracking without authorization is illegal; legitimate uses (own systems, authorized security assessments).
- `docs/SECURITY_RECOMMENDATIONS.md`: strong passwords, bcrypt/argon2, salting, MFA.
- Comparison with Hashcat/John the Ripper and note that bcrypt/argon2 deliberately resist cracking.

## Build & verification commands that must pass

1. `docker compose up -d redis rabbitmq db` starts the infrastructure.
2. `python -m pip install -e .` installs the Python package.
3. `python setup.py build_ext --inplace` compiles the CUDA extension.
4. `pytest tests/` passes unit tests (CPU/GPU hash correctness, job splitting, worker health, strategy tests).
5. `python scripts/demo.py` runs a small end-to-end distributed crack against test hashes and prints results.
6. `python -m crack_dashboard` launches a working dashboard.

## Constraints / Rules

- Keep dependencies minimal and pinned in `requirements.txt`.
- CUDA code must compile with nvcc 13.2. Use C++17.
- The system must default to test/demo mode; do not bundle real wordlists larger than a small demo list (top 100 common passwords). Add a note about sourcing larger wordlists legally.
- Include `.gitignore`, `pyproject.toml`, and `setup.py`/`setup.cfg`.
- All progress/reporting features must be backed by real runtime state, not hardcoded placeholders.
- Do not produce fake benchmark numbers; the benchmark script must measure actual runtime.
