"""Test cafe-noir Cloudflare deployment with the new deploy_cleaner."""
import asyncio
import json
import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.deployment import DeploymentOrchestrator


async def main():
    orch = DeploymentOrchestrator()
    print("=" * 60)
    print("TESTING: cafe-noir-indiranagar -> Cloudflare")
    print("=" * 60)
    
    result = await orch.deploy_to_cloudflare(
        "uploads/cafe-noir-indiranagar",
        "cafe-noir-clean-test"
    )
    
    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
