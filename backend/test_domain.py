"""Test domain search API"""
import httpx
import time

start = time.time()
r = httpx.post("http://localhost:8000/api/v1/domain/search", json={"query": "google"}, timeout=15)
elapsed = time.time() - start
print(f"Domain search took {elapsed:.1f}s")
data = r.json()

if "error" in data:
    print(f"ERROR: {data['error']}")
else:
    print(f"Source: {data.get('source')}")
    for x in data.get("results", []):
        status = "AVAILABLE" if x["available"] else ("TAKEN" if x["available"] is False else "UNKNOWN")
        print(f"  {x['domain']}: {status} | {x['registrar']}")
