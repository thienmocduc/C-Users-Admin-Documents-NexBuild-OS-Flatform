"""RAG service (Phase 2) — embed knowledge base + retrieve top-K similar items.

How it works:
1. On startup (lazy), embed all VN materials/brands/styles via ZeniCloud /ai/embed
2. Cache embeddings in memory (768-dim vectors)
3. For each agent generate() call: embed user prompt → cosine similarity →
   pick top-5 most relevant KB items → inject as context block in user prompt

Why agents become smarter:
- Interior agent learns "khách nói 'Đông Dương' → suggest gạch bông cổ + gỗ Pơmu + lụa Hà Đông"
- Architecture agent learns "khách nói 'tropical' → đề xuất sân trong + lam che + mái dốc 30°"
- Output BOQ chính xác hơn vì LLM có context vật liệu cụ thể đã được pre-curated
"""
from __future__ import annotations

import asyncio
import logging
import math
from typing import Any

from api.services import zenicloud_service as zc

logger = logging.getLogger(__name__)


# ─── KB documents per discipline ──────────────────────────
# Each doc: {id, content, metadata}
# Embedded once on first use, cached for the process lifetime.
INTERIOR_KB: list[dict[str, Any]] = [
    {"id": "indochine_palette", "content": "Phong cách Đông Dương cách tân: gạch bông cổ điển hoa văn vàng-xanh, gỗ Pơmu / gõ đỏ, lụa Hà Đông, kim loại đồng patina, palette trắng kem + nâu đậm + xanh navy", "tags": ["indochine"]},
    {"id": "tropical_modern", "content": "Tropical Modern: gỗ teak nhân tạo, đá travertine honed, vải linen tự nhiên, cây Monstera + Bird of Paradise, palette ấm beige + xanh rêu + cam đất", "tags": ["tropical_modern", "biophilic"]},
    {"id": "wabi_sabi", "content": "Wabi-Sabi: lime plaster lăn vữa thô, gỗ chưa sơn để mộc, ceramics handcrafted, ánh sáng dịu khuếch tán, palette earth tone trắng ngà + nâu nhạt + xám đá", "tags": ["wabi_sabi", "japandi"]},
    {"id": "neo_classical", "content": "Tân cổ điển: phào chỉ thạch cao, đá marble Calacatta, đèn chùm crystal, vải nhung + tafta, palette champagne + navy + gold leaf accent", "tags": ["neo_classical"]},
    {"id": "japandi", "content": "Japandi: kết hợp Nhật + Bắc Âu, gỗ sồi trắng + tre, vải linen, futon thấp, palette muted earth + sage green", "tags": ["japandi", "scandinavian"]},
    {"id": "scandinavian", "content": "Scandinavian Bắc Âu: sàn gỗ sồi sáng, tường trắng, vải len + lông cừu, đồ nội thất tối giản dáng cong, palette trắng + xám + gỗ vàng", "tags": ["scandinavian"]},
    {"id": "modern_lux", "content": "Modern Luxury: marble + kim loại brass, sofa bouclé cream, đèn pendant Flos, palette neutral + 1 màu accent đậm", "tags": ["modern", "neo_classical"]},
    {"id": "industrial", "content": "Industrial: tường gạch trần exposed, ống điện thép lộ thiên, đèn Edison filament, sofa da nâu vintage, palette grey + black + rust", "tags": ["industrial"]},
    {"id": "mediterranean", "content": "Mediterranean: gạch terracotta, vòm cong, đá tự nhiên, ceramic Hy Lạp, palette trắng kem + xanh biển + olive", "tags": ["mediterranean"]},
    {"id": "vn_san_go", "content": "Sàn gỗ Việt: An Cường 12mm AC4 285K/m², Wilsonart 8mm 195K/m², Inovar Đức 12mm 420K/m². Cao cấp dùng gỗ tự nhiên Pơmu / Walnut / Sồi 1.2-2.5M/m²", "tags": ["interior"]},
    {"id": "vn_son_tuong", "content": "Sơn tường Việt: Dulux Weathershield 5L 485K (ngoại thất), Dulux Ambiance 5L 385K (nội thất cao cấp), Jotun 5L 320K, Nippon 5L 250K. Định mức 1L = ~10m² 2 lớp", "tags": ["interior", "architecture"]},
    {"id": "vn_den_led", "content": "Đèn LED Việt: Philips Meson 7W 125K, Panel 18W 4000K 285K, Pendant Flos cao cấp 8-25M, đèn âm trần Rạng Đông 10W 65K. Mật độ tiêu chuẩn 1 đèn/3m² phòng ở", "tags": ["interior"]},
    {"id": "vn_thiet_bi_ve_sinh", "content": "TOTO MS885 (bồn cầu) 8.5M, MS888 12M; Inax CES999 6.8M; Vòi sen TOTO TBS01 1.2M; lavabo American Standard 850K-2.5M tùy size", "tags": ["interior"]},
    {"id": "vn_da_dinh_dinh", "content": "Đá Bình Định: granite đen 850K/m², trắng kem Crema Marfil 1.2M/m², travertine honed 1.8M/m². Quy cách 600x600 hoặc tấm lớn 1500x3000", "tags": ["interior", "architecture"]},
    {"id": "vn_kinh_low_e", "content": "Kính hộp Low-E Saint-Gobain 6+9A+6mm 1.85M/m², Vĩnh Tường 6+12A+6 1.45M/m². Giảm bức xạ nhiệt 70%, phù hợp khí hậu nhiệt đới", "tags": ["architecture"]},
    {"id": "vn_gach_aac", "content": "Gạch không nung AAC 100x200x600mm 12.5K/viên (Vương Hải, Tân Kỷ Nguyên, E-Block). Tiết kiệm 15-25% chi phí so gạch nung, cách nhiệt tốt hơn 2x", "tags": ["architecture", "structural"]},
    {"id": "vn_be_tong", "content": "Bê tông tươi B25 1.45M/m³ (Holcim, Insee), B30 1.65M/m³, móng B20 1.28M/m³. Mac 250 dùng cho dân dụng <5 tầng", "tags": ["structural"]},
    {"id": "vn_thep_hoa_phat", "content": "Thép Hòa Phát CB400-V φ16-φ22 18.8K/kg, CB300-V 17.5K/kg, CB240-T (đai) 17.5K/kg. Tiêu hao 80-120kg/m³ bê tông cho nhà dân dụng", "tags": ["structural"]},
    {"id": "phong_thuy_huong", "content": "Phong thủy 8 hướng: Đông Nam (Tốn) hợp Mộc + Thủy, đón gió mát; Tây Bắc (Càn) hợp Kim, vững chãi; tránh hướng Tây cho phòng chính (nóng); cửa chính không thẳng cửa hậu/WC", "tags": ["interior", "architecture"]},
    {"id": "tcvn_4205", "content": "TCVN 4205:2012 nhà ở: phòng ngủ ≥9m², khách ≥14m², WC ≥3m². Cao tầng 1 ≥3.0m, tầng trên ≥2.7m. Cầu thang bậc 25-30cm rộng × 15-17cm cao", "tags": ["architecture"]},
    {"id": "tcvn_5574", "content": "TCVN 5574:2018 BTCT: cấp bê tông B20-B40, cốt thép CB300/CB400/CB500-V, nhịp dầm khả thi ≤6m an toàn, console ≤2m", "tags": ["structural"]},
    {"id": "tcvn_2737", "content": "TCVN 2737:2023 tải trọng: tĩnh tải sàn 1.5-2.5 kN/m², hoạt tải nhà ở 1.5-2.0 kN/m², tổ hợp 1.1·DL+1.2·LL+1.4·WL", "tags": ["structural"]},
    {"id": "vn_climate_north", "content": "Khí hậu miền Bắc VN: 4 mùa, đông lạnh ẩm 13-17°C, hè nóng 32-38°C, mưa rào tháng 5-9. Nhà nên hướng Nam/Đông Nam đón gió mát hè + đón nắng đông", "tags": ["architecture"]},
    {"id": "vn_climate_south", "content": "Khí hậu miền Nam VN: 2 mùa khô (T11-T4) gió Đông Bắc, mưa (T5-T10) gió Tây Nam. Mặt trời cao đỉnh đầu hè (zenith 12.5°), mái đua sâu chống mưa xiên", "tags": ["architecture"]},
    {"id": "vn_brand_minotti", "content": "Brand cao cấp nội thất: Minotti Connery 3-seater 320M, B&B Italia Erei coffee table 85M, Cassina LC2 sofa 280M, Flos Skygarden pendant 35M. Nhập khẩu, lead time 12-16 tuần", "tags": ["interior"]},
    {"id": "vn_brand_an_cuong", "content": "Brand bình dân nội thất Việt: An Cường (gỗ MDF veneer), Hòa Phát (nội thất văn phòng), Xuân Hòa (giường tủ), Phú Quý (tủ áo). Giá hợp lý, lead time 1-2 tuần", "tags": ["interior"]},
    {"id": "vn_brand_nha_xinh", "content": "Brand trung cấp Việt: Nhà Xinh (nội thất modular), Modular (kệ tủ nhập khẩu), Index Living Mall (đồ Thái), JYSK (Bắc Âu). Sofa 15-35M, kệ TV 8-22M", "tags": ["interior"]},
    {"id": "vn_supplier_d2c", "content": "Đặt vật liệu D2C VN: Vật Liệu Xanh (gạch+xi măng+sắt thép), 24h Building (giao trong ngày HCM/HN), Ahamove (vận chuyển kg). Giảm 8-15% so showroom truyền thống", "tags": ["interior", "structural"]},
]


