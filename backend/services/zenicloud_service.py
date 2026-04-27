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
_CODE_FENCE_RE = re.compile(r"^\s*```(?:json|JSON)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def strip_code_fence(text: str) -> str:
    """Strip ```json ... ``` wrapper that Gemini sometimes adds."""
    if not text:
        return ""
    m = _CODE_FENCE_RE.match(text.strip())
    return m.group(1).strip() if m else text.strip()


def parse_json_response(text: str) -> dict | None:
    """Parse JSON from LLM output, handling code fences + extra prose."""
    cleaned = strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find first JSON object in the text
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
            return data.get("embeddings", []) or []
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
