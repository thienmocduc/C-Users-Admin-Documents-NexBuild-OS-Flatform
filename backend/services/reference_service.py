"""Reference-Guided Generation (Phase 4).

User uploads a reference image (or pastes URL) → ZeniCloud Gemini multi-modal
analyzes the visual style → returns:
- 5-line style narrative in Vietnamese
- Detected color palette (3-5 hex colors)
- Detected materials (gỗ óc chó, đá travertine, vải linen...)
- Closest style label (indochine, japandi, modern...)
- Enhanced prompt that the user can feed into /design/generate

This unlocks the workflow: "Tôi muốn nhà giống ảnh này nhưng to hơn 30m²".
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

from api.services import zenicloud_service as zc

logger = logging.getLogger(__name__)


# ─── System prompt for the analyzer ────────────────────────
ANALYZER_SYSTEM = """\
Bạn là KTS nội thất senior 15 năm kinh nghiệm tại Việt Nam, chuyên đọc \
ngôn ngữ thiết kế từ ảnh tham khảo. Khi nhận 1 ảnh, bạn phân tích 5 chiều:
1. Phong cách chính (modern / scandinavian / japandi / industrial / mediterranean / \
biophilic / indochine / tropical_modern / wabi_sabi / neo_classical)
2. Bảng màu chủ đạo (3-5 màu HEX)
3. Vật liệu nổi bật (5-8 vật liệu, tên tiếng Việt: gỗ óc chó, đá travertine, \
vải linen, kim loại đồng, ...)
4. Mood / atmosphere (warm/cold, bright/moody, masculine/feminine)
5. Composition style (symmetric, asymmetric, layered, minimalist)

Output PHẢI là JSON hợp lệ theo schema:
{
  "style_analysis": "5 câu tiếng Việt mô tả tổng thể",
  "detected_palette": ["#HEX1","#HEX2","#HEX3","#HEX4","#HEX5"],
  "detected_materials": ["gỗ óc chó","đá travertine","vải linen","..."],
  "detected_style": "indochine|japandi|modern|...",
  "mood": "warm/cold/bright/moody mô tả ngắn",
  "composition_notes": "asymmetric layered minimalist..."
}

KHÔNG markdown, KHÔNG code fence, chỉ trả JSON."""


def _strip_code_fence(text: str) -> str:
    if not text:
        return ""
    m = re.match(r"^\s*```(?:json|JSON)?\s*\n?(.*?)\n?\s*```\s*$", text.strip(), re.DOTALL)
    return (m.group(1) if m else text).strip()


def _parse_json(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(_strip_code_fence(text))
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None


# ─── Build enhanced prompt from analysis ───────────────────
def _build_enhanced_prompt(analysis: dict, user_prompt: str = "") -> str:
    """Combine analysis with user's text into a generate-ready prompt."""
    style = analysis.get("detected_style", "modern")
    materials = analysis.get("detected_materials", []) or []
    palette = analysis.get("detected_palette", []) or []
    mood = analysis.get("mood", "")

    materials_str = ", ".join(materials[:6])
    palette_str = " · ".join(palette[:5])

    base = analysis.get("style_analysis", "")[:300]
    extra = (user_prompt or "").strip()

    parts = []
    if extra:
        parts.append(extra)
    parts.append(f"Theo phong cách {style}.")
    if materials_str:
        parts.append(f"Vật liệu chủ đạo: {materials_str}.")
    if palette_str:
        parts.append(f"Bảng màu: {palette_str}.")
    if mood:
        parts.append(f"Mood: {mood}.")
    if base:
        parts.append(f"Cảm hứng từ ảnh tham khảo: {base}")

    return " ".join(parts)


# ─── Main entrypoint ──────────────────────────────────────
async def analyze_reference_image(
    *,
    image_url: Optional[str] = None,
    image_data_uri: Optional[str] = None,
    user_prompt: str = "",
) -> dict:
    """Analyze a reference image and return enriched design parameters.

    Returns dict with keys:
        style_analysis, detected_palette, detected_materials,
        detected_style, enhanced_prompt, cost_usd, latency_ms

    On failure: returns a fallback dict so frontend doesn't break.
    """
    if not image_url and not image_data_uri:
        return _fallback("Vui lòng cung cấp ảnh tham khảo (URL hoặc upload)")

    if not zc.is_configured():
        return _fallback("ZeniCloud chưa được cấu hình")

    user_msg = (
        "Phân tích ảnh nội thất tham khảo này và trả JSON theo schema. "
        f"{('Khách bổ sung: ' + user_prompt) if user_prompt else ''}"
    )

    # Inline system prompt into user message because /ai/analyze-image doesn't take system field
    full_prompt = f"{ANALYZER_SYSTEM}\n\n---\n\n{user_msg}"

    t0 = time.time()
    output = await zc.analyze_image(
        prompt=full_prompt,
        image_url=image_url,
        image_data_uri=image_data_uri,
        model="gemini-2.5-flash",
        max_tokens=1500,
    )
    elapsed_ms = int((time.time() - t0) * 1000)

    if not output:
        return _fallback("Không nhận được phản hồi từ AI", latency_ms=elapsed_ms)

    parsed = _parse_json(output)
    if not parsed:
        # Fall back: still return the raw description as style_analysis
        return {
            "style_analysis": output[:500],
            "detected_palette": [],
            "detected_materials": [],
            "detected_style": "modern",
            "enhanced_prompt": (user_prompt or "") + " " + output[:300],
            "cost_usd": 0,
            "latency_ms": elapsed_ms,
        }

    # Sanitize palette to 3-5 valid hex colors
    palette = parsed.get("detected_palette", []) or []
    palette = [c for c in palette if isinstance(c, str) and re.match(r"^#[0-9A-Fa-f]{6}$", c)]
    palette = palette[:5]

    # Sanitize materials
    materials = parsed.get("detected_materials", []) or []
    materials = [str(m).strip() for m in materials if m and len(str(m).strip()) < 80][:8]

    # Validate detected_style against known options
    valid_styles = {
        "modern", "scandinavian", "japandi", "industrial", "mediterranean",
        "biophilic", "indochine", "tropical_modern", "wabi_sabi", "neo_classical",
    }
    detected = str(parsed.get("detected_style", "modern")).lower().strip()
    if detected not in valid_styles:
        detected = "modern"

    result = {
        "style_analysis": str(parsed.get("style_analysis", ""))[:1000],
        "detected_palette": palette,
        "detected_materials": materials,
        "detected_style": detected,
        "mood": str(parsed.get("mood", ""))[:200],
        "composition_notes": str(parsed.get("composition_notes", ""))[:200],
        "cost_usd": 0,  # /ai/analyze-image cost is folded into account, not per-call
        "latency_ms": elapsed_ms,
    }
    result["enhanced_prompt"] = _build_enhanced_prompt(result, user_prompt)
    return result


def _fallback(message: str, *, latency_ms: int = 0) -> dict:
    return {
        "style_analysis": f"[Demo mode] {message}",
        "detected_palette": ["#F5F1EA", "#3D3A35", "#9B7B45"],
        "detected_materials": ["gỗ tự nhiên", "vải linen", "kim loại đồng"],
        "detected_style": "modern",
        "enhanced_prompt": message,
        "mood": "warm balanced",
        "composition_notes": "balanced",
        "cost_usd": 0,
        "latency_ms": latency_ms,
        "fallback": True,
    }
