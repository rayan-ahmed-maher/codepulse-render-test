"""
GitHub Push Service — Create repos and push local projects
============================================================
Uses GitHub REST API to create repos, then git CLI to push files.
This is more reliable than the API for large projects.
"""
import os
import re
import subprocess
import logging
import asyncio
from pathlib import Path
import httpx
from core.config import settings

logger = logging.getLogger(__name__)


class GitHubPushService:
    """Creates GitHub repos and pushes local project files."""

    def __init__(self):
        self.token = settings.GITHUB_TOKEN
        self.username = settings.GITHUB_USERNAME
        self.base_url = "https://api.github.com"

    @property
    def is_configured(self) -> bool:
        return bool(self.token and self.username)

    def _sanitize_repo_name(self, name: str) -> str:
        """Sanitize project name for GitHub repo naming."""
        name = name.lower().strip()
        name = re.sub(r'[^a-z0-9_.-]', '-', name)
        name = re.sub(r'-+', '-', name).strip('-')
        return name[:100] or "deployai-project"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def create_repo(self, project_name: str) -> dict:
        """Create a GitHub repo via REST API. Returns repo info."""
        if not self.is_configured:
            return {"error": "GITHUB_TOKEN or GITHUB_USERNAME not set in .env"}

        repo_name = self._sanitize_repo_name(project_name)
        logger.info(f"[GITHUB] Creating repo: {self.username}/{repo_name}")

        async with httpx.AsyncClient(timeout=30) as client:
            # Try to create
            resp = await client.post(
                f"{self.base_url}/user/repos",
                headers=self._headers(),
                json={
                    "name": repo_name,
                    "private": False,
                    "auto_init": False,
                    "description": "Deployed via DeployAI",
                },
            )

            if resp.status_code == 201:
                data = resp.json()
                logger.info(f"[GITHUB] Repo created: {data['html_url']}")
                return {
                    "status": "created",
                    "repo_url": data["html_url"],
                    "clone_url": data["clone_url"],
                    "name": repo_name,
                }

            if resp.status_code == 422:
                # Repo already exists — that's fine
                repo_url = f"https://github.com/{self.username}/{repo_name}"
                logger.info(f"[GITHUB] Repo already exists: {repo_url}")
                return {
                    "status": "exists",
                    "repo_url": repo_url,
                    "clone_url": f"{repo_url}.git",
                    "name": repo_name,
                }

            error_text = resp.text[:300]
            logger.error(f"[GITHUB] Create repo failed ({resp.status_code}): {error_text}")
            return {"error": f"GitHub API error ({resp.status_code}): {error_text}"}

    async def push_with_git(self, project_path: str, repo_name: str) -> dict:
        """Push project files to GitHub using git CLI (reliable for all project sizes)."""
        p = Path(project_path)
        if not p.exists():
            return {"error": f"Project path not found: {project_path}"}

        repo_url = f"https://{self.token}@github.com/{self.username}/{repo_name}.git"
        logger.info(f"[GITHUB] Pushing via git CLI: {project_path} → {self.username}/{repo_name}")

        try:
            # Run all git commands in sequence
            cmds = []

            # Check if .git already exists
            git_dir = p / ".git"
            if not git_dir.exists():
                cmds.append(["git", "init"])
                cmds.append(["git", "branch", "-M", "main"])

            # Always add remote (remove first if exists)
            cmds.append(["git", "remote", "remove", "origin"])  # May fail, that's OK
            cmds.append(["git", "remote", "add", "origin", repo_url])
            cmds.append(["git", "add", "-A"])
            cmds.append(["git", "commit", "-m", "Deploy via DeployAI", "--allow-empty"])
            cmds.append(["git", "push", "-u", "origin", "main", "--force"])

            for cmd in cmds:
                cmd_str = " ".join(cmd).replace(self.token, "***")
                logger.debug(f"[GITHUB] Running: {cmd_str}")

                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda c=cmd: subprocess.run(
                        c, cwd=str(project_path),
                        capture_output=True, text=True, timeout=120,
                        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                    )
                )

                # git remote remove may fail if remote doesn't exist — skip error
                if "remote remove" in " ".join(cmd) and result.returncode != 0:
                    continue

                if result.returncode != 0 and "push" in " ".join(cmd):
                    stderr = result.stderr[:500]
                    logger.error(f"[GITHUB] Push failed: {stderr}")
                    return {"error": f"Git push failed: {stderr}"}

                if result.returncode != 0 and "commit" in " ".join(cmd):
                    # Commit may fail if nothing to commit — OK
                    if "nothing to commit" in result.stdout + result.stderr:
                        continue
                    stderr = result.stderr[:300]
                    logger.warning(f"[GITHUB] Commit issue: {stderr}")

            public_url = f"https://github.com/{self.username}/{repo_name}"
            logger.info(f"[GITHUB] Push complete: {public_url}")
            return {
                "status": "pushed",
                "repo_url": public_url,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Git push timed out after 120 seconds"}
        except FileNotFoundError:
            return {"error": "Git is not installed. Please install git and try again."}
        except Exception as e:
            return {"error": f"Git push error: {str(e)}"}

    async def push_project(self, project_path: str, project_name: str) -> dict:
        """Complete flow: create repo → push via git → return repo URL."""
        if not self.is_configured:
            missing = []
            if not self.token:
                missing.append("GITHUB_TOKEN")
            if not self.username:
                missing.append("GITHUB_USERNAME")
            return {
                "error": f"Missing in .env: {', '.join(missing)}. "
                         f"Create a GitHub token at https://github.com/settings/tokens with 'repo' scope.",
            }

        # Step 1: Create repo on GitHub
        repo_result = await self.create_repo(project_name)
        if "error" in repo_result:
            return repo_result

        repo_name = repo_result["name"]

        # Step 2: Push files via git CLI
        push_result = await self.push_with_git(project_path, repo_name)
        if "error" in push_result:
            return push_result

        repo_url = f"https://github.com/{self.username}/{repo_name}"
        return {
            "status": "success",
            "repo_url": repo_url,
            "clone_url": f"{repo_url}.git",
            "full_name": f"{self.username}/{repo_name}",
        }


# Module-level singleton
github_push = GitHubPushService()
