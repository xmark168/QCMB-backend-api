from app.api.v1.endpoints.auth import Role, get_current_user, require_roles
from app.core.database import get_db
from app.core.models import User
from app.core.schemas import UserCreateAdmin, UserOut, UserUpdate
from app.core.security import get_password_hash
from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["users"])

# ---------- 1. Liệt kê ----------
@router.get("", response_model=list[UserOut])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    users = (await db.execute(select(User).offset(skip).limit(limit))).scalars().all()
    return users

# ---------- 2. Tạo mới ----------
@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserCreateAdmin,
    _: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
     # kiểm tra trùng username / email
    for field in ("username", "email"):
        exists = await db.scalar(select(User).filter_by(**{field: getattr(payload, field)}))
        if exists:
            raise HTTPException(400, f"{field} already exists")\
            
    user = User(
        name=payload.name,
        username=payload.username,
        email=payload.email,
        role=payload.role,
        token_balance=payload.token_balance,
        password=get_password_hash(payload.password),
        ranking_rate=0, 
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
# ---------- 3. Xem chi tiết ----------
@router.get("/{user_id}", response_model=UserOut)
async def retrieve_user(
    user_id: int,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
   user = await db.get(User, user_id)
   if not user:
      raise HTTPException(404, "User not found")
   if current.role != Role.ADMIN and current.id != user.id:
        raise HTTPException(403, "Forbidden")
   return user

# ---------- 4. Cập nhật ----------
@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
   user = await db.get(User, user_id)
   if not user:
        raise HTTPException(404, "User not found")
   if current.role != Role.ADMIN and current.id != user.id:
        raise HTTPException(403, "Forbidden")
   if payload.password:
        payload.password = get_password_hash(payload.password)
   for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)
   await db.commit()
   await db.refresh(user)
   return user

# ---------- 5. Xoá (hoặc vô hiệu hoá) ----------
@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    _: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(delete(User).where(User.id == user_id))
    if result.rowcount == 0:
        raise HTTPException(404, "User not found")
    await db.commit()
    return