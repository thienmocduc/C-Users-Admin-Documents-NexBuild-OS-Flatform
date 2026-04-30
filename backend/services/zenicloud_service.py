"""ZeniCloud unified API client — replaces direct Gemini + Fal.ai calls.

ZeniCloud is the company-wide AI gateway with:
    - 6 LLMs auto-switch (Claude/GPT/Gemini/Llama/Zeni Anima)
    - Imagen 3 image generation
    - Multi-modal image analysis (Gemini multi-modal)
    - Embeddings (text-embedding-004)
    - Built-in agents: /agents/architecture/run, /agents/structural/run

Single PAT token, single billing, no per-vendor key juggling.

Env vars:
    ZENI_TOKEN  — PAT token (zeni_pat_*)
    ZENI_BASE   — API base URL (default https://zenicloud.io/api/v1)
    ZENI_WS     — Workspace slug (default "nexbuild")
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ZENI_TOKEN = os.getenv("ZENI_TOKEN", "")
ZENI_BASE = os.getenv("ZENI_BASE", "https://zenicloud.io/api/v1").rstrip("/")
ZENI_WS = os.getenv("ZENI_WS", "nexbuild")
ZENI_TIMEOUT = float(os.getenv("ZENI_TIMEOUT", "180"))


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {ZENI_TOKEN}",
        "Content-Type": "application/json",
    }


def is_configured() -> bool:
    """True if ZENI_TOKEN is set — caller should check before using."""
    return bool(ZENI_TOKEN)


# ─── Helpers ────────────────────────────────────────────────────
# Tolerant regex — captures content inside ```...``` even if:
#   • Text appears AFTER closing fence (extra prose)
#   • Closing fence is MISSING (truncated output)
#   • Language tag is "json" or absent
_CODE_FENCE_OPEN_RE = re.compile(r"```(?:json|JSON)?\s*\n?", re.IGNORECASE)
_CODE_FENCE_CLOSE_RE = re.compile(r"\n?\s*```")


def strip_code_fence(text: str) -> str:
    """Strip ```json ... ``` wrapper. Tolerant of trailing text + missing close."""
    if not text:
        return ""
    s = text.strip()
    # Find opening fence
    m_open = _CODE_FENCE_OPEN_RE.search(s)
    if not m_open:
        return s  # no fence, return as-is
    inner_start = m_open.end()
    # Find closing fence after the opening
    m_close = _CODE_FENCE_CLOSE_RE.search(s, inner_start)
    inner_end = m_close.start() if m_close else len(s)
    return s[inner_start:inner_end].strip()


def _balanced_json_block(text: str) -> str | None:
    """Extract first balanced {...} block from text (handles nested braces)."""
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_str:
            escape = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None  # unbalanced — likely truncated


def parse_json_response(text: str) -> dict | None:
    """Parse JSON from LLM output. Multi-strategy:
    1. Strip ```...``` fence and try direct parse.
    2. If fail, find first balanced {...} block and try.
    3. Last resort: greedy match.
    """
    if not text:
        return None
    # Strategy 1: strip fence + direct parse
    cleaned = strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Strategy 2: balanced brace extraction
    block = _balanced_json_block(cleaned)
    if block:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass
    # Strategy 3: greedy regex (last resort, may fail on nested)
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


# ─── Text completion ────────────────────────────────────────────
async def complete(
    prompt: str,
    *,
    model: str = "gemini-2.5-flash",
    system: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> dict:
    """Call /ai/complete — text generation via Gemini Pro/Flash.

    Returns: {output, model, input_tokens, output_tokens, cost_usd, latency_ms}
    On failure: {error: True, status: int, message: str, output: ""}
    """
    if not ZENI_TOKEN:
        return {"error": True, "status": 0, "message": "ZENI_TOKEN missing", "output": ""}

    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system:
        body["system"] = system

    try:
        async with httpx.AsyncClient(timeout=ZENI_TIMEOUT) as client:
            r = await client.post(
                f"{ZENI_BASE}/ai/complete",
                params={"ws": ZENI_WS},
                headers=_headers(),
                json=body,
            )
            if r.status_code != 200:
                logger.error("[zeni] /ai/complete HTTP %d: %s", r.status_code, r.text[:300])
                return {
                    "error": True,
                    "status": r.status_code,
                    "message": r.text[:500],
                    "output": "",
                }
            data = r.json()
            return {
                "output": data.get("output", ""),
                "model": data.get("model", model),
                "input_tokens": data.get("input_tokens", 0),
                "output_tokens": data.get("output_tokens", 0),
                "cost_usd": data.get("cost_usd", 0),
                "latency_ms": data.get("latency_ms", 0),
            }
    except httpx.HTTPError as e:
        logger.exception("[zeni] /ai/complete network error")
        return {"error": True, "status": 0, "message": str(e), "output": ""}


async def complete_json(
    prompt: str,
    *,
    model: str = "gemini-2.5-flash",
    system: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict | None:
    """Same as complete() but parses JSON output. Returns parsed dict or None."""
    result = await complete(
        prompt,
        model=model,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=True,
    )
    if result.get("error"):
        return None
    return parse_json_response(result.get("output", ""))


# ─── Image generation (Imagen 3) ────────────────────────────────
async def generate_image(
    prompt: str,
    *,
    aspect_ratio: str = "16:9",
    n: int = 1,
    negative_prompt: str | None = None,
) -> list[str]:
    """Call /ai/generate-image — Imagen 3 photorealistic.

    Args:
        prompt: image description
        aspect_ratio: 1:1 | 9:16 | 16:9 | 3:4 | 4:3
        n: 1-4 images
        negative_prompt: things to avoid

    Returns list of data URIs (data:image/png;base64,...) or empty list on failure.
    """
    if not ZENI_TOKEN:
        return []

    body: dict[str, Any] = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "n": max(1, min(4, n)),
    }
    if negative_prompt:
        body["negative_prompt"] = negative_prompt

    try:
        async with httpx.AsyncClient(timeout=ZENI_TIMEOUT) as client:
            r = await client.post(
                f"{ZENI_BASE}/ai/generate-image",
                params={"ws": ZENI_WS},
                headers=_headers(),
                json=body,
            )
            if r.status_code != 200:
                logger.error("[zeni] /ai/generate-image HTTP %d: %s", r.status_code, r.text[:300])
                return []
            data = r.json()
            imgs = data.get("images", []) or []
            return [img.get("data_uri", "") for img in imgs if img.get("data_uri")]
    except httpx.HTTPError as e:
        logger.exception("[zeni] generate_image error: %s", e)
        return []


# ─── Multi-modal image analysis ─────────────────────────────────
async def analyze_image(
    prompt: str,
    *,
    image_url: str | None = None,
    image_data_uri: str | None = None,
    model: str = "gemini-2.5-flash",
    max_tokens: int = 1500,
) -> str:
    """Call /ai/analyze-image — Gemini multi-modal.

    Provide either image_url or image_data_uri (data:image/...).
    Returns the model's text output, or empty string on failure.
    """
    if not ZENI_TOKEN or (not image_url and not image_data_uri):
        return ""

    body: dict[str, Any] = {
        "prompt": prompt,
        "model": model,
        "max_tokens": max_tokens,
    }
    if image_url:
        body["image_url"] = image_url
    if image_data_uri:
        body["image_data_uri"] = image_data_uri

    try:
        async with httpx.AsyncClient(timeout=ZENI_TIMEOUT) as client:
            r = await client.post(
                f"{ZENI_BASE}/ai/analyze-image",
                params={"ws": ZENI_WS},
                headers=_headers(),
                json=body,
            )
            if r.status_code != 200:
                logger.error("[zeni] /ai/analyze-image HTTP %d: %s", r.status_code, r.text[:300])
                return ""
            data = r.json()
            return data.get("output", "")
    except httpx.HTTPError as e:
        logger.exception("[zeni] analyze_image error: %s", e)
        return ""


# ─── Embeddings (for RAG Phase 2) ───────────────────────────────
async def embed(
    texts: list[str],
    *,
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    """Call /ai/embed — text-embedding-004 (768-dim vectors).

    Returns list of vectors (one per text) or empty list on failure.
    """
    if not ZENI_TOKEN or not texts:
        return []

    try:
        async with httpx.AsyncClient(timeout=ZENI_TIMEOUT) as client:
            r = await client.post(
                f"{ZENI_BASE}/ai/embed",
                params={"ws": ZENI_WS},
                headers=_headers(),
                json={"texts": texts, "task_type": task_type},
            )
            if r.status_code != 200:
                logger.error("[zeni] /ai/embed HTTP %d: %s", r.status_code, r.text[:300])
                return []
            data = r.json()
            raw = data.get("embeddings", []) or []
            # ZeniCloud shape: [{"index": 0, "vector": [...], "tokens": N}, ...]
            # Extract .vector and order by .index for stable mapping back to texts.
            if raw and isinstance(raw[0], dict) and "vector" in raw[0]:
                ordered = sorted(raw, key=lambda e: e.get("index", 0))
                return [e.get("vector", []) for e in ordered]
            # Fallback: assume already list[list[float]] (older API or alt provider)
            return raw
    except httpx.HTTPError as e:
        logger.exception("[zeni] embed error: %s", e)
        return []


# ─── Built-in ZeniCloud agents (architecture/structural) ────────
async def architecture_agent_run(
    brief: str,
    *,
    generate_renders: bool = True,
    n_renders: int = 2,
    aspect_ratio: str = "16:9",
    constraints: dict | None = None,
) -> dict:
    """Call /agents/architecture/run — KTS senior level concept + renders.

    Returns: {kind, concept, critique, renders[], tokens, cost_usd}
    On failure: {error: True, status: int, message: str}
    """
    if not ZENI_TOKEN:
        return {"error": True, "status": 0, "message": "ZENI_TOKEN missing"}

    body: dict[str, Any] = {
        "brief": brief,
        "generate_renders": generate_renders,
        "n_renders": max(0, min(4, n_renders)),
        "aspect_ratio": aspect_ratio,
    }
    if constraints:
        body["constraints"] = constraints

    try:
        async with httpx.AsyncClient(timeout=ZENI_TIMEOUT) as client:
            r = await client.post(
                f"{ZENI_BASE}/agents/architecture/run",
                params={"ws": ZENI_WS},
                headers=_headers(),
                json=body,
            )
            if r.status_code != 200:
                logger.error("[zeni] arch agent HTTP %d: %s", r.status_code, r.text[:300])
                return {"error": True, "status": r.status_code, "message": r.text[:500]}
            return r.json()
    except httpx.HTTPError as e:
        logger.exception("[zeni] arch agent error: %s", e)
        return {"error": True, "status": 0, "message": str(e)}


async def architecture_agent_refine(
    previous_concept: str,
    feedback: str,
    *,
    keep_concept: bool = False,
    n_renders: int = 2,
    aspect_ratio: str = "16:9",
) -> dict:
    """Call /agents/architecture/refine — iterative refinement of an existing concept."""
    if not ZENI_TOKEN:
        return {"error": True, "status": 0, "message": "ZENI_TOKEN missing"}

    try:
        async with httpx.AsyncClient(timeout=ZENI_TIMEOUT) as client:
            r = await client.post(
                f"{ZENI_BASE}/agents/architecture/refine",
                params={"ws": ZENI_WS},
                headers=_headers(),
                json={
                    "previous_concept": previous_concept,
                    "feedback": feedback,
                    "keep_concept": keep_concept,
                    "n_renders": max(0, min(4, n_renders)),
                    "aspect_ratio": aspect_ratio,
                },
            )
            if r.status_code != 200:
                logger.error("[zeni] arch refine HTTP %d: %s", r.status_code, r.text[:300])
                return {"error": True, "status": r.status_code, "message": r.text[:500]}
            return r.json()
    except httpx.HTTPError as e:
        logger.exception("[zeni] arch refine error: %s", e)
        return {"error": True, "status": 0, "message": str(e)}


async def structural_agent_run(
    brief: str,
    *,
    constraints: dict | None = None,
    generate_renders: bool = False,
) -> dict:
    """Call /agents/structural/run — PE engineer with TCVN compliance check."""
    if not ZENI_TOKEN:
        return {"error": True, "status": 0, "message": "ZENI_TOKEN missing"}

    body: dict[str, Any] = {
        "brief": brief,
        "generate_renders": generate_renders,
    }
    if constraints:
        body["constraints"] = constraints

    try:
        async with httpx.AsyncClient(timeout=ZENI_TIMEOUT) as client:
            r = await client.post(
                f"{ZENI_BASE}/agents/structural/run",
                params={"ws": ZENI_WS},
                headers=_headers(),
                json=body,
            )
            if r.status_code != 200:
                logger.error("[zeni] struct agent HTTP %d: %s", r.status_code, r.text[:300])
                return {"error": True, "status": r.status_code, "message": r.text[:500]}
            return r.json()
    except httpx.HTTPError as e:
        logger.exception("[zeni] struct agent error: %s", e)
        return {"error": True, "status": 0, "message": str(e)}


# ─── Email (replaces Gmail SMTP / Vercel serverless) ──────────
async def send_email(
    to: str | list[str],
    subject: str,
    body_html: str,
    *,
    body_text: str | None = None,
    from_name: str | None = None,
    reply_to: str | None = None,
) -> dict:
    """Call /email/send — ZeniCloud transactional email.

    Pro tier: 2000 emails/day, 100 VND/email.
    Returns: {sent, failed, cost_vnd, message_ids, quota_remaining_today}
    On failure: {error: True, status: int, message: str}
    """
    if not ZENI_TOKEN:
        return {"error": True, "status": 0, "message": "ZENI_TOKEN missing"}

    body: dict[str, Any] = {
        "to": to if isinstance(to, str) else to,
        "subject": subject,
        "body_html": body_html,
    }
    if body_text:
        body["body_text"] = body_text
    if from_name:
        body["from_name"] = from_name
    if reply_to:
        body["reply_to"] = reply_to

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{ZENI_BASE}/email/send",
                params={"ws": ZENI_WS},
                headers=_headers(),
                json=body,
            )
            if r.status_code != 200:
                logger.error("[zeni] /email/send HTTP %d: %s", r.status_code, r.text[:300])
                return {"error": True, "status": r.status_code, "message": r.text[:500]}
            return r.json()
    except httpx.HTTPError as e:
        logger.exception("[zeni] send_email error: %s", e)
        return {"error": True, "status": 0, "message": str(e)}


async def get_email_quota() -> dict:
    """Check daily email quota."""
    if not ZENI_TOKEN:
        return {"error": True, "message": "ZENI_TOKEN missing"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{ZENI_BASE}/email/quota",
                params={"ws": ZENI_WS},
                headers=_headers(),
            )
            return r.json() if r.status_code == 200 else {"error": True, "status": r.status_code}
    except httpx.HTTPError as e:
        return {"error": True, "message": str(e)}


# ─── Health / quota ─────────────────────────────────────────────
async def get_subscription() -> dict:
    """Check current quota usage."""
    if not ZENI_TOKEN:
        return {"error": True, "message": "ZENI_TOKEN missing"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{ZENI_BASE}/billing/subscription",
                params={"ws": ZENI_WS},
                headers=_headers(),
            )
            return r.json() if r.status_code == 200 else {"error": True, "status": r.status_code}
    except httpx.HTTPError as e:
        return {"error": True, "message": str(e)}
