"""Design service — quota management + multi-discipline agent dispatcher + refine."""
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.design import BOQItem, Design, DesignRender
from api.models.user import User
from api.services.fal_service import generate_design_images


# ─── Quota ────────────────────────────────────────────────────
async def check_quota(user: User, db: AsyncSession) -> dict:
    """Check user's design quota. Free: 3/month, Pro: unlimited."""
    plan = user.plan or "free"

    if plan in ("pro", "enterprise"):
        return {"plan": plan, "used": 0, "limit": -1, "remaining": -1}

    # Count designs this month
    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(Design.id)).where(
            Design.user_id == user.id,
            Design.created_at >= first_of_month,
            Design.status != "failed",
        )
    )
    used = result.scalar() or 0
    limit = 3
    remaining = max(0, limit - used)

    return {
        "plan": plan,
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "reset_date": (
            now.replace(month=now.month % 12 + 1, day=1)
            if now.month < 12
            else now.replace(year=now.year + 1, month=1, day=1)
        ).isoformat(),
    }


# ─── Discipline dispatcher ─────────────────────────────────────
def _select_agent(discipline: str):
    """Return the right agent class for a discipline."""
    if discipline == "architecture":
        from api.services.agents.architecture_agent import ArchitectureAgent
        return ArchitectureAgent()
    if discipline == "structural":
        from api.services.agents.structural_agent import StructuralAgent
        return StructuralAgent()
    # default: interior
    from api.services.agents.interior_agent import InteriorAgent
    return InteriorAgent()


# ─── Lightweight request shim (so agents can use attribute access) ──
class _AgentRequest:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ─── Main create_design ────────────────────────────────────────
async def create_design(
    user: User,
    prompt: str,
    style: str,
    room_type: Optional[str],
    area_m2: Optional[float],
    budget_million: Optional[float],
    auto_boq: bool,
    db: AsyncSession,
    *,
    discipline: str = "interior",
    location_province: Optional[str] = None,
    floors: Optional[int] = None,
    soil_type: Optional[str] = None,
) -> dict:
    """Create a design — dispatches to the right discipline agent."""

    # Check quota (unchanged)
    quota = await check_quota(user, db)
    if quota["plan"] == "free" and quota["remaining"] <= 0:
        return {
            "error": True,
            "message": "Bạn đã hết lượt render miễn phí tháng này. Nâng cấp Pro để không giới hạn!",
            "quota": quota,
        }

    # Persist design record (with discipline/floors stored in ai_response for now)
    design = Design(
        user_id=user.id,
        prompt=prompt,
        style=style,
        room_type=room_type,
        area_m2=area_m2,
        budget_million=budget_million,
        status="processing",
    )
    db.add(design)
    await db.flush()

    # ── Dispatch to discipline agent ──────────────────────────
    agent = _select_agent(discipline)
    agent_request = _AgentRequest(
        prompt=prompt,
        style=style,
        room_type=room_type,
        area_m2=area_m2,
        budget_million=budget_million,
        auto_boq=auto_boq,
        discipline=discipline,
        location_province=location_province,
        floors=floors,
        soil_type=soil_type,
    )

    try:
        ai_result = await agent.generate(agent_request)
    except Exception as e:
        design.status = "failed"
        return {"error": True, "message": f"AI generation failed: {e}"}

    design.status = "done"
    design.ai_response = ai_result
    design.completed_at = datetime.now(timezone.utc)

    # ── Discipline-specific post-processing ───────────────────
    if discipline == "interior":
        return await _finalize_interior(design, ai_result, prompt, style, room_type, area_m2, db)
    elif discipline == "architecture":
        return _finalize_architecture(design, ai_result)
    elif discipline == "structural":
        return _finalize_structural(design, ai_result)
    else:
        return {"design_id": str(design.id), "status": "done", "agent_output": ai_result}


