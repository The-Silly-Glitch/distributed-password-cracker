from fastapi.testclient import TestClient
from crack_dashboard.app import app

client = TestClient(app)


def test_index_route():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Distributed GPU Cracker" in resp.text


def test_status_api():
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_workers" in data
    assert "total_hashrate" in data


def test_jobs_api_crud():
    # Submit job
    payload = {
        "name": "API Test Job",
        "algorithm": "md5",
        "target_hashes": ["5d41402abc4b2a76b9719d911017c592"],
        "attack_type": "dictionary",
        "priority": 9
    }
    resp = client.post("/api/jobs", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # List jobs
    list_resp = client.get("/api/jobs")
    assert list_resp.status_code == 200
    jobs = list_resp.json()
    found = next((j for j in jobs if j["id"] == job_id), None)
    assert found is not None
    assert found["priority"] == 9

    # Detail job
    detail_resp = client.get(f"/api/jobs/{job_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["job"]["id"] == job_id
