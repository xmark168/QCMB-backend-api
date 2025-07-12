from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import Enum, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.email_utils import send_password_reset_email
from ....core.database import get_db
from ....core.models import User
from ....core.schemas import (
    AvatarUpdateRequest, ForgotPasswordRequest, ForgotPasswordResponse, GenericMessage, 
    LoginInput, PasswordChangeRequest, ProfileUpdateRequest, 
    RegisterResponse, ResetWithVerifiedToken, UserRole, 
    UserCreate, UserRead, Token, VerifyOtpInput, VerifyOtpResponse
)
from ....core.security import (
    generate_raw_otp, hash_otp,
    create_otp_token, create_verified_token, decode_token,
    get_password_hash, verify_password, create_access_token, decode_access_token
)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(
    scheme_name="JWTBearer",
    description="Paste the JWT you received from /auth/login",
    bearerFormat="JWT"
)# ---------- Đăng ký ----------
@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    for field in ("username", "email"):
        exist = await db.scalar(select(User).filter_by(**{field: getattr(user_in, field)}))
        if exist:
            raise HTTPException(400, f"{field} already registered")
        
    user = User(
        name=user_in.name,
        username=user_in.username,
        email=user_in.email,
        avatar_url='',
        password=get_password_hash(user_in.password),
        token_balance=100,
        score=0
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        {
            "sub": str(user.id),
            "role": user.role.value
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }
# ---------- Đăng nhập ----------
@router.post("/login", response_model=RegisterResponse)
async def login(data: LoginInput,
                db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(
        or_(User.username == data.username, 
            User.email == data.username)
    )

    user = await db.scalar(stmt)

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid credentials"
        )

    token = create_access_token(
        {"sub": str(user.id), "role": user.role.value}
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }
# ---------- Lấy người dùng hiện tại ----------
@router.get("/currentUser", response_model=UserRead)
async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                           db: AsyncSession = Depends(get_db)) -> User:
    token: str = creds.credentials
    payload = decode_access_token(token)
    if payload is None:
         raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalid or expired")
    
    user = await db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    
    return user
# ---------- Check quyền admin----------
def admin_required(current: User = Depends(get_current_user)):
    if current.role != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return current
# authrorization decorator
def require_roles(*roles: UserRole):
    def checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            print(f"User {current_user.username} with role {current_user.role} tried to access a protected route {roles}")
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Bạn không đủ quyền truy cập",
            )
        return current_user
    return checker

# ---------- gửi OTP ----------
@router.post("/forgot-password", response_model=ForgotPasswordResponse, status_code=status.HTTP_200_OK)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.email == data.email))
    # Trả về giống nhau để tránh dò email (OWASP) :contentReference[oaicite:5]{index=5}
    if user:
        raw_otp = generate_raw_otp()
        otp_hash = hash_otp(raw_otp)
        otp_token = create_otp_token(user.id, otp_hash)
        background_tasks.add_task(send_password_reset_email, user.email, raw_otp)
        return {
            "detail": "OTP đã được gửi.",
            "otp_token": otp_token
        }
    
    return {
        "detail": "Nếu email không tồn tại",
        "otp_token": None
    }

# ---------- Xác thực OTP ----------
@router.post("/verify-otp", response_model=VerifyOtpResponse, status_code=status.HTTP_200_OK)
async def verify_otp(data: VerifyOtpInput):
    payload = decode_token(data.otp_token)
    if payload.get("scope") != "password_reset_otp":
        raise HTTPException(400, "Sai scope token")
    
    if hash_otp(data.otp) != payload["otp_hash"]:
        raise HTTPException(400, "OTP không hợp lệ")
    
    verified_token = create_verified_token(int(payload["sub"]))
    return {
        "detail": "OTP xác thực thành công",
        "verified_token": verified_token
    }

# ---------- Đặt lại mật khẩu ----------
@router.post("/reset-password", response_model=GenericMessage, status_code=status.HTTP_200_OK)
async def reset_password(
    data: ResetWithVerifiedToken,
    db: AsyncSession = Depends(get_db)
):
    payload = decode_token(data.verified_token)
    if payload.get("scope") != "otp_verified":
        raise HTTPException(400, "Token không đúng giai đoạn")
    
    user = await db.scalar(select(User).where(User.id == int(payload["sub"]), User.email == data.email))
    if not user:
        raise HTTPException(400, "Người dùng không tồn tại hoặc email không khớp")
    
    user.password = get_password_hash(data.new_password)
    await db.commit()
    return {
        "detail": "Đổi mật khẩu thành công"
    }

# ---------- Cập nhật profile ----------
@router.put("/profile", response_model=GenericMessage, status_code=status.HTTP_200_OK)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cập nhật thông tin cá nhân (tên, email)"""
    
    # Cập nhật thông tin
    if data.name is not None:
        current_user.name = data.name
    if data.email is not None:
        current_user.email = data.email
    
    await db.commit()
    await db.refresh(current_user)
    
    return GenericMessage(
        detail="Cập nhật thông tin thành công"
    )

# ---------- Cập nhật avatar ----------
@router.put("/avatar", response_model=GenericMessage)
async def update_avatar(
    data: AvatarUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cập nhật avatar của người dùng"""
    
    current_user.avatar_url = data.avatar_url
    
    await db.commit()
    await db.refresh(current_user)
    
    return GenericMessage(
        detail="Cập nhật avatar thành công"
    )

# ---------- Thay đổi mật khẩu ----------
@router.put("/password", response_model=GenericMessage)
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Thay đổi mật khẩu của người dùng"""
    
    # Xác thực mật khẩu hiện tại
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không đúng"
        )
    
    current_user.password = get_password_hash(data.new_password)
    await db.commit()
    return GenericMessage(
        detail="Đổi mật khẩu thành công"
    )
