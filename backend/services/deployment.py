"""
Deployment Orchestrator — Vercel, Netlify, Cloudflare, Render
"""

import os
import io
import re
import base64
import zipfile
import asyncio
import logging
import mimetypes

from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict

import httpx

from core.config import settings


logger = logging.getLogger(__name__)


# =========================================================
# DATA CLASSES
# =========================================================

@dataclass
class PlatformRecommendation:
    platform: str
    confidence: int
    reason: str


@dataclass
class CostComparison:
    platform: str
    free_tier: Dict[str, str]
    pro_tier: Dict[str, str]
    pro_price: str


# =========================================================
# PLATFORM RECOMMENDATIONS
# =========================================================

PLATFORM_MAP = {
    "nextjs": [
        PlatformRecommendation(
            "Vercel",
            99,
            "Vercel is the creator of Next.js — native support",
        ),
        PlatformRecommendation(
            "Netlify",
            85,
            "Good Next.js support with edge functions",
        ),
    ],

    "react": [
        PlatformRecommendation(
            "Vercel",
            95,
            "Excellent React/Vite support with Edge Functions",
        ),
        PlatformRecommendation(
            "Netlify",
            90,
            "Great CI/CD and form handling",
        ),
        PlatformRecommendation(
            "Cloudflare",
            85,
            "Unlimited free bandwidth",
        ),
    ],

    "vue": [
        PlatformRecommendation(
            "Netlify",
            92,
            "Best Vue ecosystem support",
        ),
        PlatformRecommendation(
            "Vercel",
            88,
            "Fast edge deploys",
        ),
    ],

    "vite": [
        PlatformRecommendation(
            "Vercel",
            93,
            "Native Vite framework support",
        ),
        PlatformRecommendation(
            "Netlify",
            89,
            "Excellent static + SPA hosting",
        ),
        PlatformRecommendation(
            "Cloudflare",
            86,
            "Unlimited bandwidth on free tier",
        ),
    ],

    "static": [
        PlatformRecommendation(
            "Cloudflare",
            95,
            "Unlimited bandwidth on free tier",
        ),
        PlatformRecommendation(
            "Netlify",
            90,
            "Easy drag-and-drop deploy",
        ),
        PlatformRecommendation(
            "Vercel",
            85,
            "Global CDN",
        ),
    ],

    "fastapi": [
        PlatformRecommendation(
            "Render",
            95,
            "Best free Python hosting with auto-deploy",
        ),
        PlatformRecommendation(
            "Vercel",
            75,
            "Serverless Python support (limited)",
        ),
    ],

    "flask": [
        PlatformRecommendation(
            "Render",
            94,
            "Free Python web service hosting",
        ),
        PlatformRecommendation(
            "Vercel",
            70,
            "Serverless Python (cold starts)",
        ),
    ],

    "django": [
        PlatformRecommendation(
            "Render",
            96,
            "Free PostgreSQL + Python hosting",
        ),
        PlatformRecommendation(
            "Vercel",
            60,
            "Limited Django support",
        ),
    ],

    "nodejs": [
        PlatformRecommendation(
            "Vercel",
            90,
            "Native Node.js serverless",
        ),
        PlatformRecommendation(
            "Render",
            88,
            "Full Node.js web service",
        ),
        PlatformRecommendation(
            "Netlify",
            82,
            "Netlify Functions for Node",
        ),
    ],

    "python": [
        PlatformRecommendation(
            "Render",
            92,
            "Best general Python hosting",
        ),
    ],

    "angular": [
        PlatformRecommendation(
            "Vercel",
            90,
            "Excellent Angular support",
        ),
        PlatformRecommendation(
            "Netlify",
            88,
            "Great for Angular SPAs",
        ),
        PlatformRecommendation(
            "Cloudflare",
            85,
            "Unlimited bandwidth",
        ),
    ],
}


# =========================================================
# COST TABLE
# =========================================================

