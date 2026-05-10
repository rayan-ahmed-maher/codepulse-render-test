import asyncio
import json
import httpx

async def test_endpoint():
    print("Sending deploy request...")
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            "http://localhost:8000/deploy",
            json={
                "project_path": "uploads/codepulse-for-fly-io/untd-prjt/backend",
                "project_name": "codepulse-render-test-endpoint",
                "platform": "Render"
            }
        )
        print("Status:", resp.status_code)
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)

if __name__ == "__main__":
    asyncio.run(test_endpoint())
