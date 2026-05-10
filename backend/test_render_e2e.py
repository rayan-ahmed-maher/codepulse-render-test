"""Test REAL Render deployment with codepulse FastAPI project."""
import asyncio
import json
import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

from services.github_push import github_push
from services.deployment import DeploymentOrchestrator


async def main():
    project_path = "uploads/codepulse-for-fly-io/untd-prjt/backend"
    project_name = "codepulse-render-test"
    framework = "fastapi"

    # -- PRE-DEPLOYMENT STEPS (replicated from deploy route) --
    print("\n" + "=" * 60)
    print("STEP 0: Pre-deployment files generation")
    print("=" * 60)
    
    from pathlib import Path
    import subprocess
    proj_path = Path(project_path)
    
    # 1. runtime.txt
    runtime_path = proj_path / "runtime.txt"
    if not runtime_path.exists():
        runtime_path.write_text("python-3.11.0")
        print("Generated runtime.txt")
        
    # 2. render.yaml
    render_yaml_path = proj_path / "render.yaml"
    render_yaml = f"""services:
  - type: web
    name: {project_name}
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
"""
    render_yaml_path.write_text(render_yaml)
    print("Generated render.yaml")
    
    # 3. requirements.txt
    req_file = proj_path / "requirements.txt"
    if not req_file.exists():
        print("Missing requirements.txt, auto-generating with pipreqs...")
        subprocess.run(f'pip install pipreqs && pipreqs "{proj_path}" --force', shell=True)
    else:
        print("requirements.txt already exists, keeping it.")

    print("\n" + "=" * 60)
    print(f"STEP 1: Push to GitHub")
    print("=" * 60)

    if not github_push.is_configured:
        print("ERROR: GITHUB_TOKEN or GITHUB_USERNAME not set")
        return

    github_result = await github_push.push_project(project_path, project_name)
    print(json.dumps(github_result, indent=2, default=str))

    if "error" in github_result:
        print(f"FAILED: {github_result['error']}")
        return

    repo_url = github_result["repo_url"]
    print(f"\nGitHub repo: {repo_url}")

    print("\n" + "=" * 60)
    print(f"STEP 2: Deploy to Render")
    print("=" * 60)

    orch = DeploymentOrchestrator()
    result = await orch.deploy_to_render(
        project_name=project_name,
        repo_url=repo_url,
        framework=framework,
    )

    print("\n" + "=" * 60)
    print("RENDER RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
