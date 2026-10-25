# Distributed Password Cracker — GPU-Accelerated Audit Framework

A distributed password audit and cracking demonstration framework coordinating GPU-accelerated hashing across multiple nodes using CUDA, Redis, RabbitMQ, PostgreSQL, and FastAPI.

```
       +-----------------------------------------------------------+
       |               FastAPI Real-Time Dashboard                 |
       |             (Live Telemetry, Progress, ETA)               |
       +-----------------------------+-----------------------------+
                                     |
                                     v
                       +---------------------------+
                       |    Python Coordinator     |
                       | (Range Splitting & Logic) |
                       +------+-------------+------+
                              |             |
           +------------------+             +------------------+
           v                                                   v
+---------------------+                             +---------------------+
|   Redis Queue /     |                             |  PostgreSQL / DB    |
|   Worker Heartbeats |                             |  Results Storage    |
+----------+----------+                             +----------+----------+
           |                                                   |
           +-----------------------+---------------------------+
                                   |
             +---------------------+---------------------+
             |                                           |
             v                                           v
+-------------------------+                 +-------------------------+
|     Worker Node 1       |                 |     Worker Node 2       |
| (NVIDIA RTX 4050 CUDA)  |                 | (CPU Reference Node)    |
|   crack_gpu Extension   |                 |      cpu_hasher         |
+-------------------------+                 +-------------------------+
```

---

## 1. Ethical & Legal Notice

> [!IMPORTANT]
> This software is strictly intended for educational research and authorized defensive security assessments on owned systems or demonstration targets. Cracking hashes without explicit, written authorization from the system owner constitutes an unauthorized access violation punishable under federal and international cybercrime legislation (e.g., CFAA, Computer Misuse Act).

---

## 2. Architecture & Deliverables

- **Goal 1 — GPU-Accelerated Hash Kernels:** Custom C++17/CUDA kernels for MD5, SHA-1, SHA-256, and bcrypt candidate hashing with pybind11 bindings (`crack_gpu.hash_batch`). DMA PCIe batch transfers maximize memory throughput.
- **Goal 2 — Distributed Job Queue:** Self-contained Docker Compose infrastructure with Redis, RabbitMQ, and PostgreSQL. Priority queue management with sub-range brute-force keyspace partitioning.
- **Goal 3 — Worker Management & Health Checks:** Real-time worker registration, GPU telemetry (temperature, memory, hashrate), alive heartbeats, and automatic stale worker chunk requeuing / failover.
- **Goal 4 — Multi-Stage Attack Strategies:** Wordlist dictionary attack, sub-range brute-force generation, pattern templates (`SeasonYear`, `Password123`), ruleset mutations (leet speak, capitalization toggles, affixes), and coordinated pipeline.
- **Goal 5 — Interactive Dashboard:** Modern dark-mode FastAPI control center monitoring live cluster hashrate, GPU temperature, progress bars, ETA, and recovered credentials.
- **Goal 6 — Results Database & Security Reporting:** PostgreSQL schema with SQLAlchemy ORM, Shannon entropy calculation, pattern analysis, policy violation flags, and CLI report generator.
- **Goal 7 — Documentation:** Comprehensive primers on CUDA architecture, defensive security recommendations, and ethical/legal guidelines.

---

## 3. Quick Start & Verification

### Step 1: Start Infrastructure
```bash
docker compose up -d redis rabbitmq db
```

### Step 2: Install Package
```bash
python -m pip install -e .
```

### Step 3: Build CUDA Extension In-Place
```bash
python setup.py build_ext --inplace
```

### Step 4: Run Unit Tests
```bash
pytest tests/
```

### Step 5: Run End-to-End Distributed Cracking Demo
```bash
python scripts/demo.py
```

### Step 6: Launch Real-Time Web Dashboard
```bash
python -m crack_dashboard
```
Open your browser at `http://localhost:8000` to interact with the dashboard.

### Step 7: Run Real GPU vs. CPU Throughput Benchmark
```bash
python scripts/benchmark.py
```

---

## 4. Sourcing Wordlists Legally

The framework bundles a minimal demo list of the top 100 common passwords in `src/crack_core/wordlists/top100.txt`.

For authorized enterprise auditing, security teams can legally source larger research wordlists:
- **SecLists:** Curated lists of usernames, passwords, and patterns maintained by Daniel Miessler ([GitHub SecLists](https://github.com/danielmiessler/SecLists)).
- **Have I Been Pwned Passwords:** Over 800 million real-world compromised SHA-1/NTLM hash counts for enterprise blocklist enforcement ([HIBP Passwords](https://haveibeenpwned.com/passwords)).

---

## 5. Documentation Links
- [CUDA & GPU Cracking Basics](file:///home/honeysh/Projects/distributed-password-cracker/docs/GPU_CRACKING_BASICS.md)
- [Ethics & Legal Standards](file:///home/honeysh/Projects/distributed-password-cracker/docs/ETHICS_AND_LEGAL.md)
- [Defensive Security Recommendations](file:///home/honeysh/Projects/distributed-password-cracker/docs/SECURITY_RECOMMENDATIONS.md)
