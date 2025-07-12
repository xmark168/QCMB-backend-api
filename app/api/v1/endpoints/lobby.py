from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.v1.endpoints.auth import require_roles,get_current_user

from app.core.schemas import LobbyCreate,LobbyOut, MatchPlayerCreate, MatchPlayerOut
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import   MatchPlayer,Topic, User,Lobby
import string
import random

router = APIRouter(prefix="/lobby", tags=["lobby"])

@router.post("/", response_model=LobbyOut, status_code=status.HTTP_201_CREATED)
async def create_lobby(
    payload: LobbyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    topic = await db.get(Topic, payload.topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")

    lobby = Lobby(**payload.model_dump())
    lobby.host_user_id = current_user.id
    lobby.status = "waiting" 
    lobby.code =await  generate_unique_lobby_code(db)
    lobby.created_at = datetime.utcnow()
    lobby.updated_at = datetime.utcnow()
    
    db.add(lobby)
    await db.commit()
    await db.refresh(lobby, attribute_names=["topic"])
    return lobby
@router.get("/", response_model=list[LobbyOut])
async def list_lobbies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
): 
    result = await db.execute(select(Lobby).offset(skip).limit(limit)  .options(selectinload(Lobby.topic))
            .options(selectinload(Lobby.host_user)))
    return result.scalars().all()
@router.get("/waiting", response_model=list[LobbyOut])
async def list_lobbies_waiting(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
): 
    result = await db.execute(select(Lobby).offset(skip).limit(limit)
                                    .options(selectinload(Lobby.topic))
                  .options(selectinload(Lobby.host_user))
                              .where(Lobby.status == "waiting"))
    return result.scalars().all()
async def generate_unique_lobby_code(db: AsyncSession ,
                               length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits  
    while True:
        code = ''.join(random.choices(chars, k=length))
        result = await db.execute(
            select(Lobby.id).where(Lobby.code == code)
      
        )
        exists = result.scalar_one_or_none()
        if exists is None:
            return code 

@router.post("/", response_model=MatchPlayerOut, status_code=status.HTTP_201_CREATED)
async def add_match_player(
    payload: MatchPlayerCreate,
    db: AsyncSession = Depends(get_db)
):
    lobby = await db.get(Lobby, payload.match_id)
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    result = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == payload.match_id,
            MatchPlayer.user_id == payload.user_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Player already joined")

    # Create match player
    match_player = MatchPlayer(
        id=uuid4(),
        match_id=payload.match_id,
        user_id=payload.user_id,
        score=0,
        cards_left=0,
        tokens_earned=0
    )

    db.add(match_player)
    await db.commit()
    await db.refresh(match_player)
    return match_player