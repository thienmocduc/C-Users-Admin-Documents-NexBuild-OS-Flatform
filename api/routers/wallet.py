"""Wallet, Transactions, Bank Accounts router."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import get_current_user
from api.models.finance import BankAccount, Transaction, Wallet

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("")
async def get_wallet(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Số dư + thống kê ví."""
    result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        wallet = Wallet(user_id=current_user.id)
        db.add(wallet)
        await db.flush()

    return {
        "available_balance": wallet.available_balance,
        "escrow_held": wallet.escrow_held,
        "b2b_credit_limit": wallet.b2b_credit_limit,
        "b2b_credit_used": wallet.b2b_credit_used,
        "nxt_balance": wallet.nxt_balance,
    }


@router.post("/topup")
async def topup(req: dict, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Nạp tiền vào ví."""
    amount = req.get("amount", 0)
    if amount <= 0:
        raise HTTPException(400, "Số tiền phải lớn hơn 0")

    result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        wallet = Wallet(user_id=current_user.id)
        db.add(wallet)
        await db.flush()

    wallet.available_balance += amount

    tx = Transaction(
        user_id=current_user.id,
        type="topup",
        amount=amount,
        balance_after=wallet.available_balance,
        description=f"Nạp tiền {req.get('payment_method', 'vnpay')}",
    )
    db.add(tx)

    return {"message": f"Đã nạp {amount:,}đ", "balance": wallet.available_balance}


@router.post("/withdraw")
async def withdraw(req: dict, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Rút tiền về tài khoản ngân hàng."""
    amount = req.get("amount", 0)
    if amount <= 0:
        raise HTTPException(400, "Số tiền phải lớn hơn 0")

    result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()
    if not wallet or wallet.available_balance < amount:
        raise HTTPException(400, "Số dư không đủ")

    wallet.available_balance -= amount

    tx = Transaction(
        user_id=current_user.id,
        type="withdraw",
        amount=-amount,
        balance_after=wallet.available_balance,
        reference_type="bank",
        description=req.get("note", "Rút tiền về ngân hàng"),
    )
    db.add(tx)

    return {"message": f"Đã yêu cầu rút {amount:,}đ. Xử lý trong T+1.", "balance": wallet.available_balance}


@router.get("/transactions")
async def list_transactions(
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lịch sử giao dịch."""
    query = select(Transaction).where(Transaction.user_id == current_user.id)
    if type:
        query = query.where(Transaction.type == type)
    query = query.order_by(Transaction.created_at.desc())

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    txs = result.scalars().all()

    return [
        {
            "id": str(t.id), "type": t.type, "amount": t.amount,
            "balance_after": t.balance_after, "description": t.description,
            "status": t.status, "created_at": t.created_at.isoformat(),
        }
        for t in txs
    ]


@router.get("/bank-accounts")
async def list_bank_accounts(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Danh sách tài khoản ngân hàng."""
    result = await db.execute(select(BankAccount).where(BankAccount.user_id == current_user.id))
    accounts = result.scalars().all()
    return [
        {"id": str(a.id), "bank_name": a.bank_name, "account_holder": a.account_holder,
         "is_default": a.is_default}
        for a in accounts
    ]


@router.post("/bank-accounts", status_code=201)
async def add_bank_account(req: dict, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Thêm tài khoản ngân hàng."""
    # TODO: encrypt account_number with AES-256
    account = BankAccount(
        user_id=current_user.id,
        bank_name=req.get("bank_name"),
        account_number_encrypted=req.get("account_number"),  # TODO: encrypt
        account_holder=req.get("account_holder"),
    )
    db.add(account)
    await db.flush()
    return {"id": str(account.id), "message": "Đã thêm tài khoản ngân hàng"}
