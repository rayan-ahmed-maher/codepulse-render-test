"""
Platform Name Generator — Universal custom domain naming
==========================================================
Generates clean, platform-specific project/site names for deployment.
This is a PREPROCESSING layer — it does NOT modify deployment logic.

Usage:
    from services.name_generator import generate_deploy_name

    name = generate_deploy_name("Café Noir Indiranagar!", platform="Netlify")
    # → "cafe-noir-indiranagar"

    name = generate_deploy_name("My Project", platform="Netlify", custom_name="my-cafe-site")
    # → "my-cafe-site"
"""
import re
import random
import string
import logging

logger = logging.getLogger(__name__)

# Platform-specific max lengths
PLATFORM_MAX_LENGTH = {
    "Netlify":    63,
    "Cloudflare": 50,
    "Vercel":     63,
    "Render":     30,
}

# Minimum valid name length
MIN_LENGTH = 3


def _base_sanitize(name: str) -> str:
    """Core sanitization: lowercase, remove specials, collapse hyphens."""
    # Lowercase and strip whitespace
    name = name.lower().strip()

    # Replace common word separators with hyphens
    name = name.replace("_", "-").replace(" ", "-").replace(".", "-")

    # Remove all characters except a-z, 0-9, and hyphens
    name = re.sub(r"[^a-z0-9\-]", "", name)

    # Collapse multiple consecutive hyphens into one
    name = re.sub(r"-+", "-", name)

    # Must not start or end with a hyphen
    name = name.strip("-")

    return name


def _ensure_min_length(name: str) -> str:
    """Pad short names to meet minimum length."""
    if len(name) < MIN_LENGTH:
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        name = f"{name}-{suffix}" if name else f"project-{suffix}"
    return name


def _truncate_for_platform(name: str, platform: str) -> str:
    """Truncate to platform max length, ensuring we don't end with a hyphen."""
    max_len = PLATFORM_MAX_LENGTH.get(platform, 63)
    if len(name) > max_len:
        name = name[:max_len].rstrip("-")
    return name


def _add_uniqueness_suffix(name: str, platform: str) -> str:
    """Append a short random suffix for uniqueness, respecting platform max length."""
    max_len = PLATFORM_MAX_LENGTH.get(platform, 63)
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))

    # Ensure we have room for the suffix
    available = max_len - len(suffix) - 1  # -1 for the hyphen
    if available < MIN_LENGTH:
        available = MIN_LENGTH

    base = name[:available].rstrip("-")
    return f"{base}-{suffix}"


def generate_deploy_name(
    project_name: str,
    platform: str = "Netlify",
    custom_name: str | None = None,
) -> str:
    """
    Generate a clean, valid deployment name for the given platform.

    Args:
        project_name: The raw project name (from upload/analysis).
        platform: Target platform (Netlify, Cloudflare, Vercel, Render).
        custom_name: Optional user-provided custom subdomain name.

    Returns:
        A clean, platform-compliant name ready to use as a site/project name.
        Falls back to a safe default if generation fails.
    """
    try:
        # Use custom name if provided, otherwise use project name
        raw = custom_name.strip() if custom_name and custom_name.strip() else project_name

        # Step 1: Base sanitization
        name = _base_sanitize(raw)

        # Step 2: Ensure minimum length
        name = _ensure_min_length(name)

        # Step 3: Truncate for platform
        name = _truncate_for_platform(name, platform)

        # Step 4: Final validation
        # Must be a-z, 0-9, hyphens only. Must not start/end with hyphen.
        if not re.match(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$", name) and len(name) >= 2:
            # Try to fix by stripping invalid chars again
            name = re.sub(r"[^a-z0-9\-]", "", name).strip("-")

        if not name or len(name) < MIN_LENGTH:
            name = f"deploy-{random.randint(1000, 9999)}"

        logger.info(
            f"[NAME] Generated: '{raw}' → '{name}' "
            f"(platform={platform}, len={len(name)}/{PLATFORM_MAX_LENGTH.get(platform, 63)})"
        )
        return name

    except Exception as e:
        # Fallback: never block deployment because of a naming error
        fallback = f"deploy-{random.randint(1000, 9999)}"
        logger.warning(f"[NAME] Generation failed ({e}), using fallback: {fallback}")
        return fallback


def generate_deploy_name_unique(
    project_name: str,
    platform: str = "Netlify",
    custom_name: str | None = None,
    max_retries: int = 3,
) -> str:
    """
    Generate a unique name by appending a random suffix.
    Use this when a name collision is detected.

    Returns a different name on each call.
    """
    base = generate_deploy_name(project_name, platform, custom_name)

    for attempt in range(max_retries):
        candidate = _add_uniqueness_suffix(base, platform)
        logger.info(f"[NAME] Unique attempt {attempt + 1}: '{candidate}'")
        return candidate

    # Final fallback
    return _add_uniqueness_suffix(base, platform)


def get_expected_url(name: str, platform: str) -> str:
    """Return the expected public URL for a given name and platform."""
    urls = {
        "Netlify":    f"https://{name}.netlify.app",
        "Cloudflare": f"https://{name}.pages.dev",
        "Vercel":     f"https://{name}.vercel.app",
        "Render":     f"https://{name}.onrender.com",
    }
    return urls.get(platform, f"https://{name}.example.com")
