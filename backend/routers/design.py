"""NexDesign AI router — generate designs, BOQ, quota, history."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import get_current_user
from api.models.design import BOQItem, Design, DesignRender
from api.schemas.design import GenerateRequest, QuotaResponse, RefineRequest
from api.services.design_service import check_quota, create_design, refine_design

router = APIRouter(prefix="/design", tags=["NexDesign AI"])


@router.post("/generate")
async def generate(
    req: GenerateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tạo thiết kế AI — Gemini generate 4 phương án + BOQ.

    Free: 3 renders/tháng. Pro: unlimited.
    Cost per request: ~$0.001 (Gemini 2.0 Flash).
    """
    result = await create_design(
        user=current_user,
        prompt=req.prompt,
        style=req.style,
        room_type=req.room_type,
        area_m2=req.area_m2,
        budget_million=req.budget_million,
        auto_boq=req.auto_boq,
        db=db,
        # Multi-discipline kwargs (default to interior for backward compat)
        discipline=req.discipline,
        location_province=req.location_province,
        floors=req.floors,
        soil_type=req.soil_type,
    )

    if result.get("error"):
        raise HTTPException(
            status_code=429 if "hết lượt" in result.get("message", "") else 500,
            detail=result["message"],
        )

    return result


# ─── Phase 5 — Iterative Refinement ────────────────────────────
@router.post("/{design_id}/refine")
async def refine(
    design_id: str,
    req: RefineRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refine an existing design with user feedback (Phase 5 iterative).

    User picks a variant + describes what to change → AI applies ONLY that
    change while preserving everything else. Saves as new Design row with
    parent reference for history.
    """
    result = await refine_design(
        user=current_user,
        parent_design_id=design_id,
        parent_variant_idx=req.parent_variant_idx,
        feedback=req.feedback,
        db=db,
    )
    if result.get("error"):
        msg = result.get("message", "")
        if "hết lượt" in msg:
            code = 429
        elif "không tìm thấy" in msg.lower() or "không hợp lệ" in msg.lower():
            code = 404
        elif "không có quyền" in msg.lower():
            code = 403
        elif "giới hạn 10 lần" in msg.lower():
            code = 422
        else:
            code = 500
        raise HTTPException(status_code=code, detail=msg)
    return result


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check quota còn lại — hiển thị trên header pill."""
    quota = await check_quota(current_user, db)
    return QuotaResponse(**quota)


@router.get("/history")
async def list_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lịch sử thiết kế của user."""
    query = select(Design).where(
        Design.user_id == current_user.id
    ).order_by(Design.created_at.desc())

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    designs = result.scalars().all()

    items = []
    for d in designs:
        boq_total = sum(b.total_price or 0 for b in d.boq_items)
        items.append({
            "id": str(d.id),
            "prompt": d.prompt,
            "style": d.style,
            "room_type": d.room_type,
            "area_m2": float(d.area_m2) if d.area_m2 else None,
            "status": d.status,
            "created_at": d.created_at.isoformat(),
            "variant_count": len(d.renders),
            "boq_total": boq_total,
        })

    return {"items": items, "page": page}


@router.get("/history/{design_id}")
async def get_design(
    design_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chi tiết 1 thiết kế — variants + BOQ."""
    result = await db.execute(
        select(Design).where(Design.id == design_id)
    )
    design = result.scalar_one_or_none()
    if not design:
        raise HTTPException(404, "Thiết kế không tồn tại")
    if design.user_id != current_user.id:
        raise HTTPException(403, "Không có quyền xem")

    variants = [
        {
            "variant_idx": r.variant_idx,
            "style_label": r.style_label,
            "description": r.description,
            "image_url": r.image_url,
            "selected": r.selected,
        }
        for r in design.renders
    ]

    boq_items = [
        {
            "id": str(b.id),
            "category": b.category,
            "material": b.material,
            "product_name": b.product_name,
            "unit": b.unit,
            "quantity": float(b.quantity) if b.quantity else 0,
            "unit_price": b.unit_price or 0,
            "total_price": b.total_price or 0,
            "order_status": b.order_status,
        }
        for b in design.boq_items
    ]

    boq_total = sum(b["total_price"] for b in boq_items)

    return {
        "id": str(design.id),
        "prompt": design.prompt,
        "prompt_enhanced": design.ai_response.get("prompt_enhanced", design.prompt) if design.ai_response else design.prompt,
        "style": design.style,
        "room_type": design.room_type,
        "area_m2": float(design.area_m2) if design.area_m2 else None,
        "status": design.status,
        "created_at": design.created_at.isoformat(),
        "variants": variants,
        "boq_items": boq_items,
        "boq_total": boq_total,
    }


@router.get("/{design_id}/scene")
async def get_scene(
    design_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lấy scene 3D data cho Three.js renderer."""
    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()
    if not design:
        raise HTTPException(404, "Thiết kế không tồn tại")
    if design.user_id != current_user.id:
        raise HTTPException(403, "Không có quyền xem")

    scene_3d = design.ai_response.get("scene_3d") if design.ai_response else None
    if not scene_3d:
        raise HTTPException(404, "Chưa có dữ liệu 3D cho thiết kế này")

    return {
        "design_id": str(design.id),
        "scene_3d": scene_3d,
        "style": design.style,
        "area_m2": float(design.area_m2) if design.area_m2 else None,
    }


@router.post("/{design_id}/save-3d")
async def save_scene(
    design_id: UUID,
    scene_data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lưu scene 3D data từ editor (furniture positions, materials, etc)."""
    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()
    if not design:
        raise HTTPException(404, "Thiết kế không tồn tại")
    if design.user_id != current_user.id:
        raise HTTPException(403, "Không có quyền sửa")

    # Update scene_3d in ai_response JSON
    ai_response = design.ai_response or {}
    ai_response["scene_3d"] = scene_data
    design.ai_response = ai_response

    # Flag DB update for JSON column
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(design, "ai_response")

    await db.flush()

    return {"message": "Đã lưu scene 3D", "ok": True}


@router.post("/{design_id}/export")
async def export_design(
    design_id: UUID,
    export_type: str = Query("measurements", pattern=r"^(measurements|boq_from_3d)$"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export từ 3D scene: measurements hoặc BOQ tự động."""
    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()
    if not design:
        raise HTTPException(404, "Thiết kế không tồn tại")
    if design.user_id != current_user.id:
        raise HTTPException(403, "Không có quyền")

    scene_3d = design.ai_response.get("scene_3d") if design.ai_response else None
    if not scene_3d:
        raise HTTPException(404, "Chưa có dữ liệu 3D")

    room = scene_3d.get("room", {})
    furniture = scene_3d.get("furniture", [])

    if export_type == "measurements":
        measurements = {
            "room": {
                "width": room.get("width", 0),
                "depth": room.get("depth", 0),
                "height": room.get("height", 0),
                "area": round(room.get("width", 0) * room.get("depth", 0), 1),
                "volume": round(room.get("width", 0) * room.get("depth", 0) * room.get("height", 0), 1),
            },
            "furniture": [
                {
                    "name": f.get("name", f.get("type", "Unknown")),
                    "type": f.get("type"),
                    "dimensions": f.get("dimensions", {}),
                    "position": f.get("position", {}),
                }
                for f in furniture
            ],
            "total_items": len(furniture),
        }
        return measurements

    elif export_type == "boq_from_3d":
        # Generate BOQ from 3D scene furniture
        from api.services.gemini_service import VN_MATERIALS_DB

        boq_items = []
        for f in furniture:
            ftype = f.get("type", "")
            name = f.get("name", ftype)
            dims = f.get("dimensions", {})
            # Estimate price based on type
            price_map = {
                "sofa": 15000000, "table": 5000000, "chair": 2000000,
                "bed": 12000000, "cabinet": 8000000, "desk": 6000000,
                "shelf": 850000, "lamp": 1200000, "plant": 500000,
                "rug": 2000000, "tv_stand": 4000000, "wardrobe": 10000000,
                "nightstand": 2500000, "dining_set": 20000000,
            }
            price = price_map.get(ftype, 1000000)
            boq_items.append({
                "category": "Nội thất",
                "name": name,
                "material": f.get("material", ""),
                "unit": "cái",
                "quantity": 1,
                "unit_price": price,
                "total_price": price,
            })

        # Add room materials (floor, walls, ceiling)
        room_area = room.get("width", 0) * room.get("depth", 0)
        wall_area = 2 * (room.get("width", 0) + room.get("depth", 0)) * room.get("height", 0)
        boq_items.extend([
            {"category": "Sàn", "name": "Sàn gỗ công nghiệp", "material": scene_3d.get("floor", {}).get("material", "wood"), "unit": "m²", "quantity": round(room_area, 1), "unit_price": 285000, "total_price": int(room_area * 285000)},
            {"category": "Tường", "name": "Sơn tường nội thất", "material": "paint", "unit": "m²", "quantity": round(wall_area, 1), "unit_price": 45000, "total_price": int(wall_area * 45000)},
        ])

        total = sum(i["total_price"] for i in boq_items)
        return {"items": boq_items, "total": total}


@router.get("/boq/saved")
async def list_saved_boqs(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """DS BOQ đã lưu (designs có status=done)."""
    result = await db.execute(
        select(Design).where(
            Design.user_id == current_user.id,
            Design.status == "done",
        ).order_by(Design.created_at.desc()).limit(50)
    )
    designs = result.scalars().all()

    boqs = []
    for d in designs:
        items = d.boq_items
        total = sum(b.total_price or 0 for b in items)
        if total > 0:
            boqs.append({
                "design_id": str(d.id),
                "prompt": d.prompt,
                "style": d.style,
                "item_count": len(items),
                "total": total,
                "created_at": d.created_at.isoformat(),
            })

    return {"items": boqs}
