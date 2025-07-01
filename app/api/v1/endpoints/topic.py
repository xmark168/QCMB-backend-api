from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.core.models import Topic, User
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import select

from app.api.v1.endpoints.auth import require_roles
from app.core.database import get_db
from app.core.enums import UserRole
from app.core.schemas import TopicCreate, TopicOut, TopicUpdate


router = APIRouter(prefix="/topics", tags=["topics"])

# -------- 1. Liệt kê --------
@router.get("/", response_model=list[TopicOut])
async def list_topics(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Topic).offset(skip).limit(limit))
    return result.scalars().all()

# -------- 2. Xem chi tiết --------
@router.get("/{topic_id}", response_model=TopicOut)
async def get_topic(
    topic_id: UUID,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    return topic


# -------- 3. Tạo mới --------
@router.post("/", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
async def create_topic(
    payload: TopicCreate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    # bảo toàn unique name
    exists = await db.scalar(select(Topic).filter_by(name=payload.name))
    if exists:
        raise HTTPException(400, "Name already exists")

    # tạo mới topic
    topic = Topic(**payload.model_dump()) 
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic

# -------- 4. Cập nhật --------
@router.put("/{topic_id}", response_model=TopicOut)
async def update_topic(
    topic_id: UUID,
    payload: TopicUpdate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(topic, field, value)

    await db.commit()
    await db.refresh(topic)
    return topic

# -------- 5. Xoá --------
@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: UUID,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")

    await db.delete(topic)
    await db.commit()