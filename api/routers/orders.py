"""Orders + Cart + Escrow router."""
import uuid as uuid_mod
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import get_settings
from api.core.database import get_db
from api.core.security import get_current_user
from api.models.order import CartItem, Escrow, Order, OrderItem
from api.models.product import Product

settings = get_settings()

# ─── Cart ─────────────────────────────────────────────────

cart_router = APIRouter(prefix="/cart", tags=["Cart"])


@cart_router.get("")
async def get_cart(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Giỏ hàng hiện tại."""
    result = await db.execute(
        select(CartItem).where(CartItem.user_id == current_user.id).order_by(CartItem.created_at)
    )
    items = result.scalars().all()

    cart_items = []
    for item in items:
        prod = await db.execute(select(Product).where(Product.id == item.product_id))
        product = prod.scalar_one_or_none()
        if product:
            cart_items.append({
                "id": str(item.id),
                "product_id": str(item.product_id),
                "name": product.name,
                "price": product.price,
                "unit": product.unit,
                "quantity": item.quantity,
                "total": product.price * item.quantity,
                "images": product.images,
            })

    subtotal = sum(i["total"] for i in cart_items)
    vat = int(subtotal * 0.1)

    return {"items": cart_items, "subtotal": subtotal, "vat": vat, "total": subtotal + vat, "count": len(cart_items)}


@cart_router.post("/items", status_code=201)
async def add_to_cart(
    req: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Thêm sản phẩm vào giỏ."""
    product_id = req.get("product_id")
    quantity = req.get("quantity", 1)

    # Check product exists
    prod = await db.execute(select(Product).where(Product.id == product_id))
    if not prod.scalar_one_or_none():
        raise HTTPException(404, "Sản phẩm không tồn tại")

    # Check if already in cart
    existing = await db.execute(
        select(CartItem).where(CartItem.user_id == current_user.id, CartItem.product_id == product_id)
    )
    item = existing.scalar_one_or_none()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.add(item)

    await db.flush()
    return {"message": "Đã thêm vào giỏ hàng", "ok": True}


@cart_router.put("/items/{item_id}")
async def update_cart_item(
    item_id: UUID,
    req: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sửa số lượng."""
    result = await db.execute(select(CartItem).where(CartItem.id == item_id, CartItem.user_id == current_user.id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item không tồn tại")

    quantity = req.get("quantity", 1)
    if quantity <= 0:
        await db.delete(item)
    else:
        item.quantity = quantity

    return {"message": "Đã cập nhật", "ok": True}


@cart_router.delete("/items/{item_id}")
async def remove_cart_item(
    item_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Xóa sản phẩm khỏi giỏ."""
    result = await db.execute(select(CartItem).where(CartItem.id == item_id, CartItem.user_id == current_user.id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item không tồn tại")
    await db.delete(item)
    return {"message": "Đã xóa khỏi giỏ", "ok": True}


# ─── Orders ───────────────────────────────────────────────

order_router = APIRouter(prefix="/orders", tags=["Orders"])


@order_router.post("/checkout", status_code=201)
async def checkout(
    req: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Đặt hàng + tạo Escrow."""
    # Get cart items
    cart_result = await db.execute(select(CartItem).where(CartItem.user_id == current_user.id))
    cart_items = cart_result.scalars().all()
    if not cart_items:
        raise HTTPException(400, "Giỏ hàng trống")

    # Calculate totals
    order_items = []
    subtotal = 0
    for ci in cart_items:
        prod_result = await db.execute(select(Product).where(Product.id == ci.product_id))
        product = prod_result.scalar_one_or_none()
        if not product:
            continue
        item_total = product.price * ci.quantity
        subtotal += item_total
        order_items.append(OrderItem(
            product_id=product.id,
            product_name=product.name,
            quantity=ci.quantity,
            unit_price=product.price,
            total=item_total,
        ))

    vat = int(subtotal * 0.1)
    total = subtotal + vat

    # Generate order number
    order_num = f"NXM-{datetime.now().year}-{uuid_mod.uuid4().hex[:4].upper()}"

    order = Order(
        order_number=order_num,
        buyer_id=current_user.id,
        shipping_address=req.get("shipping_address"),
        receiver_name=req.get("receiver_name"),
        receiver_phone=req.get("receiver_phone"),
        notes=req.get("notes"),
        payment_method=req.get("payment_method", "vnpay"),
        subtotal=subtotal,
        vat=vat,
        total=total,
    )
    db.add(order)
    await db.flush()

    # Add order items
    for oi in order_items:
        oi.order_id = order.id
        db.add(oi)

    # Create Escrow with idempotency key
    escrow = Escrow(
        idempotency_key=f"order-{order.id}",
        buyer_id=current_user.id,
        entity_type="order",
        entity_id=order.id,
        amount=total,
        service_fee=int(total * settings.ESCROW_FEE_PCT / 100),
        auto_release_date=date.today() + timedelta(days=settings.ESCROW_AUTO_RELEASE_DAYS),
    )
    db.add(escrow)
    await db.flush()

    order.escrow_id = escrow.id

    # Clear cart
    for ci in cart_items:
        await db.delete(ci)

    return {
        "order_id": str(order.id),
        "order_number": order_num,
        "total": total,
        "escrow_id": str(escrow.id),
        "message": "Đặt hàng thành công. Vui lòng xác minh OTP.",
        "requires_otp": True,
    }


@order_router.get("")
async def list_orders(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Danh sách đơn hàng."""
    query = select(Order).where(Order.buyer_id == current_user.id)
    if status:
        query = query.where(Order.status == status)
    query = query.order_by(Order.created_at.desc())

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    orders = result.scalars().all()

    return {
        "items": [
            {
                "id": str(o.id), "order_number": o.order_number,
                "total": o.total, "status": o.status,
                "payment_method": o.payment_method,
                "created_at": o.created_at.isoformat(),
                "items": [{"name": i.product_name, "quantity": i.quantity, "total": i.total} for i in o.items],
            }
            for o in orders
        ],
        "total": total, "page": page,
    }


@order_router.get("/{order_id}")
async def get_order(
    order_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chi tiết đơn hàng."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Đơn hàng không tồn tại")
    # IDOR check
    if order.buyer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Không có quyền xem đơn này")

    return {
        "id": str(order.id), "order_number": order.order_number,
        "shipping_address": order.shipping_address,
        "receiver_name": order.receiver_name,
        "receiver_phone": order.receiver_phone,
        "notes": order.notes,
        "payment_method": order.payment_method,
        "subtotal": order.subtotal, "vat": order.vat, "total": order.total,
        "status": order.status, "escrow_id": str(order.escrow_id) if order.escrow_id else None,
        "created_at": order.created_at.isoformat(),
        "items": [
            {"name": i.product_name, "quantity": i.quantity, "unit_price": i.unit_price, "total": i.total}
            for i in order.items
        ],
    }


@order_router.patch("/{order_id}/confirm")
async def confirm_order(
    order_id: UUID,
    req: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Xác nhận nhận hàng → release escrow."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order or order.buyer_id != current_user.id:
        raise HTTPException(404, "Đơn hàng không tồn tại")

    quality = req.get("quality", "correct")
    if quality == "serious":
        # Open dispute instead
        return {"message": "Vui lòng mở khiếu nại", "action": "dispute", "order_id": str(order.id)}

    order.status = "received"

    # Release escrow
    if order.escrow_id:
        escrow_result = await db.execute(select(Escrow).where(Escrow.id == order.escrow_id))
        escrow = escrow_result.scalar_one_or_none()
        if escrow and escrow.status == "held":
            escrow.status = "released"
            escrow.released_at = datetime.now(timezone.utc)

    return {"message": "Đã xác nhận nhận hàng. Escrow đã được giải phóng.", "ok": True}


@order_router.post("/{order_id}/reorder")
async def reorder(
    order_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mua lại tất cả items trong đơn cũ."""
    result = await db.execute(select(Order).where(Order.id == order_id, Order.buyer_id == current_user.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Đơn hàng không tồn tại")

    count = 0
    for item in order.items:
        if item.product_id:
            existing = await db.execute(
                select(CartItem).where(CartItem.user_id == current_user.id, CartItem.product_id == item.product_id)
            )
            cart_item = existing.scalar_one_or_none()
            if cart_item:
                cart_item.quantity += item.quantity
            else:
                db.add(CartItem(user_id=current_user.id, product_id=item.product_id, quantity=item.quantity))
            count += 1

    return {"message": f"Đã thêm {count} sản phẩm vào giỏ", "ok": True}
