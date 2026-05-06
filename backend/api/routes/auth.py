"""
Auth Routes — Password validation + profile management
"""
import re
from fastapi import APIRouter
from pydantic import BaseModel
from core.supabase_client import db

router = APIRouter(prefix="/auth", tags=["Auth"])

# ── Strict Password Rules ─────────────────────────────────────
PW_MIN_LENGTH = 8
PW_RULES = [
    (r"[a-zA-Z]", "Must contain at least 1 letter"),
    (r"[0-9]", "Must contain at least 1 number"),
    (r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", "Must contain at least 1 special character"),
]


def validate_password(password: str) -> dict:
    errors = []
    if len(password) < PW_MIN_LENGTH:
        errors.append(f"Must be at least {PW_MIN_LENGTH} characters")
    for pattern, msg in PW_RULES:
        if not re.search(pattern, password):
            errors.append(msg)

    strength = 0
    if len(password) >= 8: strength += 1
    if len(password) >= 12: strength += 1
    if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password): strength += 1
    if re.search(r"[0-9]", password): strength += 1
    if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", password): strength += 1

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "strength": min(strength, 5),  # 0-5
        "label": ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"][min(strength, 5)],
    }


class PasswordInput(BaseModel):
    password: str


class ProfileInput(BaseModel):
    user_id: str
    email: str
    auth_provider: str = "email"
    display_name: str = ""
    avatar_url: str = ""


@router.post("/validate-password")
async def validate_pw(data: PasswordInput):
    return validate_password(data.password)


@router.post("/register-profile")
async def register_profile(data: ProfileInput):
    result = await db.upsert_user_profile(
        user_id=data.user_id,
        email=data.email,
        provider=data.auth_provider,
        display_name=data.display_name,
        avatar_url=data.avatar_url,
    )
    return result