# ─── In-memory embedding cache ────────────────────────────
class _KBStore:
    """Holds embeddings for KB docs. Lazy-loaded once per process."""

    def __init__(self):
        self._embeddings: dict[str, list[float]] = {}  # doc_id → vector
        self._lock = asyncio.Lock()
        self._loaded = False

    async def ensure_loaded(self) -> None:
        if self._loaded:
            return
        async with self._lock:
            if self._loaded:
                return
            if not zc.is_configured():
                logger.warning("[rag] ZeniCloud not configured — RAG disabled")
                self._loaded = True  # don't retry
                return
            texts = [doc["content"] for doc in INTERIOR_KB]
            try:
                vectors = await zc.embed(texts, task_type="RETRIEVAL_DOCUMENT")
                if not vectors or len(vectors) != len(INTERIOR_KB):
                    logger.error("[rag] embed returned %d vectors for %d docs", len(vectors), len(INTERIOR_KB))
                    self._loaded = True
                    return
                for doc, vec in zip(INTERIOR_KB, vectors):
                    self._embeddings[doc["id"]] = vec
                self._loaded = True
                logger.info("[rag] loaded %d KB embeddings", len(self._embeddings))
            except Exception as e:
                logger.exception("[rag] load failed: %s", e)
                self._loaded = True

    def is_ready(self) -> bool:
        return self._loaded and bool(self._embeddings)

    def get_vector(self, doc_id: str) -> list[float] | None:
        return self._embeddings.get(doc_id)

    @property
    def doc_count(self) -> int:
        return len(self._embeddings)


