"""BaseAgent — shared Gemini client + JSON parsing + retry logic.

All discipline agents (Interior, Architecture, Structural) inherit from this
class and override `discipline`, `system_prompt`, `build_user_prompt()`, and
`enrich_response()`.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "60"))


class BaseAgent:
    """Base class — every discipline agent extends this."""

    discipline: str = "base"
    system_prompt: str = ""
    temperature: float = 0.8
    max_output_tokens: int = 8192

    # ────────────────────────────────────────────────────────────
    # Public API — subclasses override the 3 hooks below
    # ────────────────────────────────────────────────────────────
    def build_user_prompt(self, request: Any) -> str:
        """Build the user-facing prompt from a GenerateRequest."""
        raise NotImplementedError

    def fallback_response(self, request: Any) -> dict:
        """Return demo data when Gemini API key is missing or fails."""
        raise NotImplementedError

    def enrich_response(self, raw: dict, request: Any) -> dict:
        """Post-process Gemini output (validate prices, add KB references)."""
        return raw

    # ────────────────────────────────────────────────────────────
    # Main entrypoint
    # ────────────────────────────────────────────────────────────
    async def generate(self, request: Any) -> dict:
        """Call Gemini → parse JSON → enrich → return."""
        if not GEMINI_API_KEY:
            logger.warning("[%s] GEMINI_API_KEY missing — using fallback", self.discipline)
            return self.fallback_response(request)

        user_prompt = self.build_user_prompt(request)
        full_prompt = self.system_prompt + "\n\n---\n\n" + user_prompt

        try:
            async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT) as client:
                resp = await client.post(
                    GEMINI_URL,
                    params={"key": GEMINI_API_KEY},
                    json={
                        "contents": [
                            {"role": "user", "parts": [{"text": full_prompt}]}
                        ],
                        "generationConfig": {
                            "temperature": self.temperature,
                            "topP": 0.95,
                            "maxOutputTokens": self.max_output_tokens,
                            "responseMimeType": "application/json",
                        },
                    },
                )

                if resp.status_code != 200:
                    logger.error(
                        "[%s] Gemini HTTP %d: %s",
                        self.discipline, resp.status_code, resp.text[:300]
                    )
                    return self.fallback_response(request)

                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                raw = json.loads(text)
                return self.enrich_response(raw, request)
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as e:
            logger.exception("[%s] generate failed: %s", self.discipline, e)
            return self.fallback_response(request)

    # ────────────────────────────────────────────────────────────
    # Iterative refinement — Phase 5
    # ────────────────────────────────────────────────────────────
    def build_refine_prompt(
        self, parent_output: dict, parent_variant_idx: int, feedback: str, round_num: int
    ) -> str:
        """Build a refinement user-prompt that asks the model to apply
        ONLY the requested change while preserving everything else.

        Subclasses can override for discipline-specific framing.
        """
        # Extract relevant variant context (compact, ≤ 1500 chars)
        variants = parent_output.get("variants") or parent_output.get("concept_variants") or []
        target_variant = (
            variants[parent_variant_idx]
            if 0 <= parent_variant_idx < len(variants)
            else (variants[0] if variants else {})
        )
        boq_summary = self._summarize_boq(parent_output)
        scene_summary = self._summarize_scene(parent_output)

        return f"""\
ĐÂY LÀ DESIGN HIỆN TẠI (round {round_num - 1}, đã được khách duyệt 1 phần):

VARIANT ĐÃ CHỌN ({parent_variant_idx}):
- Style: {target_variant.get('style_label') or target_variant.get('concept_name', '?')}
- Mô tả: {(target_variant.get('description') or '')[:500]}
- Materials: {", ".join(target_variant.get('key_materials', []) or [])[:300]}

BOQ HIỆN TẠI (tóm tắt):
{boq_summary}

SCENE 3D (tóm tắt):
{scene_summary}

────────────────────────────────────────
PHẢN HỒI CỦA KHÁCH (round {round_num}):
"{feedback}"
────────────────────────────────────────

YÊU CẦU REFINE:
1. CHỈ thay đổi PHẦN khách yêu cầu trong feedback (không refactor toàn bộ).
2. Giữ NGUYÊN style chính, palette, layout cơ bản — chỉ adjust theo feedback.
3. Cập nhật BOQ tương ứng nếu thêm/đổi vật liệu (ví dụ feedback "thêm cây xanh"
   → thêm 2-3 chậu cây vào BOQ, không xoá BOQ cũ).
