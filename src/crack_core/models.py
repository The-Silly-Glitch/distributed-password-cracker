from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utc_now():
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False, default="Crack Job")
    algorithm = Column(String(32), nullable=False)  # md5, sha1, sha256, bcrypt
    attack_type = Column(String(32), nullable=False, default="hybrid")  # dictionary, brute_force, pattern, ruleset, hybrid
    target_hashes = Column(JSON, nullable=False)  # list of target hex strings
    priority = Column(Integer, default=5)  # 1 (low) to 10 (high)
    status = Column(String(32), default="queued")  # queued, in_progress, completed, failed, cancelled
    total_candidates = Column(Integer, default=0)
    evaluated_candidates = Column(Integer, default=0)
    parameters = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "algorithm": self.algorithm,
            "attack_type": self.attack_type,
            "target_hashes": self.target_hashes,
            "priority": self.priority,
            "status": self.status,
            "total_candidates": self.total_candidates,
            "evaluated_candidates": self.evaluated_candidates,
            "parameters": self.parameters or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Worker(Base):
    __tablename__ = "workers"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    gpu_name = Column(String(128), default="CPU")
    device_count = Column(Integer, default=0)
    hashrate = Column(Float, default=0.0)  # hashes/sec
    status = Column(String(32), default="idle")  # idle, busy, offline
    current_job_id = Column(String(64), nullable=True)
    current_range = Column(String(128), nullable=True)
    temperature_c = Column(Integer, nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), default=utc_now)
    registered_at = Column(DateTime(timezone=True), default=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "gpu_name": self.gpu_name,
            "device_count": self.device_count,
            "hashrate": self.hashrate,
            "status": self.status,
            "current_job_id": self.current_job_id,
            "current_range": self.current_range,
            "temperature_c": self.temperature_c,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
        }


class RecoveredPassword(Base):
    __tablename__ = "recovered_passwords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), nullable=False, index=True)
    worker_id = Column(String(64), nullable=False)
    hash_val = Column(String(256), nullable=False, index=True)
    algorithm = Column(String(32), nullable=False)
    plaintext = Column(String(256), nullable=False)
    cracked_at = Column(DateTime(timezone=True), default=utc_now)
    time_taken_seconds = Column(Float, default=0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "worker_id": self.worker_id,
            "hash_val": self.hash_val,
            "algorithm": self.algorithm,
            "plaintext": self.plaintext,
            "cracked_at": self.cracked_at.isoformat() if self.cracked_at else None,
            "time_taken_seconds": self.time_taken_seconds,
        }


class HashMetadata(Base):
    __tablename__ = "hash_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hash_val = Column(String(256), unique=True, nullable=False, index=True)
    algorithm = Column(String(32), nullable=False)
    salt = Column(String(128), nullable=True)
    format_info = Column(String(128), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "hash_val": self.hash_val,
            "algorithm": self.algorithm,
            "salt": self.salt,
            "format_info": self.format_info,
        }
