import logging
import subprocess
from typing import List, Optional, Dict, Any
from crack_core import cpu_hasher

logger = logging.getLogger("crack_core.gpu_hasher")

_HAS_CUDA = False
try:
    import crack_gpu
    _HAS_CUDA = crack_gpu.is_cuda_available()
except Exception as e:
    logger.warning(f"Could not load CUDA extension crack_gpu: {e}. Falling back to CPU.")
    crack_gpu = None
    _HAS_CUDA = False


def is_cuda_available() -> bool:
    """Return whether CUDA acceleration is available on this system."""
    global _HAS_CUDA
    if crack_gpu is None:
        return False
    try:
        return crack_gpu.is_cuda_available()
    except Exception:
        return False


def get_gpu_info() -> Dict[str, Any]:
    """Retrieve GPU device name, count, and telemetry (temperature, memory)."""
    info = {
        "available": is_cuda_available(),
        "device_count": 0,
        "device_name": "CPU Fallback",
        "temperature_c": None,
        "memory_used_mb": None,
        "memory_total_mb": None
    }

    if info["available"] and crack_gpu is not None:
        try:
            info["device_count"] = crack_gpu.get_device_count()
            info["device_name"] = crack_gpu.get_device_name(0)
        except Exception:
            pass

    # Read telemetry via nvidia-smi if accessible
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = res.stdout.strip().split("\n")[0].split(",")
            if len(parts) >= 3:
                info["temperature_c"] = int(parts[0].strip())
                info["memory_used_mb"] = int(parts[1].strip())
                info["memory_total_mb"] = int(parts[2].strip())
    except Exception:
        pass

    return info


def hash_batch(algorithm: str, candidates: List[str], salt: str = "", force_cpu: bool = False) -> List[str]:
    """Hash a batch of candidate strings using CUDA or fallback to CPU.
    
    Args:
        algorithm: 'md5', 'sha1', 'sha256', or 'bcrypt'
        candidates: list of candidate passwords
        salt: optional salt string (primarily for bcrypt)
        force_cpu: force CPU calculation even if GPU is available
    """
    if not candidates:
        return []

    if not force_cpu and is_cuda_available():
        try:
            return crack_gpu.hash_batch(algorithm.lower(), candidates, salt)
        except Exception as e:
            logger.warning(f"CUDA batch hash failed: {e}. Falling back to CPU.")

    return cpu_hasher.hash_batch(algorithm, candidates, salt)
