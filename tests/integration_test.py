import time
import httpx

INGEST_URL = "http://localhost:3000/ingest"
INCIDENTS_URL = "http://localhost:3000/incidents"

payload = {"component_id": "TEST_COMP_01", "severity": "critical", "message": "integration test"}

with httpx.Client() as client:
    print("Posting ingest...")
    r = client.post(INGEST_URL, json=payload, timeout=10)
    r.raise_for_status()
    print("Posted, polling for incident...")

    deadline = time.time() + 30
    found = False
    while time.time() < deadline:
        res = client.get(INCIDENTS_URL, timeout=10)
        res.raise_for_status()
        incidents = res.json()
        for inc in incidents:
            if inc.get("component_id") == payload["component_id"]:
                print("Found incident:", inc)
                found = True
                break
        if found:
            break
        time.sleep(2)

    if not found:
        raise SystemExit("Integration test failed: incident not found within timeout")
    print("Integration test passed")
