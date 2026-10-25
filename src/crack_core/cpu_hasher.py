import hashlib
import bcrypt
from typing import List, Optional


def hash_single(algorithm: str, candidate: str, salt: str = "") -> str:
    """Compute single candidate hash using standard CPU libraries.
    
    Supported algorithms: md5, sha1, sha256, bcrypt.
    """
    algo = algorithm.lower().strip()
    cand_bytes = candidate.encode("utf-8")

    if algo == "md5":
        return hashlib.md5(cand_bytes).hexdigest()
    elif algo == "sha1":
        return hashlib.sha1(cand_bytes).hexdigest()
    elif algo == "sha256":
        return hashlib.sha256(cand_bytes).hexdigest()
    elif algo == "bcrypt":
        # Standard bcrypt cost 4 demo salt if not provided
        salt_bytes = salt.encode("utf-8") if salt else b"$2b$04$usesomesillystringfore"
        if len(salt_bytes) < 28 or not salt_bytes.startswith(b"$2"):
            # Normalize to valid cost 4 salt format
            salt_bytes = b"$2b$04$usesomesillystringfore"
        hashed = bcrypt.hashpw(cand_bytes, salt_bytes)
        return hashed.decode("utf-8")
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def hash_batch(algorithm: str, candidates: List[str], salt: str = "") -> List[str]:
    """Compute batch hashes on CPU for reference and fallback comparison."""
    algo = algorithm.lower().strip()
    cand_encoded = [c.encode("utf-8") for c in candidates]

    if algo == "md5":
        return [hashlib.md5(c).hexdigest() for c in cand_encoded]
    elif algo == "sha1":
        return [hashlib.sha1(c).hexdigest() for c in cand_encoded]
    elif algo == "sha256":
        return [hashlib.sha256(c).hexdigest() for c in cand_encoded]
    elif algo == "bcrypt":
        salt_bytes = salt.encode("utf-8") if salt else b"$2b$04$usesomesillystringfore"
        if len(salt_bytes) < 28 or not salt_bytes.startswith(b"$2"):
            salt_bytes = b"$2b$04$usesomesillystringfore"
        return [bcrypt.hashpw(c, salt_bytes).decode("utf-8") for c in cand_encoded]
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def check_candidate_match(algorithm: str, candidate: str, target_hash: str) -> bool:
    """Check if a candidate password matches the target hash."""
    algo = algorithm.lower().strip()
    if algo == "bcrypt":
        try:
            return bcrypt.checkpw(candidate.encode("utf-8"), target_hash.encode("utf-8"))
        except Exception:
            return False
    else:
        computed = hash_single(algo, candidate)
        return computed.lower() == target_hash.lower()
