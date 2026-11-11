# Distributed GPU Password Cracker — GPU-Accelerated Audit Framework

A distributed password-audit demonstration framework coordinating GPU-accelerated hashing across multiple worker nodes, using CUDA, Redis, RabbitMQ, PostgreSQL, and a live FastAPI dashboard.

> [!IMPORTANT]
> **Authorized audit only.** This software is strictly for educational research and authorized defensive security assessments on systems you own or have explicit written permission to test. Cracking hashes without authorization is illegal (e.g. CFAA, Computer Misuse Act, EU Directive 2013/40/EU, India IT Act §43/§66). See `docs/ETHICS_AND_LEGAL.md`.

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

## 1. Repository

- **GitHub:** https://github.com/The-Silly-Glitch/distributed-password-cracker (public, branch `main`)
- The repo contains **only source files** needed to recreate the project from scratch. Screenshots (`*.png`), local task notes (`AGY_TASK.md`), and the resume draft (`RESUME_WRITEUP.md`) are git-ignored and never pushed.

## 2. Recreate from scratch (fresh machine)

### 2.1 Prerequisites — what you need and where to get it

| Requirement | Version used | How to get it |
|---|---|---|
| Ubuntu/Debian Linux | 22.04+ | Any recent distro works |
| NVIDIA GPU + driver | RTX 4050 Laptop, driver 595.x | [NVIDIA drivers](https://www.nvidia.com/drivers) (`nvidia-smi` must work) |
| CUDA Toolkit (`nvcc`) | 13.2 | [CUDA downloads](https://developer.nvidia.com/cuda-downloads) — `setup.py` also checks `CUDA_HOME`, `/usr/local/cuda`, and `PATH` |
| Docker + Compose | Compose v2.30+ | [Docker install](https://docs.docker.com/engine/install) |
| Python | ≥ 3.10 (tested on 3.14) | [python.org](https://www.python.org/downloads) or distro package |
| `gh` CLI (optional) | any recent | [cli.github.com](https://cli.github.com) — only needed to clone/push |
| Playwright Chromium (optional) | only for re-taking dashboard screenshots | `pip install playwright pillow && python -m playwright install chromium` |

All other dependencies come from files **in this repo**:

| File | How to get it | Purpose |
|---|---|---|
| `docker-compose.yml` | in repo | Pulls `redis:7-alpine`, `rabbitmq:3-management-alpine`, `postgres:16-alpine` automatically via `docker compose up` |
| `requirements.txt` / `pyproject.toml` | in repo | `pip install -e .` installs FastAPI, Uvicorn, Redis, Pika, SQLAlchemy, psycopg2, bcrypt, Pydantic, Jinja2, pybind11, pytest |
| `src/cuda/*` | in repo | CUDA kernels compiled locally by `setup.py` — no download needed |
| `src/crack_core/wordlists/top100.txt` | in repo | Bundled demo wordlist (see §3) — no download needed |

### 2.2 Steps

```bash
# 1. Clone
git clone https://github.com/The-Silly-Glitch/distributed-password-cracker.git
cd distributed-password-cracker

# 2. Start infrastructure (Redis, RabbitMQ, PostgreSQL)
docker compose up -d redis rabbitmq db

# 3. Install the Python package
python -m pip install -e .

# 4. Build the CUDA extension in place
python setup.py build_ext --inplace
# Produces crack_gpu.*.so (git-ignored build artifact). Default target is sm_89
# (RTX 4050/Ada). For a different GPU, edit the -arch flag in setup.py.

# 5. Run the test suite
pytest tests/ -q
# Expected: 24 passed

# 6. Run the end-to-end distributed demo (synthetic targets, no download)
python scripts/demo.py
# Expected: recovers 3/3 demo hashes + prints audit report

# 7. Launch the dashboard
python -m crack_dashboard --host 0.0.0.0 --port 8000
# Open http://localhost:8000 — 5 themes: Mono, Amber, Teal, Rose, Indigo

# 8. Benchmark GPU vs CPU throughput (synthetic candidates, no download)
python scripts/benchmark.py
```

To stop everything: kill the dashboard process, then `docker compose down`.

---

## 3. Datasets — complete guide

**Nothing needs downloading to run this project.** Every bundled/used dataset is documented below, plus optional external wordlists and exactly how to plug them in.

### 3.1 Bundled: `src/crack_core/wordlists/top100.txt` (in repo, no download)

- **What:** 100 common passwords, one per line (`123456`, `password`, `qwerty`, `dragon`, `admin`, `summer`, … plus `demo123`, `godpass`, `alpha1`–`papa16` filler entries).
- **Source:** Hand-compiled demo list in this repo for offline testing — deliberately small so the repo stays self-contained.
- **Used by:** `DictionaryStrategy` (default) via `load_demo_wordlist()` in `src/crack_core/wordlists/__init__.py`; the demo's targets (`admin`, `summer`, `dragon`) are all in this list, which is why the demo recovers 3/3.
- **License/ethics:** Common-password strings are facts, not copyrightable; safe to bundle. Demo/audit use only.

### 3.2 Synthetic runtime datasets (generated in code, no files, no download)

| Dataset | Generated where | Contents |
|---|---|---|
| Demo target hashes | `scripts/demo.py` | MD5 of `admin`, `summer`, `dragon` computed at runtime with `hashlib` — no hash file exists anywhere |
| Benchmark candidates | `scripts/benchmark.py` | `candidate_pass_0 … candidate_pass_99999` (100k for MD5/SHA-1/SHA-256, 100 for bcrypt), generated in memory |
| Brute-force keyspace | `src/crack_core/strategies/brute_force.py` | Character combinations generated on the fly over a worker's assigned sub-range — never stored |
| Pattern candidates | `src/crack_core/strategies/pattern.py` | Templates like `SeasonYear`, `Password123` expanded at runtime |
| Ruleset mutations | `src/crack_core/strategies/rules.py` | l33t-speak, capitalization toggles, affixes applied to base words at runtime |

### 3.3 Optional external wordlists (NOT required, NOT bundled)

For authorized enterprise audits you can drop in a larger list. The code accepts any Python list — no format changes needed:

```python
from crack_core.strategies.dictionary import DictionaryStrategy

with open("/path/to/wordlist.txt", errors="ignore") as f:
    words = [line.strip() for line in f if line.strip()]
strategy = DictionaryStrategy(wordlist=words)
```

| Wordlist | Where to download | Size / notes | How to use |
|---|---|---|---|
| **SecLists** (recommended) | https://github.com/danielmiessler/SecLists — `git clone https://github.com/danielmiessler/SecLists.git ~/SecLists` | Curated, research-maintained; start with `Passwords/Common-Credentials/10-million-password-list-top-100000.txt` | Pass path to `DictionaryStrategy(wordlist=...)`; keep the clone outside this repo |
| **rockyou.txt** | Inside SecLists at `Passwords/Leaked-Databases/rockyou.txt.tar.gz`, or Kaggle (“rockyou”) mirrors | ~14M passwords from the 2009 RockYou breach; heavy — only for authorized audits on isolated machines | Same as above; do not commit it to this repo |
| **Have I Been Pwned passwords** | https://haveibeenpwned.com/passwords (SHA-1/NTLM hash-count lists, ~800M entries) | Best used as a **blocklist** (check if a password appears) rather than a cracking dictionary | Download separately; never upload recovered plaintexts to the online API — use the offline hash list |

Rules: never commit large wordlists to this repo, never run them against systems you don't own, and shred test hash databases when an audit is done (see `docs/ETHICS_AND_LEGAL.md`).

---

## 4. File inventory — what's in the repo and why

### Root

| File | Purpose | External? |
|---|---|---|
| `README.md` | This file | — |
| `docker-compose.yml` | Redis + RabbitMQ + PostgreSQL services | Images pulled from Docker Hub on first `up` |
| `requirements.txt` / `pyproject.toml` | Pinned Python dependencies | Installed from PyPI |
| `setup.py` | Custom `build_ext` that compiles `src/cuda/*` with `nvcc -arch=sm_89 -std=c++17 -O3` | Needs local CUDA toolkit |
| `.gitignore` | Ignores `*.so`, `*.db`, `build/`, `*.png`, local notes | — |

### `src/cuda/` — GPU kernels (C++/CUDA, compiled locally)

| File | Contents |
|---|---|
| `crack_gpu.cu` | Kernel launch code, batch candidate hashing entry point |
| `kernels.cuh` | Shared kernel helpers |
| `md5.cuh` / `sha1.cuh` / `sha256.cuh` | Per-algorithm device hash implementations |
| `bcrypt.cuh` | bcrypt candidate hashing (demo cost — deliberately slow by design) |
| `bindings.cpp` | pybind11 bindings exposing `crack_gpu.hash_batch` |

### `src/crack_core/` — distributed backend

| File | Role |
|---|---|
| `gpu_hasher.py` / `cpu_hasher.py` | GPU batch API + CPU reference implementation (correctness checks, fallback) |
| `coordinator.py` | Job submission, keyspace sub-range splitting, priority handling |
| `queue.py` | Redis lists/sorted-sets for jobs, chunks, heartbeats; in-memory fallback if Redis is down |
| `worker.py` | Worker daemon: registration, benchmarking, chunk execution, heartbeats, result reporting |
| `models.py` / `db.py` | SQLAlchemy schema + session handling (jobs, workers, recovered passwords) |
| `analyzer.py` / `reporter.py` | Shannon entropy, pattern detection, policy-violation flags, CLI report |
| `strategies/` | `dictionary.py`, `brute_force.py`, `pattern.py`, `rules.py`, `pipeline.py` (hybrid fast→slow), `base.py` |
| `wordlists/top100.txt` | Bundled demo wordlist (§3.1) |

### `src/crack_dashboard/` — web UI

| File | Role |
|---|---|
| `app.py` | FastAPI app + `/api/*` endpoints (status, jobs, workers, recovered) |
| `__main__.py` | `python -m crack_dashboard` launcher |
| `templates/index.html` | Dashboard page (theme switcher: Mono/Amber/Teal/Rose/Indigo) |
| `static/style.css` / `static/app.js` | Theme CSS + live polling, charts, job submission, toasts |

### `scripts/` — runnable entry points

| File | Command | What it does |
|---|---|---|
| `demo.py` | `python scripts/demo.py` | 2-worker distributed crack of 3 synthetic MD5 targets → audit report |
| `benchmark.py` | `python scripts/benchmark.py` | Real GPU-vs-CPU throughput table (MD5/SHA-1/SHA-256/bcrypt) |

### `tests/` — `pytest tests/` (24 tests)

Hash correctness (GPU vs CPU), job-splitting bijection, worker health/failover, strategy generation, DB + reporting, dashboard API.

### `docs/`

`ETHICS_AND_LEGAL.md` (authorization rules, CFAA/CMA/EU/IT-Act references), `GPU_CRACKING_BASICS.md` (CUDA primer), `SECURITY_RECOMMENDATIONS.md` (Argon2id/bcrypt, salting, MFA, policy).

### Deliberately NOT in the repo

Build outputs (`*.so`, `build/`), runtime state (`*.db`, Redis/Postgres volumes), screenshots (`*.png`), local notes (`AGY_TASK.md`, `RESUME_WRITEUP.md`) — all git-ignored; everything is reproducible from source.

---

## 5. Verification checklist

| Command | Expected |
|---|---|
| `docker compose up -d redis rabbitmq db` | `crack_redis`, `crack_rabbitmq`, `crack_postgres` healthy |
| `python -m pip install -e .` | Installs cleanly |
| `python setup.py build_ext --inplace` | `crack_gpu.*.so` built for your GPU |
| `pytest tests/ -q` | **24 passed** |
| `python scripts/demo.py` | **3/3 targets recovered** |
| `python -m crack_dashboard` | Serves `http://localhost:8000`, `/api/status` shows live GPU telemetry |
| `python scripts/benchmark.py` | Measured table (reference run on RTX 4050 Laptop: ~3.4 MH/s MD5/SHA-1/SHA-256, ~1.8 kH/s bcrypt) |

## 6. Notes for other GPUs

`setup.py` defaults to `-arch=sm_89` (Ada Lovelace / RTX 4050). For a different card, change `arch_flags` (e.g. `-arch=sm_80` for Ampere, `-arch=native` where supported) and rebuild. Everything else is GPU-agnostic; without CUDA the CPU fallback still runs all strategies, tests, and the demo.

## 7. Documentation links

- `docs/GPU_CRACKING_BASICS.md` — CUDA primer
- `docs/ETHICS_AND_LEGAL.md` — ethics and legal standards
- `docs/SECURITY_RECOMMENDATIONS.md` — defensive security recommendations
