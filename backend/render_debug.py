import httpx, json
from core.config import settings

headers = {
    "Authorization": f"Bearer {settings.RENDER_API_KEY}",
    "Content-Type": "application/json"
}

r = httpx.get("https://api.render.com/v1/services?limit=3", headers=headers)
print("Status:", r.status_code)
print(json.dumps(r.json(), indent=2))
