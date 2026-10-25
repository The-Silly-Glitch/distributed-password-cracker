import sys
import argparse
from typing import List, Dict, Any, Optional
from crack_core.db import get_session
from crack_core.models import RecoveredPassword, Job
from crack_core.analyzer import analyze_password


def generate_report(job_id: Optional[str] = None) -> str:
    """Generate a formatted security audit report of recovered passwords."""
    with get_session() as session:
        query = session.query(RecoveredPassword)
        if job_id:
            query = query.filter(RecoveredPassword.job_id == job_id)
        results = query.all()

        jobs = session.query(Job).all()
        job_map = {j.id: j for j in jobs}

    lines = []
    lines.append("=" * 86)
    lines.append("           DISTRIBUTED PASSWORD AUDIT & COMPLIANCE ASSESSMENT REPORT")
    lines.append("=" * 86)

    if not results:
        lines.append("\nNo cracked passwords found in the database.")
        if job_id:
            lines.append(f"Specified Job ID: {job_id}")
        lines.append("=" * 86)
        return "\n".join(lines)

    lines.append(f"\nTotal Recovered Credentials: {len(results)}")
    if job_id and job_id in job_map:
        job = job_map[job_id]
        lines.append(f"Job Name: {job.name} (Algorithm: {job.algorithm}, Priority: {job.priority})")

    lines.append("\n" + "-" * 86)
    lines.append(f"{'Target Hash (Prefix)':<22} | {'Algorithm':<8} | {'Recovered Plaintext':<18} | {'Entropy':<8} | {'Rating':<10}")
    lines.append("-" * 86)

    rating_counts = {"Very Weak": 0, "Weak": 0, "Moderate": 0, "Strong": 0, "Very Strong": 0}
    common_violations = []

    for r in results:
        analysis = analyze_password(r.plaintext)
        rating = analysis["rating"]
        rating_counts[rating] = rating_counts.get(rating, 0) + 1
        common_violations.extend(analysis["policy_violations"])

        hash_display = (r.hash_val[:18] + "..") if len(r.hash_val) > 20 else r.hash_val
        lines.append(
            f"{hash_display:<22} | {r.algorithm:<8} | {r.plaintext:<18} | {analysis['entropy_bits']:<8.1f} | {rating:<10}"
        )

    lines.append("-" * 86)

    # Strength Distribution
    lines.append("\n[+] PASSWORD STRENGTH DISTRIBUTION:")
    for rating, count in rating_counts.items():
        bar = "#" * int(count * 2)
        pct = (count / len(results)) * 100
        lines.append(f"  - {rating:<12}: {count:>3} ({pct:>5.1f}%) {bar}")

    # Key Risk Findings
    lines.append("\n[!] KEY RISK FINDINGS & POLICY VIOLATIONS:")
    if common_violations:
        from collections import Counter
        for viol, cnt in Counter(common_violations).most_common(5):
            lines.append(f"  * {cnt} passwords flagged: {viol}")
    else:
        lines.append("  * None detected in sample.")

    # Recommendations
    lines.append("\n[*] DEFENSIVE SECURITY RECOMMENDATIONS:")
    lines.append("  1. Upstream Hashing: Immediately retire legacy unsalted/fast hashes (MD5, SHA-1, SHA-256)")
    lines.append("     in credential storage. Migrate to memory-hard KDFs: Argon2id or bcrypt (cost >= 12).")
    lines.append("  2. Minimum Length: Enforce a minimum length of 14-16 characters or 4-word passphrases.")
    lines.append("  3. Ban Common Patterns: Disallow common dictionary words, sequential digits, and seasons/years.")
    lines.append("  4. Multi-Factor Authentication: Implement FIDO2/WebAuthn hardware MFA to mitigate credential replay.")
    lines.append("=" * 86)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Distributed Password Cracker - Security Audit Report Generator")
    parser.add_argument("--job-id", type=str, default=None, help="Filter report by specific Job ID")
    parser.add_argument("--all", action="store_true", help="Include all historical jobs")
    args = parser.parse_args()

    report_text = generate_report(job_id=args.job_id)
    print(report_text)


if __name__ == "__main__":
    main()
