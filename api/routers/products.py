"""Products + Categories router."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import get_current_user, require_role
from api.models.product import Category, Product
from api.schemas.product import (
    CategoryResponse,
    ProductCreateRequest,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdateRequest,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("")
async def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = Query("newest", pattern=r"^(newest|price_asc|price_desc|rating|popular)$"),
    location: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Danh sách sản phẩm — public, có filter + sort + pagination."""
    query = select(Product).where(Product.status == "published")

    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))
    if category:
        cat = await db.execute(select(Category).where(Category.slug == category))
        cat_obj = cat.scalar_one_or_none()
        if cat_obj:
            query = query.where(Product.category_id == cat_obj.id)

    # Sort
    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "rating":
        query = query.order_by(Product.rating.desc())
    else:  # newest
        query = query.order_by(Product.created_at.desc())

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()

    return {
        "items": [ProductResponse.model_validate(p) for p in products],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    """Chi tiết sản phẩm."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Sản phẩm không tồn tại")
    return ProductResponse.model_validate(product)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    req: ProductCreateRequest,
    current_user=Depends(require_role("supplier")),
    db: AsyncSession = Depends(get_db),
):
    """Tạo sản phẩm mới (supplier only)."""
    product = Product(
        supplier_id=current_user.id,
        **req.model_dump(),
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return ProductResponse.model_validate(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    req: ProductUpdateRequest,
    current_user=Depends(require_role("supplier")),
    db: AsyncSession = Depends(get_db),
):
    """Sửa sản phẩm (supplier sở hữu)."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Sản phẩm không tồn tại")
    if product.supplier_id != current_user.id:
        raise HTTPException(403, "Không có quyền sửa sản phẩm này")

    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(product, key, value)

    await db.flush()
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: UUID,
    current_user=Depends(require_role("supplier", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Xóa sản phẩm (supplier sở hữu hoặc admin)."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Sản phẩm không tồn tại")
    if current_user.role == "supplier" and product.supplier_id != current_user.id:
        raise HTTPException(403, "Không có quyền xóa sản phẩm này")

    product.status = "archived"
    return {"message": "Đã xóa sản phẩm", "ok": True}


@router.patch("/{product_id}/status")
async def update_product_status(
    product_id: UUID,
    req: ProductStatusUpdate,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Admin duyệt/từ chối sản phẩm."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Sản phẩm không tồn tại")

    product.status = req.status
    product.approved_by = current_user.id
    from datetime import datetime, timezone
    product.approved_at = datetime.now(timezone.utc)

    return {"message": f"Sản phẩm đã được {req.status}", "ok": True}


# ─── Categories ───────────────────────────────────────────

cat_router = APIRouter(prefix="/categories", tags=["Categories"])


@cat_router.get("")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Tất cả danh mục."""
    result = await db.execute(select(Category).order_by(Category.sort_order))
    cats = result.scalars().all()
    return [CategoryResponse.model_validate(c) for c in cats]


@cat_router.get("/{slug}/products")
async def products_by_category(
    slug: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Sản phẩm theo danh mục slug."""
    cat = await db.execute(select(Category).where(Category.slug == slug))
    category = cat.scalar_one_or_none()
    if not category:
        raise HTTPException(404, "Danh mục không tồn tại")

    query = select(Product).where(
        Product.category_id == category.id, Product.status == "published"
    ).order_by(Product.created_at.desc())

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    products = result.scalars().all()

    return {"items": [ProductResponse.model_validate(p) for p in products], "category": category.name}