# ─── Interior finalize (existing flow + Fal.ai images) ─────────
async def _finalize_interior(
    design: Design,
    ai_result: dict,
    prompt: str,
    style: str,
    room_type: Optional[str],
    area_m2: Optional[float],
    db: AsyncSession,
) -> dict:
    variants = ai_result.get("variants", [])
    variant_descriptions = [v.get("description", "") for v in variants]

    # Generate images via Fal.ai (returns None array if no credits/key)
    image_urls = await generate_design_images(
        prompt=prompt,
        style=style,
        area_m2=area_m2 or 30,
        room_type=room_type or "living room",
        variant_descriptions=variant_descriptions,
        count=len(variants) or 4,
    )

    # Save renders
    for i, v in enumerate(variants):
        img_url = image_urls[i] if i < len(image_urls) else None
        v["image_url"] = img_url
        render = DesignRender(
            design_id=design.id,
            variant_idx=v.get("variant_idx", i),
            style_label=v.get("style_label", f"Variant {i+1}"),
            description=v.get("description", ""),
            image_url=img_url,
            thumbnail_url=img_url,
        )
        db.add(render)

    # Save BOQ items (DB)
    boq_items = ai_result.get("boq_items", [])
    boq_total = 0
    for item in boq_items:
        try:
            qty = float(item.get("quantity", 0) or 0)
            unit_price = int(item.get("unit_price", 0) or 0)
            total_price = int(item.get("total_price") or qty * unit_price)
            boq = BOQItem(
                design_id=design.id,
                category=str(item.get("category", "Khác"))[:100],
                material=str(item.get("material", ""))[:100],
                product_name=str(item.get("product_name", ""))[:255],
                unit=str(item.get("unit", "cái"))[:32],
                quantity=qty,
                unit_price=unit_price,
                total_price=total_price,
            )
            db.add(boq)
            boq_total += total_price
        except (ValueError, TypeError):
            continue

    await db.flush()

    return {
        "design_id": str(design.id),
        "status": "done",
        "discipline": "interior",
        "prompt_enhanced": ai_result.get("prompt_enhanced", prompt),
        "variants": variants,
        "boq_items": boq_items,
        "boq_total": boq_total,
        "scene_3d": ai_result.get("scene_3d"),
        "agent_output": ai_result,
        "message": f"{len(variants)} phương án thiết kế đã sẵn sàng!",
    }


# ─── Architecture finalize ─────────────────────────────────────
def _finalize_architecture(design: Design, ai_result: dict) -> dict:
    variants = ai_result.get("concept_variants", [])
    return {
        "design_id": str(design.id),
        "status": "done",
        "discipline": "architecture",
        "prompt_enhanced": ai_result.get("prompt_enhanced", ""),
        "variants": [
            {
                "variant_idx": v.get("variant_idx", i),
                "style_label": v.get("concept_name", f"Concept {i+1}"),
                "description": v.get("description", ""),
                "image_url": v.get("image_url"),
            }
            for i, v in enumerate(variants)
        ],
        "boq_items": [],
        "boq_total": 0,
        "agent_output": ai_result,
        "message": f"{len(variants)} phương án kiến trúc đã sẵn sàng!",
    }


# ─── Structural finalize ───────────────────────────────────────
def _finalize_structural(design: Design, ai_result: dict) -> dict:
    return {
        "design_id": str(design.id),
        "status": "done",
        "discipline": "structural",
        "prompt_enhanced": ai_result.get("prompt_enhanced", ""),
        "variants": [],  # structural không có visual variants
        "boq_items": [],
        "boq_total": ai_result.get("boq_total_vnd", 0),
        "agent_output": ai_result,
        "message": "Phương án kết cấu sơ bộ đã sẵn sàng!",
    }


