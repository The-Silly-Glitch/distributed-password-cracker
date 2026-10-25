import os
import time
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from crack_core.coordinator import Coordinator
from crack_core.queue import CrackQueue
from crack_core.gpu_hasher import get_gpu_info
from crack_core.analyzer import analyze_password
from crack_core.db import get_session, init_db
from crack_core.models import Job, Worker, RecoveredPassword


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Distributed Password Cracker Dashboard", version="0.1.0", lifespan=lifespan)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

coordinator = Coordinator()
queue = coordinator.queue


class JobSubmission(BaseModel):
    name: str = "Test Crack Job"
    algorithm: str = "md5"
    target_hashes: List[str]
    attack_type: str = "hybrid"
    priority: int = 5
    parameters: Optional[Dict[str, Any]] = None


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/status")
def get_system_status():
    coordinator.check_worker_health(timeout_seconds=15)
    workers = queue.get_workers()
    active_workers = [w for w in workers if w.get("status") not in ("offline", "stale")]
    # Sum hashrate for alive workers; stale/offline workers do not contribute
    total_hashrate = sum(float(w.get("hashrate", 0.0)) for w in active_workers)

    jobs = queue.list_all_jobs()
    active_jobs = [j for j in jobs if j.get("status") in ["queued", "in_progress"]]
    completed_jobs = [j for j in jobs if j.get("status") == "completed"]

    all_found = []
    seen_hashes = set()
    for j in jobs:
        for f in queue.get_found(j["id"]):
            key = f"{f.get('hash_val')}:{f.get('plaintext')}"
            if key not in seen_hashes:
                seen_hashes.add(key)
                all_found.append(f)

    gpu_telemetry = get_gpu_info()

    return {
        "active_workers": len(active_workers),
        "total_workers": len(workers),
        "total_hashrate": round(total_hashrate, 1),
        "active_jobs": len(active_jobs),
        "completed_jobs": len(completed_jobs),
        "total_jobs": len(jobs),
        "total_recovered": len(all_found),
        "gpu_telemetry": gpu_telemetry
    }


@app.get("/api/jobs")
def list_jobs():
    jobs = queue.list_all_jobs()
    # Sort by priority desc, then created_at desc
    jobs.sort(key=lambda j: (j.get("priority", 5), j.get("created_at", "")), reverse=True)

    enhanced = []
    for j in jobs:
        job_id = j["id"]
        progress = queue.get_progress(job_id)
        found = queue.get_found(job_id)
        total = j.get("total_candidates", 0)
        pct = round((progress / total * 100), 1) if total > 0 else 0.0
        
        # Calculate ETA based on progress & active hashrate
        workers = [w for w in queue.get_workers() if w.get("current_job_id") == job_id]
        active_rate = sum(float(w.get("hashrate", 0)) for w in workers)
        rem = max(0, total - progress)
        eta_sec = round(rem / active_rate, 1) if active_rate > 0 else None

        item = dict(j)
        item["progress"] = progress
        item["percent_complete"] = min(100.0, pct)
        item["recovered_count"] = len(found)
        item["target_count"] = len(j.get("target_hashes", []))
        item["eta_seconds"] = eta_sec
        enhanced.append(item)

    return enhanced


@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: str):
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    found = queue.get_found(job_id)
    progress = queue.get_progress(job_id)
    total = job.get("total_candidates", 0)

    analyzed_found = []
    for f in found:
        af = dict(f)
        af["analysis"] = analyze_password(f["plaintext"])
        analyzed_found.append(af)

    return {
        "job": job,
        "progress": progress,
        "total_candidates": total,
        "percent_complete": round(progress / total * 100, 1) if total > 0 else 0.0,
        "recovered": analyzed_found
    }


@app.post("/api/jobs")
def create_job(payload: JobSubmission):
    if not payload.target_hashes:
        raise HTTPException(status_code=400, detail="Must provide at least one target hash")

    job_id = coordinator.submit_job(
        name=payload.name,
        algorithm=payload.algorithm,
        target_hashes=payload.target_hashes,
        attack_type=payload.attack_type,
        priority=payload.priority,
        parameters=payload.parameters
    )
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/workers")
def list_workers():
    coordinator.check_worker_health(timeout_seconds=15)
    return queue.get_workers()


@app.get("/api/recovered")
def list_recovered():
    jobs = queue.list_all_jobs()
    all_found = []
    for j in jobs:
        for f in queue.get_found(j["id"]):
            item = dict(f)
            item["job_name"] = j.get("name", "Job")
            item["analysis"] = analyze_password(f["plaintext"])
            all_found.append(item)
    all_found.sort(key=lambda x: x.get("cracked_at", ""), reverse=True)
    return all_found
