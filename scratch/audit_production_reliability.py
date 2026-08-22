import time
import requests
import statistics
import json

RENDER_URL = "https://nyaysetu-backend-nwp2.onrender.com"

endpoints = [
    ("/api/health", "GET", None),
    ("/api/catalog/districts", "GET", None),
    ("/api/catalog/talukas?district_id=ahmedabad", "GET", None),
    ("/api/catalog/courts?district_id=ahmedabad", "GET", None),
    ("/api/catalog/case-types", "GET", None),
    ("/api/catalog/case-forms", "GET", None),
    ("/api/templates", "GET", None),
    ("/api/catalog/plans", "GET", None),
]

print("==================================================")
print("PART 2 & 3: PRODUCTION BACKEND LATENCY MEASUREMENT")
print(f"Target: {RENDER_URL}")
print("==================================================")

results = {}

for path, method, body in endpoints:
    url = f"{RENDER_URL}{path}"
    timings = []
    statuses = []
    
    # 1 cold probe
    t0 = time.time()
    try:
        r = requests.get(url, timeout=30)
        cold_time = (time.time() - t0) * 1000
        cold_status = r.status_code
    except Exception as e:
        cold_time = (time.time() - t0) * 1000
        cold_status = str(e)
    
    # 10 warm probes
    for i in range(10):
        t0 = time.time()
        try:
            r = requests.get(url, timeout=30)
            elapsed = (time.time() - t0) * 1000
            timings.append(elapsed)
            statuses.append(r.status_code)
        except Exception as e:
            timings.append((time.time() - t0) * 1000)
            statuses.append(f"ERR: {e}")
        time.sleep(0.1)
    
    valid_timings = [t for t, s in zip(timings, statuses) if isinstance(s, int) and s == 200]
    
    results[path] = {
        "cold_ms": round(cold_time, 1),
        "cold_status": cold_status,
        "warm_min_ms": round(min(valid_timings), 1) if valid_timings else None,
        "warm_max_ms": round(max(valid_timings), 1) if valid_timings else None,
        "warm_avg_ms": round(statistics.mean(valid_timings), 1) if valid_timings else None,
        "success_rate": f"{len(valid_timings)}/10",
        "sample_size_bytes": len(r.content) if 'r' in locals() and hasattr(r, 'content') else 0
    }
    print(f"\nEndpoint: {path}")
    print(f"  Cold latency: {results[path]['cold_ms']} ms (Status: {results[path]['cold_status']})")
    if valid_timings:
        print(f"  Warm min/max/avg: {results[path]['warm_min_ms']} ms / {results[path]['warm_max_ms']} ms / {results[path]['warm_avg_ms']} ms")
        print(f"  Success rate: {results[path]['success_rate']}, Payload size: {results[path]['sample_size_bytes']} bytes")
    else:
        print(f"  FAILED: Statuses = {statuses}")

with open("scratch/latency_report.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
