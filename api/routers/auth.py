"""Auth router — register, login, refresh, logout, preferences."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.redis import get_redis
from api.core.security import (
    check_login_rate_limit,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    record_login_attempt,
    verify_password,
)
from api.models.community import AuditLog
from api.models.finance import Wallet
from api.models.user import RefreshToken, User, UserPreference
from api.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    PreferenceUpdateRequest,
    RegisterRequest,
    TokenResponse,
    UserPreferenceResponse,
    UserResponse,
    VerifyOTPRequest,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Đăng ký tài khoản mới."""
    # Check email exists
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email đã được sử dụng")

    # Check phone exists
    if req.phone:
        existing_phone = await db.execute(select(User).where(User.phone == req.phone))
        if existing_phone.scalar_one_or_none():
            raise HTTPException(400, "Số điện thoại đã được sử dụng")

    user = User(
        email=req.email,
        phone=req.phone,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        role=req.role,
        status="active",  # TODO: change to "pending" when email verification is ready
    )
    db.add(user)
    await db.flush()

    # Create preferences
    pref = UserPreference(user_id=user.id)
    db.add(pref)

    # Create wallet
    wallet = Wallet(user_id=user.id)
    db.add(wallet)

    return MessageResponse(message="Đăng ký thành công. Vui lòng kiểm tra email để xác minh.")


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_conn=Depends(get_redis),
    _rate=Depends(check_login_rate_limit),
):
    """Đăng nhập — trả JWT access + set refresh cookie."""
    ip = request.client.host if request.client else "unknown"

    # Find user by email or phone
    result = await db.execute(
        select(User).where(
            or_(User.email == req.email_or_phone, User.phone == req.email_or_phone)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        await record_login_attempt(ip, False, redis_conn)
        # Audit
        db.add(AuditLog(event_type="LOGIN_FAILED", ip_address=ip, details={"email": req.email_or_phone}))
        raise HTTPException(401, "Email/SĐT hoặc mật khẩu không đúng")

    if user.status == "suspended":
        raise HTTPException(403, "Tài khoản đã bị khóa")

    # Success
    await record_login_attempt(ip, True, redis_conn)
    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id))

    # Store refresh token hash
    exp_timestamp = decode_token(refresh_token)["exp"]
    exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) if isinstance(exp_timestamp, (int, float)) else exp_timestamp
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_password(refresh_token),
        expires_at=exp_dt,
    )
    db.add(rt)

    # Update last_login
    user.last_login = datetime.now(timezone.utc)

    # Audit
    db.add(AuditLog(user_id=user.id, event_type="LOGIN_SUCCESS", ip_address=ip, severity="success"))

    # Set HttpOnly cookie for refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 3600,
        path="/api/v1/auth",
    )

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using HttpOnly cookie."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "Refresh token không tồn tại")

    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Token không hợp lệ")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User không tồn tại")

    # Rotate: create new tokens, revoke old
    new_access = create_access_token(str(user.id), user.role)
    new_refresh = create_refresh_token(str(user.id))

    # Store new refresh
    exp_ts = decode_token(new_refresh)["exp"]
    exp_dt2 = datetime.fromtimestamp(exp_ts, tz=timezone.utc) if isinstance(exp_ts, (int, float)) else exp_ts
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_password(new_refresh),
        expires_at=exp_dt2,
    )
    db.add(rt)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 3600,
        path="/api/v1/auth",
    )

    return {"access_token": new_access, "token_type": "bearer"}


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """Đăng xuất — xóa refresh cookie."""
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    return MessageResponse(message="Đăng xuất thành công")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    """Lấy thông tin user hiện tại."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    updates: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật thông tin user (full_name, avatar_url, supplier fields)."""
    allowed = {"full_name", "avatar_url", "store_name", "supplier_type", "main_category", "delivery_area", "supplier_intro"}
    for key, value in updates.items():
        if key in allowed:
            setattr(current_user, key, value)
    return UserResponse.model_validate(current_user)


@router.get("/me/preferences", response_model=UserPreferenceResponse)
async def get_preferences(current_user=Depends(get_current_user)):
    """Lấy lang/theme preferences."""
    if current_user.preferences:
        return UserPreferenceResponse.model_validate(current_user.preferences)
    return UserPreferenceResponse(lang="VI", theme="dark", daily_quota=3)


@router.patch("/me/preferences", response_model=UserPreferenceResponse)
async def update_preferences(
    req: PreferenceUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật lang/theme."""
    pref = current_user.preferences
    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)
        await db.flush()

    if req.lang is not None:
        pref.lang = req.lang
    if req.theme is not None:
        pref.theme = req.theme

    return UserPreferenceResponse.model_validate(pref)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(req: ForgotPasswordRequest):
    """Gửi link reset password qua email."""
    # TODO: implement email sending
    return MessageResponse(message="Nếu email tồn tại, link đặt lại mật khẩu đã được gửi.")


@router.post("/verify-otp", response_model=MessageResponse)
async def verify_otp(req: VerifyOTPRequest):
    """Xác minh OTP cho checkout/escrow."""
    # TODO: implement OTP verification via Redis
    return MessageResponse(message="OTP xác minh thành công")
