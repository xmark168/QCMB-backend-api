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
    host_player = MatchPlayer(
        match_id=lobby.id,
        user_id=current_user.id,
        score=0,
        cards_left=lobby.initial_hand_size,
        tokens_earned=0,
        status="waiting"  
    )
    db.add(host_player)
    await db.commit()
    await db.refresh(host_player)
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

@router.post("/join", response_model=MatchPlayerOut, status_code=status.HTTP_201_CREATED)
async def join_lobby(
    payload: MatchPlayerCreate,
    db: AsyncSession = Depends(get_db),
    currentUser : User = Depends(get_current_user),
):
    lobby1 = await db.execute(
        select(Lobby)
        .where(Lobby.id == payload.match_id)
        .with_for_update()  # locks the row
    )
    lobby = lobby1.scalar_one_or_none()
    
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")
    if lobby.status != "waiting":
        raise HTTPException(status_code=400, detail="Lobby is not in waiting status")
    if lobby.player_count_limit > 0 and lobby.player_count >= lobby.player_count_limit:
        raise HTTPException(status_code=400, detail="Lobby player limit reached")
    result = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == payload.match_id,
            MatchPlayer.user_id == currentUser.id
        )
        
    )
    
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Player already joined")

    # Create match player
    match_player = MatchPlayer(
        match_id=payload.match_id,
        user_id=currentUser.id,
        score=0,
        cards_left=0,
        tokens_earned=0,
        created_at=datetime.utcnow(),
        status="waiting"  # Trạng thái ban đầu của người chơi
    )

    db.add(match_player)
    
    lobby.player_count += 1  
    lobby.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(match_player)
    return match_player
@router.post("/join-by-code", response_model=MatchPlayerOut, status_code=status.HTTP_201_CREATED)
async def join_lobby_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Lobby)
        .where(Lobby.code == code)
        .with_for_update()
    )
    lobby = result.scalar_one_or_none()
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")
    if lobby.status != "waiting":
        raise HTTPException(status_code=400, detail="Lobby is not in waiting status")

    if lobby.player_count_limit > 0 and lobby.player_count >= lobby.player_count_limit:
        raise HTTPException(status_code=400, detail="Lobby player limit reached")
    existing = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == lobby.id,
            MatchPlayer.user_id == current_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already joined this lobby")
    
    player = MatchPlayer(
        match_id=lobby.id,
        user_id=current_user.id,
        score=0,
        cards_left=0,
        tokens_earned=0,
        created_at=datetime.utcnow(),
        status="waiting"
    )
    
    db.add(player)
    
    lobby.player_count += 1
    lobby.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(player)

    return player