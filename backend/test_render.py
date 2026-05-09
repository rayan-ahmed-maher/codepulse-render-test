"""Test Render deployment — creates GitHub repo + deploys to Render."""
import asyncio
import json
import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

from services.deployment import DeploymentOrchestrator


async def test_missing_api_key():
    """Test BUG 3 — missing RENDER_API_KEY returns structured error."""
    from core.config import settings
    original = settings.RENDER_API_KEY
    settings.RENDER_API_KEY = ""
    
    orch = DeploymentOrchestrator()
    result = await orch.deploy_to_render("test-proj", repo_url="https://github.com/test/test")
    
    print("\n=== TEST: Missing RENDER_API_KEY ===")
    print(json.dumps(result, indent=2))
    assert result["reason"] == "Render API key missing", f"Expected structured error, got: {result}"
    print("PASSED")
    
    settings.RENDER_API_KEY = original


async def test_missing_repo_url():
    """Test BUG 2 — missing repo_url returns structured error."""
    orch = DeploymentOrchestrator()
    result = await orch.deploy_to_render("test-proj", repo_url="", framework="fastapi")
    
    print("\n=== TEST: Missing repo URL ===")
    print(json.dumps(result, indent=2))
    assert result["reason"] == "Render requires GitHub integration", f"Expected structured error, got: {result}"
    print("PASSED")


async def main():
    await test_missing_api_key()
    await test_missing_repo_url()
    print("\n=== ALL RENDER TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
