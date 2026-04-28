"""Multi-stage Pipeline (Phase 3) — PLAN → SKETCH → RENDER → SELECT.

Replaces the single-shot agent.generate() with a 4-stage pipeline that produces
hyper-detailed output (concept → structured spec → 4 photoreal renders →
AI-curated top 2). Each stage uses a different model/temperature for the right
trade-off between creativity and precision.

Stages:
  1. PLAN     — gemini-2.5-pro analyzes brief → strict structured spec (JSON)
                temperature 0.4, max_tokens 4096
  2. SKETCH   — gemini-2.5-flash expands spec → 4 distinct variant prompts
                temperature 0.85 (creative), max_tokens 3072
  3. RENDER   — Imagen 3 generates 4 photorealistic interior renders 16:9
                each variant prompt → 1 image, parallelized
  4. SELECT   — gemini-2.5-flash multi-modal scores 4 renders → picks top 2
                + writes critique (3 ưu / 3 nhược / 3 cải tiến) per pick

Output is shape-compatible with single-shot generate() → existing frontend
adapters work without changes. Stage timings + cost recorded in _meta.

Toggle via env: MULTISTAGE_ENABLED=1 (default off — single-shot is faster/cheaper).
Recommended for Pro tier or when user explicitly clicks "High quality".
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from api.services import zenicloud_service as zc

logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────
_CODE_FENCE_RE = re.compile(r"^\s*```(?:json|JSON)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def _strip_fence(text: str) -> str:
    if not text:
        return ""
    m = _CODE_FENCE_RE.match(text.strip())
    return (m.group(1) if m else text).strip()


def _parse_json(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(_strip_fence(text))
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


# ─── Stage 1: PLAN ─────────────────────────────────────────
PLAN_SYSTEM = """\
Bạn là KTS senior 20 năm. NHIỆM VỤ: phân tích brief khách → trả về STRUCTURED \
SPEC dạng JSON CHÍNH XÁC (không sáng tạo, chỉ cấu trúc hoá). Output JSON:
{
  "design_intent": "1 câu thâu tóm ý đồ thiết kế",
  "key_constraints": {
    "area_m2": float,
    "style_primary": "indochine|japandi|modern|...",
    "palette_direction": "warm|cool|neutral|earth|monochrome",
    "budget_tier": "co_so|trung_cap|cao_cap|luxury",
    "must_have": ["sofa","tủ TV","..."],
    "must_avoid": ["nội thất nhập khẩu đắt","..."]
  },
  "spatial_zones": [
    {"zone": "khu tiếp khách", "area_pct": 40, "function": "đón khách + xem TV"},
    ...
  ],
  "lighting_strategy": {
    "key": "...", "fill": "...", "accent": "..."
  },
  "material_priority": ["sàn gỗ","sơn tường","trần thạch cao","..."],
  "deliverable_focus": "render|boq|3d_scene"
}
KHÔNG markdown, chỉ JSON."""


async def stage_plan(brief: str, request_meta: dict) -> dict:
    """Stage 1 — strict structured analysis of the brief."""
    user_prompt = f"""\
BRIEF KHÁCH:
{brief}

THÔNG SỐ:
- Diện tích: {request_meta.get('area_m2', '?')}m²
- Phong cách: {request_meta.get('style', '?')}
- Phòng: {request_meta.get('room_type', '?')}
- Ngân sách: {request_meta.get('budget_million', '?')} triệu VND

