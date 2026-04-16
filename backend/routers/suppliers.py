"""Suppliers router — list, detail, products by supplier."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.models.product import Product
from api.models.user import User

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("")
async def list_suppliers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Danh sách nhà cung cấp."""
    query = select(User).where(
        and_(User.role == "supplier", User.status == "active")
    )
    if category:
        query = query.where(User.main_category == category)

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    suppliers = result.scalars().all()

    items = []
    for s in suppliers:
        # Count products
        prod_count = await db.execute(
            select(func.count()).where(
                and_(Product.supplier_id == s.id, Product.status == "approved")
            )
        )
        items.append({
            "id": str(s.id),
            "full_name": s.full_name,
            "store_name": s.store_name,
            "supplier_type": s.supplier_type,
            "main_category": s.main_category,
            "delivery_area": s.delivery_area,
            "supplier_intro": s.supplier_intro,
            "avatar_url": s.avatar_url,
            "is_verified_supplier": s.is_verified_supplier,
            "product_count": prod_count.scalar() or 0,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit else 0,
    }


@router.get("/{supplier_id}")
async def get_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    """Chi tiết nhà cung cấp."""
    result = await db.execute(
        select(User).where(and_(User.id == supplier_id, User.role == "supplier"))
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(404, "Nhà cung cấp không tồn tại")

    return {
        "id": str(supplier.id),
        "full_name": supplier.full_name,
        "email": supplier.email,
        "phone": supplier.phone,
        "store_name": supplier.store_name,
        "supplier_type": supplier.supplier_type,
        "main_category": supplier.main_category,
        "delivery_area": supplier.delivery_area,
        "supplier_intro": supplier.supplier_intro,
        "b2b_credit_policy": supplier.b2b_credit_policy,
        "pricing_tier": supplier.pricing_tier,
        "avatar_url": supplier.avatar_url,
        "is_verified_supplier": supplier.is_verified_supplier,
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
    }


@router.get("/{supplier_id}/products")
async def get_supplier_products(
    supplier_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Sản phẩm của nhà cung cấp."""
    # Verify supplier exists
    supplier = await db.execute(
        select(User).where(and_(User.id == supplier_id, User.role == "supplier"))
    )
    if not supplier.scalar_one_or_none():
        raise HTTPException(404, "Nhà cung cấp không tồn tại")

    query = select(Product).where(
        and_(Product.supplier_id == supplier_id, Product.status == "approved")
    )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    products = result.scalars().all()

    return {
        "items": [
            {
                "id": str(p.id),
                "name": p.name,
                "price": p.price,
                "promo_price": p.promo_price,
                "unit": p.unit,
                "stock": p.stock,
                "images": p.images,
                "rating": float(p.rating) if p.rating else 0,
                "rating_count": p.rating_count,
                "badges": p.badges,
                "sale_label": p.sale_label,
            }
            for p in products
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit else 0,
    }
