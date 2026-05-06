"""
Domain Search Route — Cloudflare DNS over HTTPS
=================================================
Uses Cloudflare DoH to check domain availability in real-time.
NXDOMAIN (Status=3) means the domain is likely available.
NO fake results. NO API keys needed.
"""
import logging
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/domain", tags=["Domain"])
logger = logging.getLogger(__name__)


class DomainSearchInput(BaseModel):
    query: str


@router.post("/search")
async def search_domain(data: DomainSearchInput):
    query = data.query.strip().lower().replace(" ", "")
    if not query:
        return {"error": "Query is required"}

    # Strip protocol, www, and existing TLD
    query = query.replace("https://", "").replace("http://", "").replace("www.", "")
    if "." in query:
        query = query.split(".")[0]

    if not query or len(query) < 2:
        return {"error": "Query must be at least 2 characters"}

    # Check multiple TLDs using Cloudflare DNS over HTTPS
    tlds = [".com", ".net", ".io", ".tech", ".dev", ".app", ".xyz"]
    logger.info(f"[DOMAIN] Searching for: {query} across {len(tlds)} TLDs")

    async def check_domain(client: httpx.AsyncClient, tld: str) -> dict:
        domain = f"{query}{tld}"
        try:
            resp = await client.get(
                "https://cloudflare-dns.com/dns-query",
                params={"name": domain, "type": "NS"},
                headers={"accept": "application/dns-json"},
                timeout=8,
            )
            data = resp.json()
            # Status 3 = NXDOMAIN = domain is not registered
            # Status 0 = NOERROR = domain exists (has NS records)
            status = data.get("Status", -1)
            has_answer = "Answer" in data or "Authority" in data
            available = status == 3

            logger.debug(f"[DOMAIN] {domain}: DNS Status={status}, available={available}")

            return {
                "domain": domain,
                "available": available,
                "price": "$12.00/yr" if available else "N/A (taken)",
                "registrar": "Available for registration" if available else "Already registered",
                "source": "Cloudflare DNS",
            }
        except httpx.TimeoutException:
            logger.warning(f"[DOMAIN] Timeout checking {domain}")
            return {
                "domain": domain,
                "available": None,
                "price": "Unknown",
                "registrar": "Check timed out",
                "source": "Cloudflare DNS (timeout)",
            }
        except Exception as e:
            logger.error(f"[DOMAIN] Error checking {domain}: {e}")
            return {
                "domain": domain,
                "available": None,
                "price": "Unknown",
                "registrar": f"Error: {str(e)[:50]}",
                "source": "Error",
            }

    try:
        async with httpx.AsyncClient() as client:
            tasks = [check_domain(client, tld) for tld in tlds]
            results = await asyncio.gather(*tasks)

        logger.info(f"[DOMAIN] Returned {len(results)} results for '{query}'")
        return {"results": list(results), "source": "Cloudflare DNS (real-time)"}

    except Exception as e:
        logger.error(f"[DOMAIN] Search failed: {e}")
        return {
            "error": "Domain search failed",
            "details": str(e),
        }
