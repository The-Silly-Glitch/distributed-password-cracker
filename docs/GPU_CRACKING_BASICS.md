# GPU-Accelerated Password Auditing Primer

## 1. Why GPUs Excel at Hash Computation

Modern Central Processing Units (CPUs) are engineered for low-latency serial execution of complex control-flow branches, featuring large L1/L2/L3 caches, branch predictors, and out-of-order execution pipelines. In contrast, Graphics Processing Units (GPUs) are massively parallel compute engines designed around the **Single Instruction, Multiple Threads (SIMT)** execution model.

| Feature | CPU (e.g. 8-16 Cores) | GPU (e.g. NVIDIA RTX 4050, 2,560 CUDA Cores) |
| :--- | :--- | :--- |
| **Execution Units** | 8 to 32 ALUs | Thousands of FP32/INT32 execution units |
| **Parallel Threads** | Tens to hundreds | Tens of thousands in active flight |
| **Memory Bandwidth** | ~50 to 90 GB/s (DDR5) | ~192 to 1,000+ GB/s (GDDR6 / HBM) |
| **Optimization Focus** | Instruction latency & branching | Maximum compute throughput |

Because candidate hashing against precomputed target hashes involves executing the exact same mathematical operations (bitwise AND, OR, XOR, rotations, and 32-bit integer additions) over millions of independent candidate strings, the problem exhibits **embarrassingly parallel** characteristics perfectly tailored for GPU warps.

---

## 2. GPU Hardware Architecture & SIMT Execution

In NVIDIA's architecture (such as Ada Lovelace):
1. **Streaming Multiprocessors (SMs):**
   The GPU is composed of multiple SMs. Each SM contains execution units, register files, L1 data cache/shared memory, and warp schedulers.
2. **Warps:**
   Threads are grouped into execution units of **32 threads called a warp**. All 32 threads in a warp execute the same instruction simultaneously. If threads diverge (e.g., conditional branching based on string length), the warp serializes each branch path, causing branch divergence penalties. To maximize throughput:
   - Candidates are padded to uniform block boundaries.
   - Algorithms avoid dynamic runtime branching.
3. **Memory Hierarchy & Latency Hiding:**
   - **Registers:** Fastest storage (~few clock cycles). State variables (A, B, C, D in MD5; H0-H7 in SHA-256) are kept in registers.
   - **Constant Memory:** Read-only cached memory (64 KB). Constants such as `SHA256_K[64]` and Blowfish P/S tables are mapped here for rapid broadcast across warps.
   - **Shared Memory:** User-managed L1 cache shared across threads within a thread block.
   - **Global Memory / PCIe DMA:** Off-chip GDDR6 DRAM and CPU-GPU PCIe bus. Global memory accesses require hundreds of clock cycles. To prevent memory bandwidth bottlenecks:
     - Candidates are packed into a single contiguous contiguous host buffer.
     - A single DMA transfer moves thousands of candidates across PCIe.
     - Hashes are computed entirely in registers and local memory.
     - Hex digests are copied back to host memory in a single DMA transfer.

---

## 3. Fast Hashes vs. Slow Key Derivation Functions (KDFs)

Not all hashing algorithms respond equally to GPU acceleration:

### Compute-Bound Fast Hashes (MD5, SHA-1, SHA-256)
- **Design Intent:** Message integrity verification and digital signatures. Designed to run as fast as possible on hardware.
- **Memory Footprint:** Zero dynamic memory requirements; state fits entirely into 4 to 8 32-bit registers.
- **GPU Scaling:** Scales almost linearly with CUDA core counts. A modern GPU cluster can evaluate billions of SHA-256 hashes per second.

### Memory-Hard / Compute-Hard Functions (bcrypt, scrypt, Argon2id)
- **Design Intent:** Credential storage deliberately designed to resist parallel hardware acceleration (ASICs, FPGAs, and GPUs).
- **bcrypt (EksBlowfish):** Requires 4 KB of S-box lookup tables per candidate and repeats key expansion for $2^{\text{cost}}$ iterations. The 4 KB table creates memory pressure on thread-local cache and register files, severely limiting the number of active warps per SM.
- **scrypt / Argon2id:** Requires megabytes of pseudo-random memory read/writes (memory-hardness). Even high-end GPUs quickly saturate their memory bus, driving throughput down from millions/sec to tens or hundreds/sec.
