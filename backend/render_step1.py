import httpx, json
from core.config import settings

headers = {
    "Authorization": f"Bearer {settings.RENDER_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "type": "web_service",
    "name": "test-deployai-service",
    "ownerId": "tea-d7qbf068bjmc73c1dutg",
    "repo": "https://github.com/rayan-ahmed-maher/codepulse-render-test",
    "branch": "main",
    "buildCommand": "pip install -r requirements.txt",
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port 10000",
    "plan": "free",
    "region": "oregon",
    "envVars": []
}

r = httpx.post("https://api.render.com/v1/services", headers=headers, json=payload)
print("Status:", r.status_code)
print(json.dumps(r.json(), indent=2))