Phân tích → trả JSON theo schema."""
    result = await zc.complete(
        prompt=user_prompt,
        system=PLAN_SYSTEM,
        model="gemini-2.5-pro",  # reasoning-heavy stage uses Pro
        temperature=0.4,
        max_tokens=4096,
    )
    if result.get("error"):
        return {"error": True, "message": result.get("message", ""), "stage": "plan"}
    parsed = _parse_json(result.get("output", ""))
    return {
        "spec": parsed or {},
        "raw_output": result.get("output", "")[:1000],
        "input_tokens": result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
        "cost_usd": result.get("cost_usd", 0),
        "latency_ms": result.get("latency_ms", 0),
    }


# ─── Stage 2: SKETCH ───────────────────────────────────────
SKETCH_SYSTEM = """\
Bạn là KTS thiết kế concept. Nhận STRUCTURED SPEC từ stage PLAN, sáng tạo 4 \
PHƯƠNG ÁN khác nhau RÕ RỆT về parti/atmosphere (không chỉ khác palette).
Mỗi phương án trả về:
{
  "variant_idx": 0-3,
  "style_label": "Tên phương án giàu hình ảnh, vd 'Indochine Lụa Hà Đông' hoặc 'Japandi Sương Sớm'",
  "description": "150-250 chữ mô tả không gian — như đứng giữa phòng cảm nhận",
  "key_materials": ["vật liệu 1","vật liệu 2","..."],
  "render_prompt": "1500+ chars detailed prompt cho Imagen — gồm MASTER SHOT, \
SCENE COMPOSITION, MATERIALS PRECISE (brand+spec), FURNITURE SPECIFIC, \
LIGHTING (3-point + Kelvin), CAMERA (focal+aperture+ISO), POST-PROCESSING, \
NEGATIVE PROMPT"
}
Output JSON:
{
  "variants": [4 phương án theo schema trên]
}
Mỗi phương án PHẢI có render_prompt ĐÁNG TIN CẬY 1500+ chars cho Imagen 3."""


async def stage_sketch(plan_spec: dict, brief: str) -> dict:
    """Stage 2 — generate 4 distinct variant concepts + detailed image prompts."""
    user_prompt = f"""\
STRUCTURED SPEC (từ stage PLAN):
{json.dumps(plan_spec, ensure_ascii=False, indent=2)}

BRIEF GỐC: {brief[:500]}

→ Tạo 4 phương án khác nhau RÕ RỆT về parti/mood. Mỗi phương án có \
render_prompt 1500+ chars sẵn sàng feed Imagen 3."""
    result = await zc.complete(
        prompt=user_prompt,
        system=SKETCH_SYSTEM,
        model="gemini-2.5-flash",  # Flash đủ cho tạo prompt
        temperature=0.85,
        max_tokens=8192,
    )
    if result.get("error"):
        return {"error": True, "message": result.get("message", ""), "stage": "sketch"}
    parsed = _parse_json(result.get("output", ""))
    variants = (parsed or {}).get("variants", [])
    return {
        "variants": variants,
        "input_tokens": result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
        "cost_usd": result.get("cost_usd", 0),
        "latency_ms": result.get("latency_ms", 0),
    }


# ─── Stage 3: RENDER ───────────────────────────────────────
async def stage_render(variants: list[dict]) -> list[dict]:
    """Stage 3 — generate Imagen 3 renders for each variant in parallel.

    Modifies variants in-place adding `image_url` (data URI base64).
    """
    async def _render_one(v: dict) -> None:
        prompt = v.get("render_prompt") or v.get("description", "")
        if not prompt:
            return
        try:
            urls = await zc.generate_image(
                prompt=prompt[:4000],  # Imagen has prompt length cap
                aspect_ratio="16:9",
                n=1,
                negative_prompt=(
                    "blurry, distorted perspective, oversaturated, AI artifacts, "
                    "deformed, extra limbs, mannequin people, plastic textures, "
                    "cartoonish, generic stock photo, low resolution"
                ),
            )
            v["image_url"] = urls[0] if urls else None
        except Exception as e:
            logger.warning("[multistage] render failed for variant %s: %s", v.get("variant_idx"), e)
            v["image_url"] = None

    t0 = time.time()
    await asyncio.gather(*[_render_one(v) for v in variants])
    return variants


# ─── Stage 4: SELECT ───────────────────────────────────────
SELECT_SYSTEM = """\
Bạn là KTS senior chấm bài. Có 4 phương án thiết kế (mỗi phương án 1 ảnh + \
mô tả). Hãy chấm theo 5 tiêu chí: (1) Đúng brief, (2) Tính thẩm mỹ, \
(3) Khả thi thi công VN, (4) Phù hợp ngân sách, (5) Tính sáng tạo.