_store = _KBStore()


# ─── Cosine similarity ────────────────────────────────────
def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ─── Public API ─────────────────────────────────────────────
async def retrieve_relevant_kb(
    query: str,
    *,
    discipline: str = "interior",
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Embed query → return top-K most similar KB docs (filtered by discipline tag).

    Returns list of {id, content, score, tags}. Empty list if RAG unavailable.
    """
    if not query or not zc.is_configured():
        return []

    await _store.ensure_loaded()
    if not _store.is_ready():
        return []

    # Embed the query
    try:
        q_vecs = await zc.embed([query], task_type="RETRIEVAL_QUERY")
        if not q_vecs:
            return []
        q_vec = q_vecs[0]
    except Exception as e:
        logger.exception("[rag] query embed failed: %s", e)
        return []

    # Filter docs by discipline tag (interior includes all generic docs)
    candidates = INTERIOR_KB
    if discipline in ("architecture", "structural"):
        candidates = [
            d for d in INTERIOR_KB
            if discipline in d.get("tags", []) or "interior" not in d.get("tags", [])
        ]

    # Score every candidate
    scored: list[tuple[float, dict]] = []
    for doc in candidates:
        v = _store.get_vector(doc["id"])
        if v:
            scored.append((_cosine(q_vec, v), doc))
    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {"id": d["id"], "content": d["content"], "score": round(score, 3), "tags": d.get("tags", [])}
        for score, d in scored[:top_k]
        if score > 0.55  # similarity threshold
    ]


def format_rag_context(docs: list[dict[str, Any]]) -> str:
    """Format retrieved docs into a context block to inject into agent prompt."""
    if not docs:
        return ""
    lines = ["📚 KIẾN THỨC THAM KHẢO (RAG retrieved):"]
    for i, doc in enumerate(docs, 1):
        lines.append(f"  {i}. [{doc['id']}] {doc['content']}")
    lines.append("")
    lines.append("→ Sử dụng kiến thức trên ĐỂ ENRICH output (vật liệu cụ thể, brand VN, giá thực tế 2026).")
    return "\n".join(lines)


async def get_rag_status() -> dict:
    """Diagnostic: check if RAG is loaded."""
    await _store.ensure_loaded()
    return {
        "ready": _store.is_ready(),
        "doc_count": _store.doc_count,
        "kb_total": len(INTERIOR_KB),
        "zenicloud_configured": zc.is_configured(),
    }
