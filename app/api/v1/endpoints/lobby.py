from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.v1.endpoints.auth import require_roles,get_current_user
from app.core.enums import UserRole
from app.core.schemas import QuestionCreate, QuestionOut, QuestionUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.models import Question, Topic, User


router = APIRouter(prefix="/lobby", tags=["lobby"])

# -------- 3. Tạo mới --------
@router.post("/", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def create_question(
    payload: QuestionCreate,
    _: User = Depends(get_current_user),
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