Output JSON:
{
  "ranking": [variant_idx tốt nhất trước, kém nhất sau],
  "top_picks": [variant_idx top 1, variant_idx top 2],
  "critique": {
    "0": {"score": 7.5, "pros": ["..."], "cons": ["..."], "improvements": ["..."]},
    "1": {...}, "2": {...}, "3": {...}
  },
  "recommendation": "Khuyên khách chọn phương án X vì ..."
}
Mỗi pros/cons/improvements có 3 mục. KHÔNG markdown, chỉ JSON."""


async def stage_select(variants: list[dict], brief: str) -> dict:
    """Stage 4 — score variants and pick top 2 with critique."""
    if len(variants) < 2:
        return {"top_picks": [0], "critique": {}, "recommendation": ""}

    # Build a comparison prompt — text-only since not all variants may have images
    summary = "\n\n".join([
        f"Variant {v.get('variant_idx', i)}:\n"
        f"  Style: {v.get('style_label', '?')}\n"
        f"  Description: {(v.get('description') or '')[:400]}\n"
        f"  Has image: {'yes' if v.get('image_url') else 'no'}"
        for i, v in enumerate(variants)
    ])
    user_prompt = f"""\
BRIEF KHÁCH: {brief[:500]}

4 PHƯƠNG ÁN ĐỀ XUẤT:
{summary}

Chấm điểm 5 tiêu chí, pick top 2, viết critique chi tiết."""
    result = await zc.complete(
        prompt=user_prompt,
        system=SELECT_SYSTEM,
        model="gemini-2.5-flash",
        temperature=0.5,
        max_tokens=3072,
    )
    if result.get("error"):
        return {"top_picks": [0, 1], "critique": {}, "recommendation": "", "error": result.get("message")}
    parsed = _parse_json(result.get("output", "")) or {}
    return {
        "ranking": parsed.get("ranking", []),
        "top_picks": parsed.get("top_picks", [0, 1])[:2],
        "critique": parsed.get("critique", {}),
        "recommendation": parsed.get("recommendation", ""),
        "input_tokens": result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
        "cost_usd": result.get("cost_usd", 0),
        "latency_ms": result.get("latency_ms", 0),
    }


# ─── Orchestrator ─────────────────────────────────────────
async def run_multistage(
    brief: str,
    request_meta: dict,
    *,
    skip_render: bool = False,
) -> dict:
    """Run full PLAN→SKETCH→RENDER→SELECT pipeline.

    Returns shape-compatible with single-shot generate():
        {
            "variants": [4 enriched variants with image_url + rank],
            "boq_items": [],  # multistage doesn't generate BOQ — call generate() for that
            "scene_3d": null,
            "multistage": {
                "plan": {spec, tokens, cost},
                "sketch": {tokens, cost},
                "render": {durations_ms, success_count},
                "select": {top_picks, critique, recommendation, cost},
                "total_cost_usd": X,
                "total_latency_ms": Y,
            }
        }
    """
    if not zc.is_configured():
        return {"error": True, "message": "ZeniCloud chưa cấu hình"}

    overall_t0 = time.time()
    total_cost = 0.0

    # Stage 1
    plan = await stage_plan(brief, request_meta)
    if plan.get("error"):
        return {"error": True, "stage": "plan", "message": plan.get("message")}
    total_cost += plan.get("cost_usd", 0)

    # Stage 2
    sketch = await stage_sketch(plan["spec"], brief)
    if sketch.get("error") or not sketch.get("variants"):
        return {"error": True, "stage": "sketch", "message": sketch.get("message", "no variants")}
    total_cost += sketch.get("cost_usd", 0)
    variants = sketch["variants"]

    # Stage 3 (parallel image renders)
    if not skip_render:
        await stage_render(variants)

    # Stage 4
    selection = await stage_select(variants, brief)
    total_cost += selection.get("cost_usd", 0)

    # Mark top picks on variants
    top_picks = set(selection.get("top_picks", []))
    for v in variants:
        idx = v.get("variant_idx")
        v["is_top_pick"] = idx in top_picks
        crit = (selection.get("critique") or {}).get(str(idx))
        if crit:
            v["critique"] = crit

    return {
        "variants": variants,
        "prompt_enhanced": plan["spec"].get("design_intent", brief)[:300],
        "boq_items": [],
        "scene_3d": None,
        "multistage": {
            "plan_spec": plan["spec"],
            "sketch_tokens": sketch.get("output_tokens", 0),
            "render_count": sum(1 for v in variants if v.get("image_url")),
            "select_recommendation": selection.get("recommendation", ""),
            "select_ranking": selection.get("ranking", []),
            "total_cost_usd": round(total_cost, 6),
            "total_latency_ms": int((time.time() - overall_t0) * 1000),
        },
    }
