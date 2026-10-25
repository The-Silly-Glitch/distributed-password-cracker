# Legal Framework & Ethical Guidelines for Password Auditing

## 1. Legal Warning & Prohibited Conduct

Password cracking, unauthorized access to computer systems, and intercepting or tampering with electronic communications are severe criminal offenses under international and domestic cybercrime legislation:

- **United States:** Computer Fraud and Abuse Act (CFAA, 18 U.S.C. § 1030) prohibits accessing a protected computer without authorization or exceeding authorized access. Penalties include substantial fines and multi-year federal imprisonment.
- **United Kingdom:** Computer Misuse Act 1990 (Section 1–3) penalizes unauthorized access to computer material and unauthorized acts with intent to impair computer operations.
- **European Union:** Directive 2013/40/EU on attacks against information systems mandates criminal sanctions for illegal system access, illegal data interference, and related offenses.
- **India:** Information Technology Act 2000 (Section 43 & 66) penalizes unauthorized access, password interception, and data extraction.

**Under no circumstances should this software be pointed at hashes, databases, or systems without explicit, verifiable, and written authorization from the system owner.**

---

## 2. Legitimate, Authorized Dual-Use Scenarios

Cryptographic auditing and recovery tools have recognized legitimate applications within enterprise cybersecurity, auditing, and academic research:

1. **System Administration & Self-Recovery:**
   - Recovering lost administrative or system passwords for owned infrastructure where legitimate key recovery paths are unavailable.
2. **Defensive Password Policy Audits:**
   - Security teams extracting active directory or database password hashes in an isolated environment to verify compliance with enterprise password policies (e.g., verifying that no employees are using passwords from the top 100,000 breached password list or vulnerable pattern templates).
3. **Authorized Penetration Testing & Red Teaming:**
   - Third-party security consultants operating under a strict **Rules of Engagement (RoE)** contract and written **Letter of Authorization (LoA)** signed by corporate executives.
4. **Academic Research & Cryptanalysis:**
   - Studying hash function collision resistance, evaluating parallel computing throughput across GPU architectures, and analyzing password entropy models.

---

## 3. Strict Operating Principles

When conducting password security audits:
- **Environment Isolation:** Hash auditing must strictly occur on isolated, air-gapped or dedicated offline audit workstations. Hashes or recovered plaintexts should never be uploaded to external public pastebins or cloud services.
- **Need-to-Know Principle:** Recovered plaintexts from internal audits should not be disclosed or shared in plaintext with colleagues. Audit reports should report policy violations, entropy metrics, and hashed identifiers rather than exposing raw user passwords.
- **Secure Destruction:** Test hash databases, wordlist derivatives, and cracked results files must be securely shredded once the assessment report is finalized.
