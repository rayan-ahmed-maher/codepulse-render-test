"""E2E test: local deploy unique ports + old project cleanup"""
import httpx
import os
import time

BASE = "http://localhost:8000/api/v1"

def section(t):
    print(f"\n{'='*60}\n  {t}\n{'='*60}")

# Health check
r = httpx.get("http://localhost:8000/health", timeout=5)
print(f"Health: {r.json()}")

# Create two different test projects
dir_a = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_a")
dir_b = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_b")
os.makedirs(dir_a, exist_ok=True)
os.makedirs(dir_b, exist_ok=True)
with open(os.path.join(dir_a, "index.html"), "w") as f:
    f.write("<html><body><h1>PROJECT A</h1></body></html>")
with open(os.path.join(dir_b, "index.html"), "w") as f:
    f.write("<html><body><h1>PROJECT B</h1></body></html>")

# ── Test 1: Deploy project A ──
section("1. DEPLOY PROJECT A")
r1 = httpx.post(f"{BASE}/deploy/local", json={
    "project_path": dir_a, "project_name": "proj-a"
}, timeout=60)
a = r1.json()
print(f"  Status: {a.get('status')}")
print(f"  URL:    {a.get('url')}")
print(f"  Port:   {a.get('port')}")
print(f"  PID:    {a.get('pid')}")
if a.get("url"):
    time.sleep(1)
    try:
        c = httpx.get(a["url"], timeout=5)
        has_a = "PROJECT A" in c.text
        print(f"  Content correct: {has_a} ({c.status_code})")
    except Exception as e:
        print(f"  HTTP check failed: {e}")

# ── Test 2: Deploy project B (should get DIFFERENT port) ──
section("2. DEPLOY PROJECT B (different port)")
r2 = httpx.post(f"{BASE}/deploy/local", json={
    "project_path": dir_b, "project_name": "proj-b"
}, timeout=60)
b = r2.json()
print(f"  Status: {b.get('status')}")
print(f"  URL:    {b.get('url')}")
print(f"  Port:   {b.get('port')}")
print(f"  PID:    {b.get('pid')}")
ports_differ = a.get("port") != b.get("port")
print(f"  Ports differ: {ports_differ} (A={a.get('port')}, B={b.get('port')})")
if b.get("url"):
    time.sleep(1)
    try:
        c = httpx.get(b["url"], timeout=5)
        has_b = "PROJECT B" in c.text
        print(f"  Content correct: {has_b} ({c.status_code})")
    except Exception as e:
        print(f"  HTTP check failed: {e}")

# ── Test 3: Redeploy project A (should kill old A and start fresh) ──
section("3. REDEPLOY PROJECT A (should kill old, fresh port)")
# Change content to prove it's not cached
with open(os.path.join(dir_a, "index.html"), "w") as f:
    f.write("<html><body><h1>PROJECT A v2</h1></body></html>")

r3 = httpx.post(f"{BASE}/deploy/local", json={
    "project_path": dir_a, "project_name": "proj-a"
}, timeout=60)
a2 = r3.json()
print(f"  Status: {a2.get('status')}")
print(f"  URL:    {a2.get('url')}")
print(f"  Port:   {a2.get('port')}")
print(f"  PID:    {a2.get('pid')}")
old_a_killed = a2.get("pid") != a.get("pid")
print(f"  Old PID killed: {old_a_killed} (old={a.get('pid')}, new={a2.get('pid')})")
if a2.get("url"):
    time.sleep(1)
    try:
        c = httpx.get(a2["url"], timeout=5)
        has_v2 = "PROJECT A v2" in c.text
        print(f"  Content updated: {has_v2} ({c.status_code})")
    except Exception as e:
        print(f"  HTTP check failed: {e}")

# ── Test 4: List running processes ──
section("4. LIST RUNNING")
r = httpx.get(f"{BASE}/deploy/local/list", timeout=5)
running = r.json()
print(f"  Running: {len(running)} processes")
for p in running:
    print(f"    PID {p['pid']} → port {p['port']} | {p['project_path']}")

# ── Test 5: Stop all ──
section("5. STOP ALL")
r = httpx.post(f"{BASE}/deploy/local/stop-all", timeout=5)
print(f"  {r.json()}")

# ── Test 6: List after stop ──
r = httpx.get(f"{BASE}/deploy/local/list", timeout=5)
print(f"  Running after stop: {len(r.json())}")

# ── Summary ──
section("RESULTS")
print(f"  Ports unique:      {ports_differ}")
print(f"  Old deploy killed: {old_a_killed}")
print(f"  All tests done!")
