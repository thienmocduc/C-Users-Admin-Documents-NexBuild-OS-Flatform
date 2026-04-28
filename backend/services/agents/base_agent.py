"""BaseAgent — calls ZeniCloud /ai/complete (gateway to 6 LLMs).

All discipline agents (Interior, Architecture, Structural) inherit from this.
Subclasses override `discipline`, `system_prompt`, `build_user_prompt()`,
`fallback_response()`, and optionally `enrich_response()`.

Migrated from direct Gemini API → ZeniCloud unified gateway 2026-04-27.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from api.services import rag_service, zenicloud_service as zc

logger = logging.getLogger(__name__)

# Default model for agents — Gemini Flash via ZeniCloud (best $/quality)
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")
# Fallback to legacy Gemini direct when ZENI_TOKEN missing (dev only)
LEGACY_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
# Phase 2 — RAG toggle (default on)
RAG_ENABLED = os.getenv("RAG_ENABLED", "1") == "1"
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))


class BaseAgent:
    """Base class — every discipline agent extends this."""

    discipline: str = "base"
    system_prompt: str = ""
    temperature: float = 0.8
    max_output_tokens: int = 8192
    model: str = AGENT_MODEL

    # ────────────────────────────────────────────────────────────
    # Public API — subclasses override the 3 hooks below
    # ────────────────────────────────────────────────────────────
    def build_user_prompt(self, request: Any) -> str:
        """Build the user-facing prompt from a GenerateRequest."""
        raise NotImplementedError

    def fallback_response(self, request: Any) -> dict:
        """Return demo data when ZeniCloud unavailable or fails."""
        raise NotImplementedError

    def enrich_response(self, raw: dict, request: Any) -> dict:
        """Post-process LLM output (validate prices, add KB references)."""
        return raw

    # ────────────────────────────────────────────────────────────
    # Main entrypoint
    # ────────────────────────────────────────────────────────────
    async def generate(self, request: Any) -> dict:
        """Call ZeniCloud /ai/complete → parse JSON → enrich → return.

        Phase 2: prepends RAG-retrieved KB context to user_prompt for richer output.
        """
        if not zc.is_configured():
            logger.warning("[%s] ZENI_TOKEN missing — using fallback", self.discipline)
            return self.fallback_response(request)

        user_prompt = self.build_user_prompt(request)

        # ── Phase 2 — RAG: retrieve relevant KB docs and inject ────
        rag_block = ""
        rag_docs: list[dict[str, Any]] = []
        if RAG_ENABLED:
            try:
                # Build query from user input fields
                query_parts = [
                    getattr(request, "prompt", "") or "",
                    getattr(request, "style", "") or "",
                    getattr(request, "room_type", "") or "",
                ]
                rag_query = " ".join(p for p in query_parts if p)[:500]
                if rag_query:
                    rag_docs = await rag_service.retrieve_relevant_kb(
                        rag_query, discipline=self.discipline, top_k=RAG_TOP_K,
                    )
                    rag_block = rag_service.format_rag_context(rag_docs)
            except Exception as e:
                logger.warning("[%s] RAG retrieval failed (non-fatal): %s", self.discipline, e)

        if rag_block:
            user_prompt = f"{rag_block}\n\n────────\n\n{user_prompt}"

        result = await zc.complete(
            prompt=user_prompt,
            system=self.system_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
            json_mode=True,
        )

        if result.get("error"):
            logger.error(
                "[%s] generate failed (HTTP %s): %s",
                self.discipline, result.get("status"), result.get("message", "")[:200],
            )
            return self.fallback_response(request)

        raw = zc.parse_json_response(result.get("output", ""))
        if not raw:
            logger.error("[%s] LLM returned non-JSON: %s", self.discipline, result.get("output", "")[:200])
            return self.fallback_response(request)

        # Track tokens used for billing/observability
        raw["_meta"] = {
            "model": result.get("model"),
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "cost_usd": result.get("cost_usd", 0),
            "latency_ms": result.get("latency_ms", 0),
            "provider": "zenicloud",
            "rag_docs_used": len(rag_docs),
            "rag_doc_ids": [d["id"] for d in rag_docs],
        }

        return self.enrich_response(raw, request)

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
        """Refine an existing design based on user feedback via ZeniCloud."""
        if not zc.is_configured():
            logger.warning("[%s] refine fallback (ZENI_TOKEN missing)", self.discipline)
            fallback = self.fallback_response(request)
            fallback["refinement_demo"] = True
            return fallback

        refine_prompt = self.build_refine_prompt(
            parent_output, parent_variant_idx, feedback, round_num
        )

        result = await zc.complete(
            prompt=refine_prompt,
            system=self.system_prompt,
            model=self.model,
            temperature=0.6,  # lower temp for refinement = more controlled
            max_tokens=self.max_output_tokens,
            json_mode=True,
        )

        if result.get("error"):
            logger.error("[%s] refine failed: %s", self.discipline, result.get("message", "")[:200])
            return self.fallback_response(request)

        raw = zc.parse_json_response(result.get("output", ""))
        if not raw:
            logger.error("[%s] refine returned non-JSON", self.discipline)
            return self.fallback_response(request)

        raw["_meta"] = {
            "model": result.get("model"),
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "cost_usd": result.get("cost_usd", 0),
            "latency_ms": result.get("latency_ms", 0),
            "provider": "zenicloud",
            "refine_round": round_num,
        }

        return self.enrich_response(raw, request)

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
        s = str(value).strip() if value is not None else ""
        return s if s else default

    @staticmethod
    def clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))
