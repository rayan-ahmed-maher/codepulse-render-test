import httpx, json
from core.config import settings

headers = {"Authorization": f"Bearer {settings.RENDER_API_KEY}"}
r = httpx.get("https://api.render.com/v1/owners?limit=10", headers=headers)
print("Status:", r.status_code)
print(json.dumps(r.json(), indent=2))
