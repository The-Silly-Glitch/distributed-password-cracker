from crack_core.db import get_session, init_db
from crack_core.models import Job, Worker, RecoveredPassword
from crack_core.analyzer import calculate_entropy, analyze_password
from crack_core.reporter import generate_report


def test_db_persistence():
    init_db()
    with get_session() as session:
        job = Job(
            id="job-unit-test",
            name="Unit Test Job",
            algorithm="sha256",
            attack_type="dictionary",
            target_hashes=["test_hash_val"],
            priority=8
        )
        session.merge(job)

        rec = RecoveredPassword(
            job_id="job-unit-test",
            worker_id="worker-unit-test",
            hash_val="test_hash_val",
            algorithm="sha256",
            plaintext="secret123",
            time_taken_seconds=0.45
        )
        session.add(rec)

    with get_session() as session:
        saved_job = session.query(Job).filter(Job.id == "job-unit-test").first()
        assert saved_job is not None
        assert saved_job.priority == 8

        saved_rec = session.query(RecoveredPassword).filter(RecoveredPassword.job_id == "job-unit-test").first()
        assert saved_rec is not None
        assert saved_rec.plaintext == "secret123"


def test_analyzer_entropy_and_scoring():
    weak = analyze_password("123456")
    assert weak["rating"] == "Very Weak"
    assert weak["entropy_bits"] < 25.0
    assert len(weak["policy_violations"]) > 0

    strong = analyze_password("CorrectHorseBatteryStaple2026!#")
    assert strong["rating"] in ["Strong", "Very Strong"]
    assert strong["entropy_bits"] > 80.0


def test_report_generator():
    report = generate_report(job_id="job-unit-test")
    assert "DISTRIBUTED PASSWORD AUDIT" in report
    assert "secret123" in report
    assert "DEFENSIVE SECURITY RECOMMENDATIONS" in report
