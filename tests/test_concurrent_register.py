import threading
import requests

BASE_URL = "http://localhost:7000"
RESULTS = []
LOCK =  threading.Lock()

def register(thread_id: int):
    response = requests.post(
        f"{BASE_URL}/registry/register",
        json={
            "service_name": "payment-service",
            "host": "127.0.0.1",
            "port": 9002,
            "ttl": 30,
            "expected_version": 0
        }
    )
    with LOCK:
        RESULTS.append({
            "thread_id": thread_id,
            "status_code": response.status_code,
            "response": response.json()
        })
        print(f"Thread {thread_id} -> {response.status_code} | {response.json()}")

if __name__ == "__main__":
    threads = [threading.Thread(target=register, args=(i,)) for i in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    success = [r for r in RESULTS if r["status_code"] == 201]
    conflicts = [r for r in RESULTS if r["status_code"] == 409]

    print(f"\n--- Results ---")
    print(f"✅ Success (201): {len(success)}")
    print(f"⚔️  Conflicts (409): {len(conflicts)}")
    print(f"❌ Other: {len(RESULTS) - len(success) - len(conflicts)}")

    version_zero = [r for r in success if r["response"]["version"] == 0]
    assert len(version_zero) == 1, "Only one thread should create version 0"
    print("\n✅ Test passed — exactly one thread created the initial entry")
