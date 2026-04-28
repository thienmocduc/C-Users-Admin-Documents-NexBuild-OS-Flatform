"""Design AI request/response schemas."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=2000)
    # Style: relaxed pattern — Vietnamese styles (indochine, tropical_modern, wabi_sabi, neo_classical) added
    style: str = Field(
        "modern",
        pattern=r"^(modern|scandinavian|japandi|industrial|mediterranean|biophilic|indochine|tropical_modern|wabi_sabi|neo_classical)$",
    )
    room_type: Optional[str] = None
    # area_m2: expanded to 10000 to accommodate architecture (large villa, commercial)
    area_m2: Optional[float] = Field(None, ge=5, le=10000)
    budget_million: Optional[float] = Field(None, ge=0)
    auto_boq: bool = True
    shoppable: bool = True

    # NEW — Multi-discipline support
    discipline: Literal["interior", "architecture", "structural"] = "interior"
    location_province: Optional[str] = Field(
        None, description="VN province for sun path / climate / wind zone"
    )
    floors: Optional[int] = Field(None, ge=1, le=50, description="Number of floors (architecture/structural)")
    soil_type: Optional[str] = Field(
        None, description="Soil description for foundation design (structural)"
    )

    # Phase 3 — Multi-stage pipeline toggle (slower but higher quality)
    high_quality: bool = Field(
        False,
        description="Run PLAN→SKETCH→RENDER→SELECT pipeline (3-5x slower, ~$0.05/run)",
    )


class DesignVariant(BaseModel):
    variant_idx: int
    style_label: str
    description: str
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class BOQItemResponse(BaseModel):
    id: Optional[str] = None
    category: str
    material: str
    product_name: str
    unit: str
    quantity: float
    unit_price: int
    total_price: int

    model_config = {"from_attributes": True}


class GenerateResponse(BaseModel):
    """Generic response — agent-specific data lives under `agent_output`.

    Backward-compatible: legacy `variants` + `boq_items` fields preserved
    when discipline=interior.
    """
    design_id: str
    status: str
    discipline: str = "interior"
    # Legacy interior fields (kept for backward compatibility)
    variants: list[DesignVariant] = []
    boq_items: list[BOQItemResponse] = []
    boq_total: int = 0
    prompt_enhanced: str = ""
    message: str = ""
    # NEW — full agent output (for architecture/structural with custom shape)
    agent_output: Optional[dict[str, Any]] = None


class DesignHistoryItem(BaseModel):
    id: str
    prompt: str
    style: Optional[str] = None
    room_type: Optional[str] = None
    area_m2: Optional[float] = None
    discipline: str = "interior"
    status: str
    created_at: str
    variant_count: int = 0
    boq_total: int = 0

    model_config = {"from_attributes": True}


class QuotaResponse(BaseModel):
    plan: str
    used: int
    limit: int
    remaining: int
    reset_date: Optional[str] = None


# ─── Phase 5 — Iterative Refinement ───────────────────────────
class RefineRequest(BaseModel):
    """User feedback to refine an existing design.

    Example:
        parent_design_id: "uuid"
        parent_variant_idx: 0  # which variant the user picked
        feedback: "Thêm vài chậu cây xanh bên cửa sổ, đổi đèn chùm sang đèn vàng ấm hơn"
    """
    parent_variant_idx: int = Field(0, ge=0, le=10)
    feedback: str = Field(..., min_length=5, max_length=2000)


class RefineResponse(BaseModel):
    design_id: str
    parent_design_id: str
    round: int
    feedback_history: list[str]
    discipline: str
    status: str
    variants: list[dict] = []
    boq_items: list[dict] = []
    boq_total: int = 0
    agent_output: Optional[dict] = None
    message: str = ""


# ─── Phase 4 — Reference-Guided ───────────────────────────────
class AnalyzeReferenceRequest(BaseModel):
    """Analyze a reference image to extract design DNA → enriches user's prompt.

    Provide either image_url (public) or image_data_uri (uploaded base64).
    """
    image_url: Optional[str] = Field(None, max_length=2000)
    image_data_uri: Optional[str] = Field(None, max_length=10_000_000)  # ~7MB base64
    user_prompt: str = Field("", max_length=500, description="Optional extra context")


class AnalyzeReferenceResponse(BaseModel):
    style_analysis: str            # 5-line description in Vietnamese
    detected_palette: list[str]    # 3-5 hex colors
    detected_materials: list[str]  # eg ["gỗ óc chó", "đá travertine"]
    detected_style: str            # eg "indochine" / "japandi"
    enhanced_prompt: str           # ready-to-use prompt for /design/generate
    cost_usd: float = 0
    latency_ms: int = 0