# ─────────────────────────────────────────────────────────────
# PHASE 5 — Iterative Refinement
# ─────────────────────────────────────────────────────────────
async def refine_design(
    user: User,
    parent_design_id: str,
    parent_variant_idx: int,
    feedback: str,
    db: AsyncSession,
) -> dict:
    """Refine an existing design based on user feedback.

    Loads parent context → calls agent.refine() → saves new Design row
    with refinement metadata in ai_response.
    """
    # Validate UUID
    try:
        pid = UUID(parent_design_id)
    except (ValueError, TypeError):
        return {"error": True, "message": "parent_design_id không hợp lệ"}

    # Load parent design
    result = await db.execute(select(Design).where(Design.id == pid))
    parent: Design | None = result.scalar_one_or_none()
    if not parent:
        return {"error": True, "message": "Không tìm thấy design gốc"}
    if parent.user_id != user.id:
        return {"error": True, "message": "Bạn không có quyền refine design này"}
    if not parent.ai_response:
        return {"error": True, "message": "Design gốc chưa có nội dung AI để refine"}

    parent_output = parent.ai_response
    parent_refinement = parent_output.get("refinement", {}) or {}
    round_num = int(parent_refinement.get("round", 1)) + 1

    # Cap rounds to 10 (prevent abuse)
    if round_num > 10:
        return {"error": True, "message": "Đã đạt giới hạn 10 lần refine cho design này"}

    # Quota check (refine consumes quota too)
    quota = await check_quota(user, db)
    if quota["plan"] == "free" and quota["remaining"] <= 0:
        return {
            "error": True,
            "message": "Bạn đã hết lượt render miễn phí tháng này. Nâng cấp Pro để không giới hạn!",
            "quota": quota,
        }

    # Determine discipline from parent
    discipline = parent_output.get("discipline", "interior")
    agent = _select_agent(discipline)

    # Build agent request from parent metadata
    agent_request = _AgentRequest(
        prompt=parent.prompt or "",
        style=parent.style or "modern",
        room_type=parent.room_type,
        area_m2=float(parent.area_m2) if parent.area_m2 else None,
        budget_million=float(parent.budget_million) if parent.budget_million else None,
        auto_boq=True,
        discipline=discipline,
        location_province=parent_output.get("site_analysis", {}).get("city"),
        floors=None,
        soil_type=None,
    )

    # Call agent.refine()
    try:
        refined = await agent.refine(
            parent_output=parent_output,
            parent_variant_idx=parent_variant_idx,
            feedback=feedback,
            round_num=round_num,
            request=agent_request,
        )
    except Exception as e:
        return {"error": True, "message": f"Refine failed: {e}"}

    # Inject refinement metadata
    feedback_history = list(parent_refinement.get("feedback_history", []))
    feedback_history.append(feedback)
    refined["refinement"] = {
        "is_refinement": True,
        "parent_design_id": str(parent.id),
        "parent_variant_idx": parent_variant_idx,
        "round": round_num,
        "feedback": feedback,
        "feedback_history": feedback_history,
    }

    # Persist as a new Design row (preserves history)
    new_design = Design(
        user_id=user.id,
        prompt=f"[v{round_num}] {parent.prompt}",
        style=parent.style,
        room_type=parent.room_type,
        area_m2=parent.area_m2,
        budget_million=parent.budget_million,
        status="done",
        ai_response=refined,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(new_design)
    await db.flush()

    # Save renders + BOQ for interior (legacy frontend compat)
    if discipline == "interior":
        for i, v in enumerate(refined.get("variants", [])):
            render = DesignRender(
                design_id=new_design.id,
                variant_idx=v.get("variant_idx", i),
                style_label=v.get("style_label", f"Variant {i+1}"),
                description=v.get("description", ""),
                image_url=v.get("image_url"),
                thumbnail_url=v.get("image_url"),
            )
            db.add(render)
        for item in refined.get("boq_items", []):
            try:
                qty = float(item.get("quantity", 0) or 0)
                up = int(item.get("unit_price", 0) or 0)
                tp = int(item.get("total_price") or qty * up)
                db.add(BOQItem(
                    design_id=new_design.id,
                    category=str(item.get("category", "Khác"))[:100],
                    material=str(item.get("material", ""))[:100],
                    product_name=str(item.get("product_name", ""))[:255],
                    unit=str(item.get("unit", "cái"))[:32],
                    quantity=qty,
                    unit_price=up,
                    total_price=tp,
                ))
            except (ValueError, TypeError):
                continue
    await db.flush()

    return {
        "design_id": str(new_design.id),
        "parent_design_id": str(parent.id),
        "round": round_num,
        "feedback_history": feedback_history,
        "discipline": discipline,
        "status": "done",
        "variants": refined.get("variants") or refined.get("concept_variants", []),
        "boq_items": refined.get("boq_items", []),
        "boq_total": refined.get("boq_total") or refined.get("boq_total_vnd", 0),
        "agent_output": refined,
        "message": f"Refine round {round_num} đã sẵn sàng!",
    }
