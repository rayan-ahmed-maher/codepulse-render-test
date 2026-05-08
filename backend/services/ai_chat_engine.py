"""
AI Chat Engine — NVIDIA NIM + Serper Live Doc Search
=====================================================
Provides context-aware AI responses with live documentation lookup.
"""
import logging
from typing import Optional, List, Dict
import httpx
from openai import OpenAI
from core.config import settings

logger = logging.getLogger(__name__)


class ChatEngine:
    """Handles NIM AI responses with full context injection and Serper search."""

    SRE_SYSTEM_PROMPT = """You are an elite Senior SRE (Site Reliability Engineer) for DeployAI.
You analyze deployment errors, build failures, and infrastructure issues.

RULES:
1. ALWAYS use the project context provided to give specific answers about THIS project.
2. When Serper search results are provided, incorporate them into your answer with real documentation links.
3. NEVER give generic responses — always reference the actual framework, error, and platform from context.
4. Format your response clearly with:
   - ROOT CAUSE: one sentence
   - FIX: step-by-step instructions specific to this project
   - COMMAND: the exact terminal command to fix it (if applicable)
5. Keep responses under 250 words.
6. If the error matches a known Serper doc result, cite the source URL."""

    GUIDE_SYSTEM_PROMPT = """You are the Owl Guide 🦉 — the AI deployment assistant for DeployAI, powered by NVIDIA NIM.

RULES:
1. You ONLY discuss: deployment, hosting, domains, DNS, SSL, CI/CD, build systems, debugging, framework configuration, and DevOps.
2. ALWAYS reference the project context provided — mention the user's actual framework, platform, and project name.
3. If the user asks about their project, use the injected context (framework, health score, entry point) to answer.
4. Be concise, actionable, and specific. Use emoji sparingly.
5. When suggesting deployment targets, consider the detected framework from context.
6. Keep responses under 200 words.
7. If asked off-topic, reply: "I'm your deployment specialist! I can help with deploying, domains, and debugging builds. What would you like to deploy?"."""

    def __init__(self):
        self.client = None
        self.model = "meta/llama-3.1-70b-instruct"
        if settings.has_nvidia:
            try:
                self.client = OpenAI(
                    base_url=settings.NVIDIA_BASE_URL,
                    api_key=settings.NVIDIA_API_KEY,
                )
            except Exception as e:
                logger.warning(f"[CHAT] NIM client init failed: {e}")

    async def search_docs(self, query: str) -> Optional[List[dict]]:
        """Search live documentation using Serper API."""
        if not settings.has_serper:
            logger.info("[CHAT] Serper not configured — skipping doc search")
            return None

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": settings.SERPER_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={"q": query, "num": 5},
                    timeout=8,
                )

            if resp.status_code == 200:
                data = resp.json()
                results = []
                for item in data.get("organic", [])[:5]:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "link": item.get("link", ""),
                    })
                return results
            else:
                logger.warning(f"[CHAT] Serper returned {resp.status_code}")
                return None
        except Exception as e:
            logger.warning(f"[CHAT] Serper search failed: {e}")
            return None

    async def answer_with_context(
        self,
        message: str,
        context: str = "",
        history: list = None,
        serper_results: list = None,
        mode: str = "guide",
    ) -> dict:
        """Generate an AI response with full context injection."""
        if not self.client:
            return {
                "agent": "System",
                "response": "AI not configured. Set NVIDIA_API_KEY in .env to enable the Owl Guide.",
            }

        # Build the full user message with context
        user_parts = []

        if context:
            user_parts.append(f"=== CURRENT PROJECT CONTEXT ===\n{context}\n=== END CONTEXT ===\n")

        if serper_results:
            docs_text = "\n".join(
                f"- [{r['title']}]({r['link']}): {r['snippet']}"
                for r in serper_results
            )
            user_parts.append(f"=== LIVE DOCUMENTATION RESULTS ===\n{docs_text}\n=== END DOCS ===\n")

        user_parts.append(f"User's question: {message}")
        full_user_message = "\n".join(user_parts)

        # Build message list
        system_prompt = self.SRE_SYSTEM_PROMPT if mode == "sre" else self.GUIDE_SYSTEM_PROMPT
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history for context
        if history:
            for msg in history[-10:]:  # Last 10 messages for context window
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        messages.append({"role": "user", "content": full_user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3 if mode == "sre" else 0.7,
                max_tokens=800,
            )
            reply = response.choices[0].message.content

            agent_name = "SRE" if mode == "sre" else "Owl Guide"
            result = {"agent": agent_name, "response": reply}

            # Parse SRE-specific fields
            if mode == "sre":
                diagnosis = self._parse_sre_response(reply)
                if diagnosis:
                    result["diagnosis"] = diagnosis

            return result

        except Exception as e:
            logger.error(f"[CHAT] NIM call failed: {e}")
            return {
                "agent": "System",
                "response": f"AI service temporarily unavailable: {str(e)[:100]}. Your project context has been preserved — try again in a moment.",
            }

    @staticmethod
    def _parse_sre_response(text: str) -> Optional[dict]:
        """Extract structured SRE diagnosis from response text."""
        import re
        diagnosis = {}
        for line in text.split("\n"):
            l = line.strip()
            if l.upper().startswith("ROOT CAUSE:"):
                diagnosis["root_cause"] = l.split(":", 1)[1].strip()
            elif l.upper().startswith("COMMAND:"):
                diagnosis["ghost_command"] = l.split(":", 1)[1].strip()
            elif l.upper().startswith("FIX:"):
                diagnosis["fix"] = l.split(":", 1)[1].strip()
            elif re.match(r"^\d+\.", l):
                diagnosis.setdefault("steps", []).append(re.sub(r"^\d+\.\s*", "", l))

        return diagnosis if diagnosis else None
