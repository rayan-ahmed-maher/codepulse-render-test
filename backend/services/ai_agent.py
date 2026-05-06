"""
AI Agent Services — NVIDIA NIM SRE Diagnostics & Owl Guide Chat
================================================================
Strict SRE-in-character prompting, ghost typing, cinematic summaries,
and proactive optimization suggestions.
"""
import re, logging
from dataclasses import dataclass, field
from typing import List, Optional
from openai import OpenAI
from core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class LogDiagnosis:
    severity: str
    human_fix: str
    root_cause: str
    fix_steps: List[str]
    ghost_command: str = ""
    summary: str = ""

@dataclass
class SecurityFinding:
    severity: str
    category: str
    description: str
    file_path: Optional[str] = None
    recommendation: str = ""

@dataclass
class SecurityScanResult:
    findings: List[SecurityFinding]
    overall_risk: str
    score_penalty: int


class NIMDiagnosticsAgent:
    """NVIDIA NIM-powered SRE agent for log analysis, security, and optimization."""

    SRE_PROMPT = """You are an elite Senior SRE (Site Reliability Engineer) for AutoDeploy AI.
You ONLY help with deployment, hosting, DevOps, CI/CD, build systems, and infrastructure.

STRICT RULES:
1. NEVER answer questions outside deployment/DevOps scope.
2. If asked something off-topic, reply: "I'm the AutoDeploy SRE — I only handle deployment, builds, and infrastructure. Ask me about your deployment!"
3. Always analyze logs with this format:
   SEVERITY: CRITICAL|HIGH|MEDIUM|LOW
   ROOT_CAUSE: <one sentence>
   HUMAN_FIX: <beginner-friendly fix explanation>
   GHOST_CMD: <the exact terminal command to fix it>
   SUMMARY: <condense the entire log into ONE cinematic sentence>
   STEPS:
   1. <step>
   2. <step>
   3. <step>
4. If no errors found, proactively suggest optimizations (image compression, tree-shaking, caching headers, etc.)
5. Keep responses under 200 words.
6. Always suggest the GHOST_CMD — the exact command the user should run."""

    OPTIMIZATION_PROMPT = """You are an elite SRE. The build succeeded with zero errors.
Analyze these project files and proactively suggest performance optimizations:
- Large image files → suggest WebP conversion
- Missing compression → suggest gzip/brotli
- Unused dependencies → suggest tree-shaking
- Missing caching headers → suggest cache config
- Large bundle size → suggest code splitting
Return 3-5 actionable tips, each on one line starting with "TIP:"."""

    def __init__(self):
        self.client = None
        self.model = "meta/llama-3.1-70b-instruct"
        if settings.has_nvidia:
            try:
                self.client = OpenAI(base_url=settings.NVIDIA_BASE_URL, api_key=settings.NVIDIA_API_KEY)
            except Exception:
                # OpenAI client init can fail with version mismatches — degrade gracefully
                import logging
                logging.getLogger(__name__).warning("[NIM] OpenAI client init failed — AI diagnostics disabled")

    def _call(self, system: str, user: str, max_tokens=1024) -> str:
        if not self.client:
            return "NVIDIA NIM not configured. Set NVIDIA_API_KEY in .env."
        try:
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                temperature=0.3, max_tokens=max_tokens,
            )
            return r.choices[0].message.content
        except Exception as e:
            logger.error(f"NIM error: {e}")
            return f"AI unavailable: {e}"

    def analyze_logs(self, logs: str) -> LogDiagnosis:
        raw = self._call(self.SRE_PROMPT, f"Analyze these build/deployment logs:\n\n{logs}")
        sev, rc, hf, steps, ghost, summary = "MEDIUM", "Unknown", "Check logs manually", [], "", ""
        for line in raw.split("\n"):
            l = line.strip()
            if l.startswith("SEVERITY:"):   sev = l.split(":",1)[1].strip()
            elif l.startswith("ROOT_CAUSE:"): rc = l.split(":",1)[1].strip()
            elif l.startswith("HUMAN_FIX:"):  hf = l.split(":",1)[1].strip()
            elif l.startswith("GHOST_CMD:"):  ghost = l.split(":",1)[1].strip()
            elif l.startswith("SUMMARY:"):    summary = l.split(":",1)[1].strip()
            elif re.match(r"^\d+\.", l):      steps.append(re.sub(r"^\d+\.\s*","",l))
        return LogDiagnosis(
            severity=sev, human_fix=hf, root_cause=rc,
            fix_steps=steps or ["Check error","Review config","Retry"],
            ghost_command=ghost, summary=summary,
        )

    def get_optimization_tips(self, file_list: List[str]) -> List[str]:
        raw = self._call(self.OPTIMIZATION_PROMPT, f"Project files:\n{chr(10).join(file_list[:30])}")
        tips = [l.replace("TIP:","").strip() for l in raw.split("\n") if l.strip().startswith("TIP:")]
        return tips or ["Run lighthouse audit for performance insights"]

    def security_scan(self, file_contents: dict) -> SecurityScanResult:
        findings = []
        patterns = [
            (r"(?:api_key|secret|token|password)\s*=\s*['\"][^'\"]{8,}['\"]","Hardcoded Secret"),
            (r"(?:AKIA)[A-Za-z0-9]{16,}","AWS Key"),
            (r"sk-[a-zA-Z0-9]{20,}","OpenAI Key"),
            (r"ghp_[a-zA-Z0-9]{36,}","GitHub Token"),
            (r"nvapi-[a-zA-Z0-9]{40,}","NVIDIA API Key"),
        ]
        for fp, content in file_contents.items():
            for pat, cat in patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    findings.append(SecurityFinding("CRITICAL",cat,
                        f"Secret found: {m.group()[:20]}...",fp,"Use .env variables"))
        penalty = min(40, sum({"CRITICAL":15,"HIGH":10,"MEDIUM":5,"LOW":2}.get(f.severity,0) for f in findings))
        risk = "CRITICAL" if penalty>=30 else "HIGH" if penalty>=20 else "MEDIUM" if penalty>=10 else "LOW"
        return SecurityScanResult(findings=findings, overall_risk=risk, score_penalty=penalty)


