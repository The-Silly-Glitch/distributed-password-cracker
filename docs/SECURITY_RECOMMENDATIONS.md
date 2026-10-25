# Defensive Security Recommendations & Credential Protection

## 1. Upstream Hashing: Retiring Fast Hashes

Legacy applications frequently store passwords using fast message-digest functions (MD5, SHA-1, SHA-256). As demonstrated by GPU clusters and dedicated audit rigs:
- **MD5 & SHA-1 are cryptographically broken** and can be computed at rates of billions of attempts per second on consumer GPUs.
- **Unsalted SHA-256** is susceptible to precomputed Rainbow Tables and rapid dictionary/brute-force attacks.

### Recommended Standards:
1. **Argon2id (Winner of the Password Hashing Competition):**
   - Memory-hard, compute-hard, and side-channel resistant.
   - Recommended parameters: `memory = 64 MB`, `iterations = 3`, `parallelism = 4`.
2. **bcrypt:**
   - EksBlowfish-based adaptive key derivation function.
   - Recommended work factor: `cost >= 12` (minimum ~250ms computation time on server CPUs).
   - Inherent memory requirements (4 KB state) significantly suppress GPU parallelism.
3. **Cryptographic Salting:**
   - Every password must be hashed with a unique, cryptographically secure 16+ byte salt (`os.urandom(16)`).
   - Prevents rainbow tables and ensures two identical passwords yield distinct hashes.
4. **Server-Side Pepper:**
   - An application-wide secret key stored separately (e.g., in an HSM or KMS) combined via HMAC before hashing. If the database is compromised without the KMS key, offline cracking is unfeasible.

---

## 2. Password Complexity vs. Length & Passphrases

Historically, organizations mandated frequent 90-day rotations and artificial character diversity rules (e.g., must contain 1 uppercase, 1 symbol, 1 digit). NIST Special Publication 800-63B (Digital Identity Guidelines) has overhauled these guidelines:

- **Length Trumps Complexity:** An 8-character complex password like `P@$$w0rd` has approximately 45 bits of entropy and is cracked in seconds. A 4-word random passphrase like `correct-horse-battery-staple` has over 77 bits of entropy, rendering brute-force impossible even with planetary compute capacity.
- **Ban Common Passwords:** Enforce blocklists against the top 100,000 compromised passwords from public breaches (e.g., integrating HaveIBeenPwned Passwords API via k-Anonymity).
- **Discontinue Arbitrary Expirations:** Forcing users to change passwords every 90 days causes predictable mutations (`Spring2024!` -> `Summer2024!`). Rotate passwords only upon evidence of compromise.

---

## 3. Defense-in-Depth Measures

1. **Multi-Factor Authentication (MFA / 2FA):**
   - Prioritize FIDO2 / WebAuthn passkeys and hardware security keys (YubiKey).
   - Discourage SMS 2FA due to SIM-swapping vulnerabilities.
2. **Adaptive Rate Limiting & Account Lockouts:**
   - Throttle login attempts per IP and per username using sliding-window rate limiters.
   - Implement CAPTCHAs upon 3 consecutive failed attempts.
3. **Breach Monitoring & Alerting:**
   - Continuously audit active credential hashes against known leaked hash dumps in secure staging environments.

---

## 4. Comparison: Industry Tools (Hashcat & John the Ripper)

| Capability | Hashcat | John the Ripper (JtR) | This Distributed Framework |
| :--- | :--- | :--- | :--- |
| **Primary Domain** | Extreme GPU-optimized offline cracking | Multi-format CPU/GPU security auditing | Distributed GPU cluster orchestration |
| **Kernel Implementation** | Highly optimized raw OpenCL/CUDA assembly | C/OpenCL plugin modules | Modern C++17 / CUDA SIMT with pybind11 |
| **Distributed Scaling** | Requires third-party tools (Hashtopolis) | OpenMPI / custom grid scripts | Native Redis stream/queue + Postgres + Docker |
| **Telemetry & Reporting** | CLI / stdout | CLI / stdout | Real-time FastAPI dashboard + compliance reporting |
| **Primary Focus** | Speed & algorithm breadth | Hash format diversity | Distributed architecture, safety, and compliance |
