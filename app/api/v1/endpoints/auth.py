from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ....core.database import get_db
from ....core.models import User
from ....core.schemas import LoginInput, UserCreate, UserRead, Token
from ....core.security import (
    get_password_hash, verify_password,
    create_access_token, decode_access_token
)

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
# ---------- Đăng ký ----------
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    for field in ("username", "email"):
        exist = await db.scalar(select(User).filter_by(**{field: getattr(user_in, field)}))
        if exist:
            raise HTTPException(400, f"{field} already registered")
        
    user = User(
        name=user_in.name,
        username=user_in.username,
        email=user_in.email,
        password=get_password_hash(user_in.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
# ---------- Đăng nhập ----------
@router.post("/login", response_model=Token)
async def login(data: LoginInput,
                db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).filter_by(username=data.username))
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}
# ---------- Lấy người dùng hiện tại ----------
async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_db)) -> User:
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

class Role(str, Enum):
    PLAYER = "PLAYER"
    ADMIN  = "ADMIN"
def require_roles(*roles: Role):
    def checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Bạn không đủ quyền truy cập",
            )
        return current_user
    return checker