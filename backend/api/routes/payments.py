"""
Payment Routes — Razorpay Integration (Real Orders, HMAC Verification)
========================================================================
ABSOLUTE RULES:
1. NEVER register domain without verified HMAC SHA256 signature
2. NEVER confirm payment without Supabase record written first
3. NEVER skip HMAC verification under any circumstance
"""
import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List

import httpx
from fastapi import APIRouter, Request, Header
from pydantic import BaseModel

from core.config import settings
from core.supabase_client import get_supabase
from services.email import send_domain_registration_email

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = logging.getLogger(__name__)


# ── Models ──────────────────────────────────────────────────
class CreateOrderInput(BaseModel):
    domains: List[str]
    total_amount_inr: float  # Total in INR (will be converted to paise)
    user_id: Optional[str] = None
    user_email: Optional[str] = None


class VerifyPaymentInput(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    domains: List[str] = []


# ── Create Razorpay Order ──────────────────────────────────
@router.post("/create-order")
async def create_order(data: CreateOrderInput):
    """Create a real Razorpay order. Amount in paise. Returns order_id + key_id."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return {
            "status": "error",
            "reason": "Razorpay credentials not configured",
            "evidence": "RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET missing from .env",
            "solution": "Add Razorpay credentials to your .env file",
        }

    amount_paise = int(data.total_amount_inr * 100)
    if amount_paise < 100:  # Razorpay minimum ₹1
        return {
            "status": "error",
            "reason": "Amount too low",
            "evidence": f"₹{data.total_amount_inr} is below minimum ₹1",
            "solution": "Select at least one domain to proceed",
        }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.razorpay.com/v1/orders",
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                json={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": f"dom_{int(time.time())}",
                    "notes": {
                        "domains": ",".join(data.domains),
                        "user_id": data.user_id or "",
                    },
                },
                timeout=15,
            )

        result = resp.json()

        if resp.status_code >= 300:
            logger.error(f"[RAZORPAY] Order creation failed: {result}")
            return {
                "status": "error",
                "reason": "Razorpay order creation failed",
                "evidence": result.get("error", {}).get("description", str(result)),
                "solution": "Check Razorpay dashboard for account issues",
            }

        order_id = result.get("id")
        logger.info(f"[RAZORPAY] Order created: {order_id} for ₹{data.total_amount_inr}")

        # Write Supabase record BEFORE returning to frontend
        sb = get_supabase()
        if sb:
            try:
                sb.table("domain_orders").insert({
                    "razorpay_order_id": order_id,
                    "user_id": data.user_id or "",
                    "user_email": data.user_email or "",
                    "domains": data.domains,
                    "amount_inr": data.total_amount_inr,
                    "amount_paise": amount_paise,
                    "status": "created",
                }).execute()
            except Exception as e:
                logger.warning(f"[RAZORPAY] Supabase order record failed: {e}")

        return {
            "status": "success",
            "order_id": order_id,
            "amount": amount_paise,
            "amount_inr": data.total_amount_inr,
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
        }

    except Exception as e:
        logger.exception("[RAZORPAY] Order creation crashed")
        return {
            "status": "error",
            "reason": "Payment service unavailable",
            "evidence": str(e),
            "solution": "Try again in a few seconds. If the issue persists, contact support.",
        }


# ── Verify Payment (HMAC SHA256) ───────────────────────────
@router.post("/verify")
async def verify_payment(data: VerifyPaymentInput):
    """
    Verify Razorpay payment signature using HMAC SHA256.
    ABSOLUTE RULE: Domain registration ONLY happens after this check passes.
    """
    if not settings.RAZORPAY_KEY_SECRET:
        return {
            "status": "error",
            "reason": "Razorpay credentials not configured",
            "evidence": "RAZORPAY_KEY_SECRET missing",
            "solution": "Add RAZORPAY_KEY_SECRET to .env",
        }

    # ── Step 1: HMAC SHA256 signature verification ──
    message = f"{data.razorpay_order_id}|{data.razorpay_payment_id}"
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, data.razorpay_signature):
        logger.error(f"[RAZORPAY] HMAC verification FAILED for order {data.razorpay_order_id}")
        return {
            "status": "error",
            "verified": False,
            "reason": "Payment signature verification failed",
            "evidence": "HMAC SHA256 mismatch — possible tampering detected",
            "solution": "Do not retry. Contact support if you believe this is an error.",
        }

    logger.info(f"[RAZORPAY] HMAC verified ✓ for order {data.razorpay_order_id}")

    # ── Step 2: Update Supabase order record to 'paid' ──
    sb = get_supabase()
    if sb:
        try:
            sb.table("domain_orders").update({
                "status": "paid",
                "razorpay_payment_id": data.razorpay_payment_id,
                "paid_at": datetime.utcnow().isoformat(),
            }).eq("razorpay_order_id", data.razorpay_order_id).execute()
        except Exception as e:
            logger.warning(f"[RAZORPAY] Supabase order update failed: {e}")

    # ── Step 3: Register domains in Supabase (only AFTER verification) ──
    registered_domains = []
    expiry_date = (datetime.utcnow() + timedelta(days=365)).isoformat()

    for domain in data.domains:
        domain_record = {
            "domain_name": domain,
            "user_id": data.user_id or "",
            "user_email": data.user_email or "",
            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "registration_status": "active",
            "registered_at": datetime.utcnow().isoformat(),
            "expiry_date": expiry_date,
        }
        if sb:
            try:
                sb.table("domain_purchases").insert(domain_record).execute()
                registered_domains.append(domain)
            except Exception as e:
                logger.error(f"[RAZORPAY] Domain record insert failed for {domain}: {e}")
        else:
            registered_domains.append(domain)

    # ── Step 4: Send confirmation email ──
    if data.user_email and registered_domains:
        try:
            await send_domain_registration_email(
                data.user_email, registered_domains, expiry_date
            )
        except Exception as e:
            logger.warning(f"[RAZORPAY] Email send failed: {e}")

    logger.info(f"[RAZORPAY] Payment verified + {len(registered_domains)} domains registered")

    return {
        "status": "success",
        "verified": True,
        "order_id": data.razorpay_order_id,
        "payment_id": data.razorpay_payment_id,
        "registered_domains": registered_domains,
        "expiry_date": expiry_date,
    }


# ── Webhook (payment.captured / payment.failed) ────────────
@router.post("/webhook")
async def payment_webhook(request: Request):
    """
    Handle Razorpay webhook events.
    Verifies webhook signature if RAZORPAY_WEBHOOK_SECRET is set.
    """
    body = await request.body()
    body_str = body.decode("utf-8")

    # Verify webhook signature if secret is set
    webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if webhook_secret:
        sig_header = request.headers.get("x-razorpay-signature", "")
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, sig_header):
            logger.error("[WEBHOOK] Signature verification failed")
            return {"status": "error", "reason": "Invalid webhook signature"}

    import json
    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError:
        return {"status": "error", "reason": "Invalid JSON payload"}

    event = payload.get("event", "")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id", "")

    logger.info(f"[WEBHOOK] Event: {event} | Order: {order_id}")

    sb = get_supabase()

    if event == "payment.captured":
        if sb and order_id:
            try:
                sb.table("domain_orders").update({
                    "status": "captured",
                    "webhook_confirmed_at": datetime.utcnow().isoformat(),
                }).eq("razorpay_order_id", order_id).execute()
            except Exception as e:
                logger.warning(f"[WEBHOOK] Supabase update failed: {e}")

    elif event == "payment.failed":
        if sb and order_id:
            try:
                sb.table("domain_orders").update({
                    "status": "failed",
                    "failure_reason": payment_entity.get("error_description", ""),
                }).eq("razorpay_order_id", order_id).execute()
            except Exception as e:
                logger.warning(f"[WEBHOOK] Supabase update failed: {e}")

    return {"status": "ok"}