COST_TABLE = {
    "Vercel": CostComparison(
        "Vercel",
        {
            "Bandwidth": "100GB",
            "Builds": "6000 min",
            "Serverless": "100GB-hrs",
            "Domains": "*.vercel.app",
        },
        {
            "Bandwidth": "1TB",
            "Builds": "Unlimited",
            "Serverless": "1000GB-hrs",
            "Domains": "Custom + SSL",
        },
        "$20/mo",
    ),

    "Netlify": CostComparison(
        "Netlify",
        {
            "Bandwidth": "100GB",
            "Builds": "300 min",
            "Forms": "100/mo",
            "Identity": "1000 users",
        },
        {
            "Bandwidth": "1TB",
            "Builds": "Unlimited",
            "Forms": "Unlimited",
            "Identity": "Unlimited",
        },
        "$19/mo",
    ),

    "Cloudflare": CostComparison(
        "Cloudflare",
        {
            "Bandwidth": "Unlimited",
            "Builds": "500/mo",
            "Workers": "100K req/day",
            "KV": "1GB",
        },
        {
            "Bandwidth": "Unlimited",
            "Builds": "5000/mo",
            "Workers": "10M req/mo",
            "KV": "25GB",
        },
        "$5/mo",
    ),

    "Render": CostComparison(
        "Render",
        {
            "Bandwidth": "100GB",
            "Builds": "Unlimited",
            "RAM": "512MB",
            "Auto-Deploy": "Yes",
        },
        {
            "Bandwidth": "Unlimited",
            "Builds": "Unlimited",
            "RAM": "2GB+",
            "Auto-Deploy": "Yes",
        },
        "$7/mo",
    ),
}


# =========================================================
# FRAMEWORK CONFIGS
# =========================================================

FRAMEWORK_CONFIGS = {
    "react": {
        "install": "npm install",
        "build": "npm run build",
        "output": "build",
    },

    "vite": {
        "install": "npm install",
        "build": "npm run build",
        "output": "dist",
    },

    "vue": {
        "install": "npm install",
        "build": "npm run build",
        "output": "dist",
    },

    "nextjs": {
        "install": "npm install",
        "build": "next build",
        "output": ".next",
    },

    "angular": {
        "install": "npm install",
        "build": "ng build",
        "output": "dist",
    },

    "static": {
        "install": None,
        "build": None,
        "output": ".",
    },

    "fastapi": {
        "install": "pip install -r requirements.txt",
        "build": None,
        "output": None,
    },

    "flask": {
        "install": "pip install -r requirements.txt",
        "build": None,
        "output": None,
    },

    "django": {
        "install": "pip install -r requirements.txt",
        "build": None,
        "output": None,
    },
}


# =========================================================
# DEPLOYMENT ORCHESTRATOR
# =========================================================