4. Cập nhật scene_3d nếu thêm/đổi furniture.
5. Trong trường style_label/concept_name, ĐÁNH DẤU "(refined v{round_num})".
6. Output PHẢI là JSON theo SCHEMA gốc của discipline này (cùng shape như
   lần generate đầu) — KHÔNG dùng schema khác.
7. Số variants có thể GIẢM xuống 1-2 (vì user chỉ refine variant đã chọn).

Trả về JSON hợp lệ."""

    def _summarize_boq(self, parent: dict, max_items: int = 10) -> str:
        """Compact BOQ summary for refine prompt."""
        items = parent.get("boq_items") or parent.get("boq_structural") or []
        if not items:
            return "(trống)"
        lines = []
        for it in items[:max_items]:
            name = it.get("product_name") or it.get("item") or "?"
            qty = it.get("quantity") or it.get("qty", "?")
            unit = it.get("unit", "")
            price = it.get("total_price", 0)
            lines.append(f"  - {name[:60]} x {qty}{unit} = {price:,} VND")
        if len(items) > max_items:
            lines.append(f"  ... +{len(items) - max_items} items khác")
        return "\n".join(lines)

    def _summarize_scene(self, parent: dict, max_items: int = 5) -> str:
        """Compact scene_3d summary."""
        s = parent.get("scene_3d") or {}
        room = s.get("room", {})
        furniture = s.get("furniture", []) or []
        lines = [
            f"  Room: {room.get('width_m','?')}×{room.get('depth_m','?')}×{room.get('height_m','?')}m",
            f"  Floor: {s.get('floor', '?')}",
            f"  Walls: {s.get('walls', '?')}",
        ]
        if furniture:
            lines.append(f"  Furniture ({len(furniture)} items):")
            for f in furniture[:max_items]:
                lines.append(f"    - {f.get('type','?')}: {f.get('name','?')}")
        return "\n".join(lines)

    async def refine(
        self,
        parent_output: dict,
        parent_variant_idx: int,
        feedback: str,
        round_num: int,
        request: Any,
    ) -> dict:
        """Refine an existing design based on user feedback.

        Same pipeline as generate() but with refine prompt + parent context.
        """
        if not GEMINI_API_KEY:
            logger.warning("[%s] refine fallback (no API key)", self.discipline)
            # Mark fallback so frontend shows demo banner
            fallback = self.fallback_response(request)
            fallback["refinement_demo"] = True
            return fallback

        refine_prompt = self.build_refine_prompt(
            parent_output, parent_variant_idx, feedback, round_num
        )
        full_prompt = self.system_prompt + "\n\n---\n\n" + refine_prompt

        try:
            async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT) as client:
                resp = await client.post(
                    GEMINI_URL,
                    params={"key": GEMINI_API_KEY},
                    json={
                        "contents": [
                            {"role": "user", "parts": [{"text": full_prompt}]}
                        ],
                        "generationConfig": {
                            "temperature": 0.6,  # Lower temp for refinement = more controlled
                            "topP": 0.9,
                            "maxOutputTokens": self.max_output_tokens,
                            "responseMimeType": "application/json",
                        },
                    },
                )
                if resp.status_code != 200:
                    logger.error("[%s] refine HTTP %d: %s", self.discipline, resp.status_code, resp.text[:300])
                    return self.fallback_response(request)
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                raw = json.loads(text)
                return self.enrich_response(raw, request)
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as e:
            logger.exception("[%s] refine failed: %s", self.discipline, e)
            return self.fallback_response(request)

    # ────────────────────────────────────────────────────────────
    # Helper utilities for subclasses
    # ────────────────────────────────────────────────────────────
    @staticmethod
    def vnd_int(value: Any, default: int = 0) -> int:
        """Coerce value to int VND, never negative."""
        try:
            v = int(float(value))
            return v if v > 0 else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def safe_str(value: Any, default: str = "") -> str:
        """Coerce to non-empty string."""
        s = str(value).strip() if value is not None else ""
        return s if s else default

    @staticmethod
    def clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))
