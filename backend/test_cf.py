"""REAL Cloudflare deploy test: create project via API + deploy via wrangler"""
import subprocess
import os
import sys
import httpx
from pathlib import Path

# Load .env
env_file = Path(__file__).parent.parent / ".env"
env = {**os.environ}
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

token = env.get("CLOUDFLARE_API_TOKEN", "")
acct = env.get("CLOUDFLARE_ACCOUNT_ID", "")
if not token or not acct:
    print("Missing CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID")
    sys.exit(1)

project_name = "deployai-test"

# Step 1: Create project via REST API
print(f"Step 1: Creating Pages project '{project_name}'...")
r = httpx.post(
    f"https://api.cloudflare.com/client/v4/accounts/{acct}/pages/projects",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
    json={"name": project_name, "production_branch": "main"},
    timeout=15,
)
print(f"  HTTP {r.status_code}")
try:
    body = r.json()
    if r.status_code == 200:
        print(f"  Project created!")
    elif r.status_code == 409:
        print(f"  Project already exists (OK)")
    else:
        err = body.get("errors", [{}])
        print(f"  Response: {err}")
except:
    print(f"  Raw: {r.text[:200]}")

# Step 2: Create test files
abs_path = os.path.abspath("_test_cf")
os.makedirs(abs_path, exist_ok=True)
with open(os.path.join(abs_path, "index.html"), "w") as f:
    f.write("<html><head><title>DeployAI Test</title></head><body><h1>DeployAI CF Test</h1><p>Deployed automatically</p></body></html>")

# Step 3: Deploy via wrangler
print(f"\nStep 2: Deploying via wrangler...")
print(f"  CWD: {abs_path}")

cmd = (
    'cmd /c "npx wrangler pages deploy . '
    f'--project-name={project_name} '
    '--branch=main '
    '--commit-dirty=true"'
)

r = subprocess.run(
    cmd,
    shell=True,
    capture_output=True,
    timeout=120,
    env=env,
    cwd=abs_path,
)

stdout = r.stdout.decode("utf-8", errors="replace").strip() if r.stdout else ""
stderr = r.stderr.decode("utf-8", errors="replace").strip() if r.stderr else ""

with open("_test_cf_result.txt", "w", encoding="utf-8") as f:
    f.write(f"Exit: {r.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}\n")

print(f"  Exit: {r.returncode}")

# Safe print
safe = (stdout + "\n" + stderr).encode("ascii", errors="replace").decode()
for line in safe.split("\n"):
    if "pages.dev" in line.lower() or "error" in line.lower() or "success" in line.lower() or "deploy" in line.lower():
        print(f"  {line.strip()[:120]}")

if r.returncode == 0:
    # Extract URL
    import re
    urls = re.findall(r'https?://[^\s"\'<>]+\.pages\.dev[^\s"\'<>]*', stdout + stderr)
    if urls:
        print(f"\n  DEPLOYED: {urls[0]}")
    else:
        print(f"\n  DEPLOYED: https://{project_name}.pages.dev")
else:
    print(f"\n  FAILED (exit {r.returncode})")
    print(f"  See _test_cf_result.txt for details")
