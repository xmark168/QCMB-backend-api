from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.v1.endpoints.auth import require_roles
from app.core.enums import UserRole
from app.core.schemas import QuestionCreate, QuestionOut, QuestionUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.models import Question, Topic, User


router = APIRouter(prefix="/questions", tags=["questions"])

# -------- 1. Liệt kê --------
@router.get("/", response_model=list[QuestionOut])
async def list_questions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Question).offset(skip).limit(limit))
    return result.scalars().all()

# -------- 2. Xem chi tiết --------
@router.get("/{q_id}", response_model=QuestionOut)
async def get_question(
    q_id: UUID,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    question = await db.get(Question, q_id)
    if not question:
        raise HTTPException(404, "Question not found")
    return question

# -------- 3. Tạo mới --------
@router.post("/", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def create_question(
    payload: QuestionCreate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    # bảo đảm Topic tồn tại
    topic = await db.get(Topic, payload.topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")

    question = Question(**payload.model_dump())
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question

# -------- 4. Cập nhật --------
@router.put("/{q_id}", response_model=QuestionOut)
async def update_question(
    q_id: UUID,
    payload: QuestionUpdate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    question = await db.get(Question, q_id)
    if not question:
        raise HTTPException(404, "Question not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)

    await db.commit()
    await db.refresh(question)
    return question

# -------- 5. Xoá --------
@router.delete("/{q_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    q_id: UUID,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    question = await db.get(Question, q_id)
    if not question:
        raise HTTPException(404, "Question not found")

    await db.delete(question)
    await db.commit()