class DeploymentOrchestrator:

    def __init__(self):
        self.http = httpx.AsyncClient(timeout=60)

    # =====================================================
    # UTILITIES
    # =====================================================
    # HELPERS
    # =====================================================

    def _refine_project_path(self, path: str, framework: str) -> str:
        """Refine path to only deploy build artifacts if they exist (Vite dist, Next out, etc)."""
        p = Path(path).resolve()
        
        # ── SAFETY: Prevent deploying system root or parent 'uploads' folder ──
        # If we are at the root of 'uploads', we MUST look deeper.
        if p.name == "uploads":
            logger.warning("[DEPLOY] project_path is 'uploads' root. Attempting to narrow down...")
            subdirs = [d for d in p.iterdir() if d.is_dir()]
            if len(subdirs) == 1:
                p = subdirs[0]
                logger.info(f"[DEPLOY] Narrowed down uploads root to: {p.name}")

        # ── VITE / REACT / VUE: dist/ or build/ ──
        if framework in ("react", "vite", "vue", "frontend"):
            for d in ["dist", "build"]:
                if (p / d).exists() and (p / d).is_dir():
                    logger.info(f"[DEPLOY] Refined path to build artifact: {d}/")
                    return str(p / d)
                    
        # ── NEXT.JS: out/ ──
        elif framework == "nextjs":
            if (p / "out").exists() and (p / "out").is_dir():
                logger.info(f"[DEPLOY] Refined path to Next.js output: out/")
                return str(p / "out")
                
        # ── STATIC: Ensure we are at index.html folder ──
        elif framework == "static":
            if not (p / "index.html").exists():
                # Search one level deep for index.html
                for d in p.iterdir():
                    if d.is_dir() and (d / (p.name if p.name != "uploads" else "") / "index.html").exists():
                         pass # keep logic simple
                    if d.is_dir() and (d / "index.html").exists():
                        logger.info(f"[DEPLOY] Refined static path to subfolder: {d.name}/")
                        return str(d)
                        
        return str(p)

    @staticmethod
    def sanitize_name(name: str) -> str:
        """
        Sanitize project name for deployment platforms.
        """

        name = name.lower().strip()

        name = re.sub(
            r"[^a-z0-9\-]",
            "-",
            name,
        )

        name = re.sub(
            r"-+",
            "-",
            name,
        ).strip("-")

        return name[:100] or "project"

    def recommend(
        self,
        framework: str
    ) -> List[PlatformRecommendation]:

        return PLATFORM_MAP.get(
            framework,
            PLATFORM_MAP["static"]
        )

    def get_costs(
        self,
        platform: str
    ) -> Optional[CostComparison]:

        return COST_TABLE.get(platform)

    # =====================================================
    # VERCEL DEPLOYMENT
    # =====================================================

    async def deploy_to_vercel(
        self,
        project_path: str,
        project_name: str,
        framework: str = "static"
    ) -> dict:

        if not settings.has_vercel:
            return {
                "status": "error",
                "message": "VERCEL_TOKEN not set",
            }

        print("VERCEL DEPLOY PATH:", project_path)

        project_root = Path(__file__).resolve().parents[2]
        resolved_project_path = Path(project_path).resolve()
        path_lower = str(resolved_project_path).lower()
        root_name = project_root.name.lower()

        if (
            "deployai" in path_lower
            or resolved_project_path == project_root
            or resolved_project_path.name.lower() == root_name
        ):
            return {
                "status": "error",
                "error": "INVALID_DEPLOY_PATH",
                "message": f"Invalid Vercel deploy path: {project_path}",
            }

        if not resolved_project_path.is_dir():
            return {
                "status": "error",
                "error": "INVALID_DEPLOY_PATH",
                "message": (
                    f"Project directory not found: "
                    f"{project_path}"
                ),
            }

        normalized_framework = (framework or "static").lower()
        is_frontend = normalized_framework in {
            "vite",
            "react",
            "next",
            "nextjs",
            "frontend",
        }
        build_dir_names = {"dist", "build"}
        source_project_path = resolved_project_path
        prebuilt_deploy_path = None

        if resolved_project_path.name.lower() in build_dir_names:
            parent_path = resolved_project_path.parent
            if (parent_path / "package.json").is_file():
                source_project_path = parent_path
            else:
                prebuilt_deploy_path = resolved_project_path
                is_frontend = False

        def _package_name(path: Path) -> str:
            try:
                import json

                pkg_path = path / "package.json"
                if not pkg_path.is_file():
                    return ""

                with open(pkg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                return str(data.get("name") or "")
            except Exception:
                return ""

        def _html_title(path: Path) -> str:
            try:
                index_path = path / "index.html"
                if not index_path.is_file():
                    return ""

                with open(index_path, "r", encoding="utf-8", errors="ignore") as f:
                    html = f.read(20000)

                match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
                if not match:
                    return ""

                return re.sub(r"\s+", " ", match.group(1)).strip()
            except Exception:
                return ""

        project_name = self.sanitize_name(project_name)
        if (
            project_name in build_dir_names
            or any(project_name.startswith(f"{name}-") for name in build_dir_names)
        ):
            deploy_name_source = (
                _package_name(source_project_path)
                or _html_title(prebuilt_deploy_path or source_project_path)
                or source_project_path.name
            )
            sanitized_source_name = self.sanitize_name(deploy_name_source)
            if (
                sanitized_source_name in build_dir_names
                or any(sanitized_source_name.startswith(f"{name}-") for name in build_dir_names)
            ):
                deploy_name_source = "site"

            project_name = self.sanitize_name(deploy_name_source)
        
        try:
            if is_frontend:
                vercel_config_path = source_project_path / "vercel.json"
                if not vercel_config_path.exists():
                    import json

                    with open(vercel_config_path, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "buildCommand": "npm run build",
                                "outputDirectory": "dist",
                                "framework": "vite",
                            },
                            f,
                            indent=2,
                        )
                        f.write("\n")

                import subprocess as _sp

                def _run_npm(args):
                    return _sp.run(
                        args,
                        cwd=str(source_project_path),
                        capture_output=True,
                        text=True,
                        timeout=300,
                        encoding="utf-8",
                        errors="replace",
                    )

                install_result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: _run_npm(["npm", "install"]),
                )

                if install_result.returncode != 0:
                    return {
                        "status": "error",
                        "error": "BUILD_FAILED",
                        "message": "npm install failed before Vercel deployment",
                        "raw": {
                            "stdout": install_result.stdout[-2000:],
                            "stderr": install_result.stderr[-2000:],
                        },
                    }

                build_result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: _run_npm(["npm", "run", "build"]),
                )

                if build_result.returncode != 0:
                    return {
                        "status": "error",
                        "error": "BUILD_FAILED",
                        "message": "npm run build failed before Vercel deployment",
                        "raw": {
                            "stdout": build_result.stdout[-2000:],
                            "stderr": build_result.stderr[-2000:],
                        },
                    }

                dist_path = source_project_path / "dist"
                if not dist_path.is_dir():
                    return {
                        "status": "error",
                        "error": "BUILD_FAILED",
                        "message": f"Build completed but dist folder is missing: {dist_path}",
                    }

                deploy_path = dist_path
            else:
                deploy_path = prebuilt_deploy_path or resolved_project_path

            if not deploy_path.is_dir():
                return {
                    "status": "error",
                    "error": "INVALID_DEPLOY_PATH",
                    "message": f"Vercel deploy directory not found: {deploy_path}",
                }

            excluded_dirs = {"node_modules", ".git", "__pycache__", ".next", ".venv"}
            deploy_files = [
                item
                for item in deploy_path.rglob("*")
                if item.is_file()
                and not any(part in excluded_dirs for part in item.parts)
            ]

            if not deploy_files:
                return {
                    "status": "error",
                    "error": "INVALID_DEPLOY_PATH",
                    "message": f"Vercel deploy directory is empty: {deploy_path}",
                }

            max_hobby_upload_bytes = 100 * 1024 * 1024
            oversized_files = [
                item
                for item in deploy_files
                if item.stat().st_size > max_hobby_upload_bytes
            ]
            if oversized_files:
                largest = max(
                    oversized_files,
                    key=lambda item: item.stat().st_size,
                )
                rel = largest.relative_to(deploy_path).as_posix()
                size_mb = largest.stat().st_size / (1024 * 1024)
                return {
                    "status": "error",
                    "error": "VERCEL_FILE_TOO_LARGE",
                    "message": (
                        f"Vercel rejected this deployment because '{rel}' is "
                        f"{size_mb:.1f} MB. Vercel Hobby static uploads are "
                        "limited to 100 MB. Compress this file, host it on "
                        "external storage, or use a smaller asset before "
                        "deploying to Vercel."
                    ),
                }

            total_upload_bytes = sum(item.stat().st_size for item in deploy_files)
            if total_upload_bytes > max_hobby_upload_bytes:
                total_mb = total_upload_bytes / (1024 * 1024)
                return {
                    "status": "error",
                    "error": "VERCEL_DEPLOY_TOO_LARGE",
                    "message": (
                        f"Vercel rejected this deployment because the upload is "
                        f"{total_mb:.1f} MB. Vercel Hobby static/source uploads "
                        "are limited to 100 MB. Remove or compress large assets "
                        "before deploying to Vercel."
                    ),
                }

            logger.info(
                f"[VERCEL] Uploading {len(deploy_files)} files "
                f"({total_upload_bytes / (1024 * 1024):.1f} MB) "
                f"from {deploy_path}"
            )

            files = []
            for root, dirs, fnames in os.walk(deploy_path):
                dirs[:] = [d for d in dirs if d not in excluded_dirs]
                for fn in fnames:
                    fp = os.path.join(root, fn)
                    rel = os.path.relpath(fp, deploy_path).replace("\\", "/")

                    content_type, _ = mimetypes.guess_type(fp)
                    is_text_file = (
                        (content_type or "").startswith("text/")
                        or Path(fp).suffix.lower() in {
                            ".html",
                            ".htm",
                            ".css",
                            ".js",
                            ".mjs",
                            ".cjs",
                            ".json",
                            ".svg",
                            ".xml",
                            ".txt",
                            ".md",
                            ".map",
                            ".webmanifest",
                        }
                    )

                    if is_text_file:
                        try:
                            with open(fp, "r", encoding="utf-8") as f:
                                files.append({
                                    "file": rel,
                                    "data": f.read(),
                                    "encoding": "utf-8",
                                })
                            continue
                        except UnicodeDecodeError:
                            pass

                    with open(fp, "rb") as f:
                        data = base64.b64encode(f.read()).decode()

                    files.append({
                        "file": rel,
                        "data": data,
                        "encoding": "base64",
                    })

            # ── VERCEL PROJECT ISOLATION ──
            # Use the requested platform project name so the public alias matches it.
            unique_name = project_name
            
            payload = {
                "name": unique_name,
                "project": unique_name,
                "files": files,
                "target": "production",
                "projectSettings": {
                    "framework": None,
                    "installCommand": None,
                    "buildCommand": None,
                    "outputDirectory": ".",
                    "rootDirectory": None,
                },
            }

            logger.info(
                f"[VERCEL] Deploying "
                f"{project_name} "
                f"framework={framework} "
                f"from={deploy_path}"
            )

            resp = await self.http.post(
                "https://api.vercel.com/v13/deployments",
                headers={
                    "Authorization": (
                        f"Bearer {settings.VERCEL_TOKEN}"
                    ),
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            result = resp.json()

            if resp.status_code >= 300:

                logger.error(
                    f"[VERCEL ERROR] "
                    f"status={resp.status_code} "
                    f"response={result}"
                )

                return {
                    "status": "error",
                    "error": "VERCEL_PROJECT_ERROR",
                    "message": result.get("error", {}).get("message", "Vercel deployment failed"),
                    "raw": result,
                }

            # ── CLEAN RESULT FORMAT ──
            deployment_host = result.get("url", "")
            aliases = result.get("alias") or result.get("aliases") or result.get("userAliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]

            deploy_host = ""
            for alias in aliases:
                if alias and alias != deployment_host:
                    deploy_host = alias
                    break

            deploy_url = deploy_host or f"{unique_name}.vercel.app"
            if deploy_url and not deploy_url.startswith("http"):
                deploy_url = f"https://{deploy_url}"

            return {
                "platform": "vercel",
                "url": deploy_url,
                "project_name": unique_name,
                "status": "success"
            }

        except Exception as e:

            logger.exception(
                "[VERCEL DEPLOY FAILED]"
            )

            return {
                "status": "error",
                "error": "VERCEL_PROJECT_ERROR",
                "message": str(e),
            }

    # =====================================================
    # NETLIFY DEPLOYMENT
    # =====================================================

    async def deploy_to_netlify(
        self,
        project_path: str,
        site_name: str = ""
    ) -> dict:

        if not settings.has_netlify:
            return {
                "status": "error",
                "message": "NETLIFY_TOKEN not set. Add it to your .env file.",
            }

        if not os.path.isdir(project_path):
            return {
                "status": "error",
                "message": f"Project directory not found: {project_path}",
            }

        site_name = self.sanitize_name(site_name) if site_name else ""
        
        # ── REFINE PROJECT PATH ──
        refined_path = self._refine_project_path(project_path, "static")  # Netlify is for static/frontend
        logger.info(f"[NETLIFY] Original path: {project_path} -> Refined path: {refined_path}")
        
        logger.info(f"[NETLIFY] Deploying from {refined_path}, site_name={site_name or '(auto)'}")

        try:
            # Build ZIP
            buf = io.BytesIO()
            file_count = 0
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, fnames in os.walk(refined_path):
                    dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", "__pycache__", ".next", "dist", "build"}]
                    for fn in fnames:
                        fp = os.path.join(root, fn)
                        zf.write(fp, os.path.relpath(fp, refined_path))
                        file_count += 1
            buf.seek(0)
            logger.info(f"[NETLIFY] ZIP created with {file_count} files")

            headers = {"Authorization": f"Bearer {settings.NETLIFY_TOKEN}"}
            site_id = None

            # If custom site name provided, create site first
            if site_name:
                create_resp = await self.http.post(
                    "https://api.netlify.com/api/v1/sites",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"name": site_name},
                )
                if create_resp.status_code < 300:
                    site_data = create_resp.json()
                    site_id = site_data.get("id")
                    logger.info(f"[NETLIFY] Created site: {site_name}.netlify.app (id={site_id})")
                elif create_resp.status_code == 422:
                    # Name already taken — try deploying anyway
                    logger.info(f"[NETLIFY] Site name '{site_name}' already exists, deploying to it...")
                    # Fetch existing site
                    fetch_resp = await self.http.get(
                        f"https://api.netlify.com/api/v1/sites?name={site_name}",
                        headers=headers,
                    )
                    if fetch_resp.status_code == 200:
                        sites = fetch_resp.json()
                        if sites and len(sites) > 0:
                            site_id = sites[0].get("id")

            # Deploy the ZIP
            buf.seek(0)
            deploy_url = "https://api.netlify.com/api/v1/sites"
            if site_id:
                deploy_url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"

            resp = await self.http.post(
                deploy_url,
                headers={**headers, "Content-Type": "application/zip"},
                content=buf.read(),
            )

            # Safe JSON parsing
            try:
                result = resp.json()
            except Exception:
                logger.error(f"[NETLIFY] Non-JSON response: {resp.text[:500]}")
                return {
                    "status": "error",
                    "message": f"Netlify returned non-JSON response (HTTP {resp.status_code})",
                }

            logger.info(f"[NETLIFY] Deploy response: {resp.status_code}")

            if resp.status_code < 300:
                # ── CLEAN RESULT FORMAT ──
                final_url = result.get("ssl_url") or result.get("url") or ""
                return {
                    "platform": "netlify",
                    "url": final_url,
                    "project_name": result.get("name", site_name),
                    "status": "success"
                }
            else:
                error_msg = result.get("message", "") if isinstance(result, dict) else str(result)[:200]
                return {
                    "status": "error",
                    "message": f"Netlify deploy failed ({resp.status_code}): {error_msg}",
                    "raw": result,
                }

        except Exception as e:
            logger.exception("[NETLIFY] Deploy crashed")
            return {
                "status": "error",
                "message": f"Netlify deploy error: {str(e)}",
            }

    # =====================================================
    # CLOUDFLARE DEPLOYMENT (wrangler pages deploy CLI)
    # =====================================================

    async def deploy_to_cloudflare(
        self,
        project_path: str,
        project_name: str
    ) -> dict:
        """
        Deploy to Cloudflare Pages using the official wrangler CLI.
        Matches the exact behavior of manual Cloudflare dashboard upload.

        On Windows, runs via `cmd /c` to bypass PowerShell execution policy.
        Only returns a URL if the CLI exits with code 0.
        Falls back to Netlify if Cloudflare fails.
        """

        if not settings.has_cloudflare:
            return {
                "status": "error",
                "message": "Cloudflare credentials not set. Add CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID to .env.",
            }

        # ── REFINE PROJECT PATH ──
        # Cloudflare Pages is for static sites, so we use build artifact if present
        refined_path = self._refine_project_path(project_path, "static")
        logger.info(f"[CLOUDFLARE] Original path: {project_path} -> Refined path: {refined_path}")
        
        # Normalize to absolute path
        abs_path = os.path.abspath(refined_path)
        logger.info(f"[CLOUDFLARE] Project path: {abs_path}")

        if not os.path.isdir(abs_path):
            return {
                "status": "error",
                "message": f"Project directory not found: {abs_path}",
            }

        # Check there are actual files to deploy
        file_list = [f for f in os.listdir(abs_path) if os.path.isfile(os.path.join(abs_path, f))]
        if not file_list:
            return {
                "status": "error",
                "message": f"No files found in project directory: {abs_path}",
            }
        logger.info(f"[CLOUDFLARE] Files found: {file_list[:10]}")

        project_name = self.sanitize_name(project_name)

        try:
            import subprocess as _sp
            import re as _re

            # Build environment with Cloudflare credentials
            env = {**os.environ}
            env["CLOUDFLARE_API_TOKEN"] = settings.CLOUDFLARE_API_TOKEN
            env["CLOUDFLARE_ACCOUNT_ID"] = settings.CLOUDFLARE_ACCOUNT_ID

            # Step 1: Create the Pages project via REST API (wrangler deploy doesn't auto-create)
            # This is idempotent — if project exists, API returns 409 which we ignore
            acct = settings.CLOUDFLARE_ACCOUNT_ID
            try:
                create_resp = await self.http.post(
                    f"https://api.cloudflare.com/client/v4/accounts/{acct}/pages/projects",
                    headers={
                        "Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "name": project_name,
                        "production_branch": "main",
                    },
                )
                logger.info(f"[CLOUDFLARE] Create project '{project_name}': HTTP {create_resp.status_code}")
                
                if create_resp.status_code not in [200, 201, 409]:
                    logger.error(f"[CLOUDFLARE] Project creation failed: {create_resp.text}")
                    return {
                        "status": "error",
                        "error": "CLOUDFLARE_API_FAILED",
                        "message": f"Cloudflare API failed to create project (HTTP {create_resp.status_code})"
                    }
            except Exception as ce:
                logger.error(f"[CLOUDFLARE] Create project API crash: {ce}")
                return {
                    "status": "error",
                    "error": "CLOUDFLARE_API_FAILED",
                    "message": f"Cloudflare API connection failed: {str(ce)}"
                }

            # On Windows, use cmd /c to bypass PowerShell execution policy.
            # For paths with spaces, we set the cwd to the project dir and use "." as the directory arg.
            if os.name == "nt":
                cmd = (
                    f'cmd /c "npx wrangler pages deploy . '
                    f'--project-name={project_name} '
                    f'--branch=main '
                    f'--commit-dirty=true"'
                )
            else:
                cmd = (
                    f"npx wrangler pages deploy . "
                    f"--project-name={project_name} "
                    f"--branch=main "
                    f"--commit-dirty=true"
                )

            logger.info(f"[CLOUDFLARE] Running wrangler in cwd={abs_path}")
            logger.info(f"[CLOUDFLARE] Command: {cmd}")

            # Step 2: Proactive CLI check (Fix WinError 2)
            import shutil as _sh
            if not _sh.which("npm"):
                logger.error("[CLOUDFLARE] npm/npx not found on system")
                return {
                    "status": "error",
                    "error": "CLOUDFLARE_CLI_MISSING",
                    "message": "npm/npx not found. Please install Node.js to use Cloudflare Pages deployment."
                }

            # Run the command with cwd set to the project directory
            # Use encoding='utf-8' + errors='replace' because wrangler outputs emoji
            # that Windows cp1252 cannot decode
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _sp.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env=env,
                    cwd=abs_path,
                    encoding="utf-8",
                    errors="replace",
                )
            )

            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            exit_code = result.returncode

            logger.info(f"[CLOUDFLARE] Exit code: {exit_code}")
            if stdout:
                logger.info(f"[CLOUDFLARE] stdout:\n{stdout[:800]}")
            if stderr:
                logger.info(f"[CLOUDFLARE] stderr:\n{stderr[:800]}")

            # ── SUCCESS: exit code 0 ──
            if exit_code == 0:
                # Extract the .pages.dev URL from wrangler output
                # Wrangler prints lines like:
                #   ✨ Deployment complete! Take a peek over at https://xxxxx.project.pages.dev
                deploy_url = ""
                combined = stdout + "\n" + stderr
                for line in combined.split("\n"):
                    urls = _re.findall(r'https?://[^\s"\'<>]+\.pages\.dev[^\s"\'<>]*', line)
                    if urls:
                        deploy_url = urls[0].rstrip(".")
                        break

                if not deploy_url:
                    # No fallback allowed
                    logger.error("[CLOUDFLARE] Wrangler succeeded but no deployment URL found in output")
                    return {
                        "status": "error",
                        "error": "DEPLOYMENT_FAILED",
                        "message": "Cloudflare succeeded but could not detect deployment URL"
                    }

                logger.info(f"[CLOUDFLARE] ✓ SUCCESS: {deploy_url}")
                # ── CLEAN RESULT FORMAT ──
                return {
                    "platform": "cloudflare",
                    "url": deploy_url,
                    "project_name": project_name,
                    "status": "success"
                }

            # ── FAILURE: non-zero exit code ──
            error_detail = stderr or stdout or "Unknown wrangler error"

            # Check for common issues
            if "could not find" in error_detail.lower() or "is not recognized" in error_detail.lower():
                logger.error(f"[CLOUDFLARE] Wrangler not installed: {error_detail[:200]}")
                return {
                    "status": "error",
                    "error": "CLOUDFLARE_CLI_MISSING",
                    "message": "wrangler CLI is not installed or accessible. Please run: npm install -g wrangler"
                }

            # NO FALLBACK
            return {
                "status": "error",
                "error": "DEPLOYMENT_FAILED",
                "message": f"Cloudflare failed: {error_detail[:300]}",
            }

        except _sp.TimeoutExpired:
            logger.error("[CLOUDFLARE] Timed out after 180s")
            return {
                "status": "error",
                "error": "DEPLOYMENT_FAILED",
                "message": "Cloudflare deployment timed out after 180s"
            }

        except Exception as e:
            logger.exception("[CLOUDFLARE] Deploy crashed")
            return {
                "status": "error",
                "message": f"Cloudflare deploy error: {str(e)}",
            }



    # =====================================================
    # POLL STATUS
    # =====================================================

    async def poll_status(
        self,
        platform: str,
        deployment_id: str,
        max_polls: int = 20
    ) -> dict:

        for _ in range(max_polls):

            await asyncio.sleep(3)

            try:

                if (
                    platform == "Vercel"
                    and settings.has_vercel
                ):

                    resp = await self.http.get(
                        (
                            "https://api.vercel.com/"
                            f"v13/deployments/"
                            f"{deployment_id}"
                        ),
                        headers={
                            "Authorization": (
                                f"Bearer "
                                f"{settings.VERCEL_TOKEN}"
                            )
                        },
                    )

                    data = resp.json()

                    state = data.get(
                        "readyState",
                        "UNKNOWN"
                    )

                    if state in (
                        "READY",
                        "ERROR",
                        "CANCELED",
                    ):

                        url = data.get("url", "")

                        if (
                            url
                            and not url.startswith("http")
                        ):
                            url = f"https://{url}"

                        return {
                            "status": state.lower(),
                            "url": url,
                            "raw": data,
                        }

                elif (
                    platform == "Render"
                    and settings.RENDER_API_KEY
                ):

                    resp = await self.http.get(
                        (
                            "https://api.render.com/v1/"
                            f"services/{deployment_id}"
                        ),
                        headers={
                            "Authorization": (
                                "Bearer "
                                f"{settings.RENDER_API_KEY}"
                            )
                        },
                    )

                    if resp.status_code == 200:

                        data = resp.json()

                        svc = data.get(
                            "service",
                            data
                        )

                        if (
                            svc.get("suspended")
                            == "not_suspended"
                        ):

                            return {
                                "status": "ready",
                                "url": (
                                    "https://"
                                    f"{svc.get('slug', deployment_id)}"
                                    ".onrender.com"
                                ),
                                "raw": data,
                            }

            except Exception:
                pass

        return {
            "status": "timeout",
            "message": (
                "Deployment polling timed out"
            ),
        }

    # =====================================================
    # RENDER DEPLOYMENT
    # =====================================================

    async def deploy_to_render(
        self,
        project_name: str,
        repo_url: str = "",
        framework: str = ""
    ) -> dict:

        if not settings.RENDER_API_KEY:
            return {
                "status": "error",
                "message": "RENDER_API_KEY not set",
            }

        if not repo_url:
            return {
                "status": "error",
                "message": (
                    "Render requires a GitHub "
                    "repository URL for deployment"
                ),
            }

        try:

            env = (
                "python"
                if framework in (
                    "fastapi",
                    "flask",
                    "django",
                    "python",
                )
                else "node"
            )

            start_cmd = {
                "fastapi": (
                    "uvicorn main:app "
                    "--host 0.0.0.0 "
                    "--port $PORT"
                ),

                "flask": "python app.py",

                "django": (
                    "python manage.py "
                    "runserver 0.0.0.0:$PORT"
                ),

                "nodejs": "npm start",

                "nextjs": "npm start",

                "react": (
                    "npx serve -s build -l $PORT"
                ),
            }.get(
                framework,
                "npm start"
            )

            resp = await self.http.post(
                "https://api.render.com/v1/services",
                headers={
                    "Authorization": (
                        "Bearer "
                        f"{settings.RENDER_API_KEY}"
                    ),
                    "Content-Type": "application/json",
                },
                json={
                    "type": "web_service",
                    "name": project_name,
                    "repo": repo_url,
                    "autoDeploy": "yes",
                    "branch": "main",
                    "runtime": env,
                    "startCommand": start_cmd,
                    "plan": "free",
                    "region": "oregon",
                },
            )

            result = resp.json()

            if resp.status_code < 300:

                svc = result.get(
                    "service",
                    result
                )

                # ── CLEAN RESULT FORMAT ──
                return {
                    "platform": "render",
                    "url": f"https://{svc.get('slug', project_name)}.onrender.com",
                    "project_name": project_name,
                    "status": "success"
                }

            return {
                "status": "error",
                "message": result.get(
                    "message",
                    str(result)
                ),
                "raw": result,
            }

        except Exception as e:

            return {
                "status": "error",
                "message": str(e),
            }

    # =====================================================
    # VERIFY DEPLOYMENT
    # =====================================================

    async def verify_deployment(
        self,
        url: str,
        max_retries: int = 5
    ) -> dict:

        if not url:
            return {
                "verified": False,
                "reason": "No URL provided",
            }

        if not url.startswith("http"):
            url = f"https://{url}"

        logger.info(
            f"[VERIFY] Checking deployment URL: {url}"
        )

        for attempt in range(max_retries):

            try:

                resp = await self.http.get(
                    url,
                    follow_redirects=True,
                    timeout=10,
                )

                if resp.status_code < 500:

                    logger.info(
                        f"[VERIFY] {url} → "
                        f"{resp.status_code} "
                        f"(attempt {attempt + 1})"
                    )

                    return {
                        "verified": True,
                        "status_code": resp.status_code,
                        "url": str(resp.url),
                        "attempts": attempt + 1,
                    }

                logger.warning(
                    f"[VERIFY] {url} → "
                    f"{resp.status_code} "
                    f"(attempt {attempt + 1})"
                )

            except Exception as e:

                logger.debug(
                    f"[VERIFY] Attempt "
                    f"{attempt + 1} failed: {e}"
                )

            await asyncio.sleep(3)

        return {
            "verified": False,
            "reason": (
                f"URL did not respond after "
                f"{max_retries} attempts"
            ),
            "url": url,
        }
