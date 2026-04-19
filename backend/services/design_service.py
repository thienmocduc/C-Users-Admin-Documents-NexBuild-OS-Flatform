"""Design service — quota management + orchestration."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.user import User
from api.models.design import BOQItem, Design, DesignRender
from api.services.gemini_service import generate_design
from api.services.fal_service import generate_design_images


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
        "reset_date": (now.replace(month=now.month % 12 + 1, day=1) if now.month < 12 else now.replace(year=now.year + 1, month=1, day=1)).isoformat(),
    }


async def create_design(
    user: User,
    prompt: str,
    style: str,
    room_type: Optional[str],
    area_m2: Optional[float],
    budget_million: Optional[float],
    auto_boq: bool,
    db: AsyncSession,
) -> dict:
    """Create a design — calls Gemini AI, saves to DB."""

    # Check quota
    quota = await check_quota(user, db)
    if quota["plan"] == "free" and quota["remaining"] <= 0:
        return {
            "error": True,
            "message": "Bạn đã hết lượt render miễn phí tháng này. Nâng cấp Pro để không giới hạn!",
            "quota": quota,
        }

    # Create design record
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

    # Call Gemini AI
    try:
        ai_result = await generate_design(
            prompt=prompt,
            style=style,
            room_type=room_type,
            area_m2=area_m2,
            budget_million=budget_million,
            auto_boq=auto_boq,
        )
    except Exception as e:
        design.status = "failed"
        return {"error": True, "message": f"AI generation failed: {str(e)}"}

    design.status = "done"
    design.ai_response = ai_result
    design.completed_at = datetime.now(timezone.utc)

    # Generate images via Fal.ai (server-side — key in .env, NOT client)
    variants = ai_result.get("variants", [])
    variant_descriptions = [v.get("description", "") for v in variants]
    image_urls = await generate_design_images(
        prompt=prompt,
        style=style,
        area_m2=area_m2 or 30,
        room_type=room_type or "living room",
        variant_descriptions=variant_descriptions,
        count=len(variants),
    )

    # Save renders with image URLs
    for i, v in enumerate(variants):
        img_url = image_urls[i] if i < len(image_urls) else None
        v["image_url"] = img_url  # Enrich response
        render = DesignRender(
            design_id=design.id,
            variant_idx=v["variant_idx"],
            style_label=v["style_label"],
            description=v["description"],
            image_url=img_url,
            thumbnail_url=img_url,  # Same for Phase 1
        )
        db.add(render)

    # Save BOQ items
    boq_items = ai_result.get("boq_items", [])
    boq_total = 0
    for item in boq_items:
        boq = BOQItem(
            design_id=design.id,
            category=item["category"],
            material=item["material"],
            product_name=item["product_name"],
            unit=item["unit"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            total_price=item["total_price"],
        )
        db.add(boq)
        boq_total += item["total_price"]

    await db.flush()

    return {
        "design_id": str(design.id),
        "status": "done",
        "prompt_enhanced": ai_result.get("prompt_enhanced", prompt),
        "variants": variants,
        "boq_items": boq_items,
        "boq_total": boq_total,
        "scene_3d": ai_result.get("scene_3d"),
        "message": "4 phương án thiết kế đã sẵn sàng!",
    }
