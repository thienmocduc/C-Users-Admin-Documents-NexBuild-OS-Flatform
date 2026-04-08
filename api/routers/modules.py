"""Module/Ecosystem router — public endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.models.module import Module, ModulePain, ModuleResult

router = APIRouter(prefix="/modules", tags=["Modules"])


@router.get("")
async def list_modules(db: AsyncSession = Depends(get_db)):
    """Lấy tất cả 12 modules cho trang chủ."""
    result = await db.execute(
        select(Module).where(Module.is_active == True).order_by(Module.sort_order)
    )
    modules = result.scalars().all()
    return [
        {
            "id": m.id, "name": m.name, "num": m.num, "tag": m.tag,
            "model": m.model, "hook": m.hook, "description": m.description,
            "icon_svg": m.icon_svg, "icon_bg": m.icon_bg, "icon_border": m.icon_border,
            "cta_bg": m.cta_bg, "color": m.color, "gradient": m.gradient,
            "file_url": m.file_url, "pricing_label": m.pricing_label,
            "pricing_detail": m.pricing_detail,
        }
        for m in modules
    ]


@router.get("/{module_id}")
async def get_module(module_id: str, db: AsyncSession = Depends(get_db)):
    """Chi tiết 1 module + pains + results."""
    result = await db.execute(select(Module).where(Module.id == module_id))
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(404, "Module không tồn tại")

    pains = await db.execute(
        select(ModulePain).where(ModulePain.module_id == module_id).order_by(ModulePain.sort_order)
    )
    results = await db.execute(
        select(ModuleResult).where(ModuleResult.module_id == module_id).order_by(ModuleResult.sort_order)
    )

    return {
        "module": {
            "id": module.id, "name": module.name, "num": module.num,
            "tag": module.tag, "model": module.model, "hook": module.hook,
            "description": module.description, "icon_svg": module.icon_svg,
            "color": module.color, "gradient": module.gradient, "file_url": module.file_url,
            "pricing_label": module.pricing_label, "pricing_detail": module.pricing_detail,
        },
        "pains": [
            {"before_title": p.before_title, "before_desc": p.before_desc,
             "after_title": p.after_title, "after_desc": p.after_desc}
            for p in pains.scalars()
        ],
        "results": [
            {"emoji": r.emoji, "title": r.title, "kpi": r.kpi}
            for r in results.scalars()
        ],
    }
