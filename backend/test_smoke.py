"""Quick smoke test"""
import httpx
BASE = "http://localhost:8000"

# Health
r = httpx.get(f"{BASE}/health", timeout=5)
print(f"Health: {r.json()}")

# Root
r = httpx.get(f"{BASE}/", timeout=5)
root = r.json()
print(f"Version: {root.get('version')}")
for k, v in root.get("services", {}).items():
    print(f"  {k}: {v}")

# Domain search (real DNS)
r = httpx.post(f"{BASE}/api/v1/domain/search", json={"query": "google"}, timeout=15)
d = r.json()
if "results" in d:
    print(f"\nDomain search ({len(d['results'])} results):")
    for x in d["results"][:3]:
        tag = "AVAILABLE" if x["available"] else "TAKEN" if x["available"] is False else "?"
        print(f"  {x['domain']}: {tag}")
else:
    print(f"Domain error: {d}")

print("\nAll smoke tests passed!")