class OwlGuideAgent:
    """Owl Guide — SRE-restricted chat assistant."""

    PROMPT = """You are the Owl Guide 🦉 — the AI deployment assistant for AutoDeploy AI, powered by NVIDIA NIM.

STRICT CHARACTER RULES:
1. You ONLY discuss: deployment, hosting, domains, DNS, SSL, CI/CD, build systems, debugging build errors, framework configuration, and DevOps best practices.
2. If the user asks anything off-topic (coding tutorials, general knowledge, personal questions), reply:
   "I'm your deployment specialist! I can help with deploying your project, configuring domains, debugging builds, and optimizing your stack. What would you like to deploy today?"
3. Be concise, actionable, and friendly. Use emoji sparingly.
4. When giving deployment advice, always mention specific platforms (Vercel, Netlify, Cloudflare).
5. If the user provides project context (framework, error logs), use it to give targeted advice.
6. Keep responses under 150 words."""

    def __init__(self):
        self.client = None
        self.model = "meta/llama-3.1-70b-instruct"
        if settings.has_nvidia:
            self.client = OpenAI(base_url=settings.NVIDIA_BASE_URL, api_key=settings.NVIDIA_API_KEY)

    def ask(self, question: str, context: str = "") -> str:
        if not self.client:
            return "AI not configured. Set NVIDIA_API_KEY in .env to enable the Owl Guide."
        msg = f"User's project context: {context}\n\nUser's question: {question}" if context else question
        try:
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"system","content":self.PROMPT},{"role":"user","content":msg}],
                temperature=0.7, max_tokens=600,
            )
            return r.choices[0].message.content
        except Exception as e:
            return f"AI error: {e}"


class AIAgentOrchestrator:
    """Routes queries to the correct agent based on intent detection."""

    def __init__(self):
        self.sre = NIMDiagnosticsAgent()
        self.chat = OwlGuideAgent()

    def route_query(self, query: str, context: str = "") -> dict:
        sre_kw = ["error","fail","crash","bug","debug","fix","broken","500","404",
                   "timeout","logs","traceback","exception","build failed","deploy failed"]
        if any(kw in query.lower() for kw in sre_kw):
            d = self.sre.analyze_logs(query)
            return {
                "agent": "SRE",
                "response": d.human_fix,
                "diagnosis": {
                    "severity": d.severity,
                    "root_cause": d.root_cause,
                    "steps": d.fix_steps,
                    "ghost_command": d.ghost_command,
                    "summary": d.summary,
                },
            }
        return {"agent": "Owl Guide", "response": self.chat.ask(query, context)}
