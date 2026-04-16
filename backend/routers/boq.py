"""BOQ (Bill of Quantities) router — import, parse, add-to-cart."""
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import get_settings
from api.core.database import get_db
from api.core.security import get_current_user
from api.models.community import BOQImport
from api.models.order import CartItem
from api.models.product import Product
from api.schemas.boq import BOQAddToCartRequest, BOQImportRequest, BOQParseResponse

router = APIRouter(prefix="/boq", tags=["BOQ"])
settings = get_settings()


async def _parse_boq_with_gemini(text: str) -> dict:
    """Parse BOQ text using Gemini AI."""
    if not settings.GEMINI_API_KEY:
        # Fallback demo response
        return {
            "items": [
                {"category": "Sàn", "name": "Sàn gỗ công nghiệp AC4", "material": "Gỗ công nghiệp", "unit": "m²", "quantity": 50, "unit_price": 285000, "total_price": 14250000},
                {"category": "Sơn", "name": "Sơn Dulux nội thất", "material": "Sơn nước", "unit": "lít", "quantity": 20, "unit_price": 485000, "total_price": 9700000},
                {"category": "Điện", "name": "Đèn LED Panel Philips", "material": "LED", "unit": "bộ", "quantity": 8, "unit_price": 285000, "total_price": 2280000},
            ],
            "total": 26230000,
        }

    import httpx
    prompt = f"""Phân tích danh mục vật tư xây dựng (BOQ) sau và trả về JSON:
{text}

Trả về đúng format JSON:
{{"items": [{{"category": "...", "name": "...", "material": "...", "unit": "...", "quantity": 0, "unit_price": 0, "total_price": 0}}], "total": 0}}

Sử dụng đơn giá thị trường Việt Nam (VND). Nếu không có đơn giá, ước tính hợp lý."""

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent",
            params={"key": settings.GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                },
            },
            timeout=30.0,
        )

    if resp.status_code != 200:
        return {"items": [], "total": 0}

    try:
        data = resp.json()
        text_result = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text_result)
    except (KeyError, json.JSONDecodeError):
        return {"items": [], "total": 0}


async def _save_and_parse_boq(text_to_parse: str, file_url: str | None, db, current_user) -> dict:
    """Shared logic: save BOQ record, parse with Gemini, return response."""
    boq_import = BOQImport(
        user_id=current_user.id,
        file_url=file_url,
        manual_text=text_to_parse[:5000] if text_to_parse else None,
        status="processing",
    )
    db.add(boq_import)
    await db.flush()

    result = await _parse_boq_with_gemini(text_to_parse)

    boq_import.result = result
    boq_import.status = "completed" if result.get("items") else "failed"

    await db.flush()
    await db.refresh(boq_import)

    return {
        "id": str(boq_import.id),
        "status": boq_import.status,
        "items": result.get("items", []),
        "total": result.get("total", 0),
        "created_at": boq_import.created_at.isoformat(),
    }


@router.post("/import", status_code=201)
async def import_boq(
    req: BOQImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Import BOQ từ text thủ công (JSON body)."""
    if not req.manual_text:
        raise HTTPException(400, "Cần manual_text để import BOQ")
    return await _save_and_parse_boq(req.manual_text, None, db, current_user)


@router.post("/import-file", status_code=201)
async def import_boq_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Import BOQ từ file upload (xlsx/csv/pdf)."""
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File quá lớn. Tối đa 10MB")
    try:
        text_to_parse = content.decode("utf-8")
    except UnicodeDecodeError:
        text_to_parse = f"[Uploaded file: {file.filename}, {len(content)} bytes]"
    return await _save_and_parse_boq(text_to_parse, f"/uploads/{file.filename}", db, current_user)


@router.get("/{import_id}")
async def get_boq_result(
    import_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Lấy kết quả parse BOQ."""
    result = await db.execute(
        select(BOQImport).where(
            and_(BOQImport.id == import_id, BOQImport.user_id == current_user.id)
        )
    )
    boq = result.scalar_one_or_none()
    if not boq:
        raise HTTPException(404, "BOQ import không tồn tại")

    return {
        "id": str(boq.id),
        "status": boq.status,
        "items": boq.result.get("items", []) if boq.result else [],
        "total": boq.result.get("total", 0) if boq.result else 0,
        "manual_text": boq.manual_text,
        "file_url": boq.file_url,
        "created_at": boq.created_at.isoformat(),
    }


@router.post("/{import_id}/add-to-cart")
async def add_boq_to_cart(
    import_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Thêm items từ BOQ vào giỏ hàng (match tên sản phẩm)."""
    result = await db.execute(
        select(BOQImport).where(
            and_(BOQImport.id == import_id, BOQImport.user_id == current_user.id)
        )
    )
    boq = result.scalar_one_or_none()
    if not boq:
        raise HTTPException(404, "BOQ import không tồn tại")
    if not boq.result or not boq.result.get("items"):
        raise HTTPException(400, "BOQ chưa có items")

    added = 0
    not_found = []

    for item in boq.result["items"]:
        # Try to find matching product by name
        product = await db.execute(
            select(Product).where(
                and_(
                    Product.name.ilike(f"%{item['name']}%"),
                    Product.status == "approved",
                    Product.show_in_boq == True,
                )
            )
        )
        product = product.scalar_one_or_none()

        if product:
            # Check if already in cart
            existing = await db.execute(
                select(CartItem).where(
                    and_(
                        CartItem.user_id == current_user.id,
                        CartItem.product_id == product.id,
                    )
                )
            )
            cart_item = existing.scalar_one_or_none()

            qty = max(1, int(item.get("quantity", 1)))

            if cart_item:
                cart_item.quantity += qty
            else:
                db.add(CartItem(
                    user_id=current_user.id,
                    product_id=product.id,
                    quantity=qty,
                ))
            added += 1
        else:
            not_found.append(item["name"])

    await db.commit()

    return {
        "message": f"Đã thêm {added} sản phẩm vào giỏ hàng",
        "ok": True,
        "added": added,
        "not_found": not_found,
    }
