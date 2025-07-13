from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.v1.endpoints.auth import require_roles,get_current_user

from app.core.schemas import LobbyCreate,LobbyOut, MatchPlayerCreate, MatchPlayerOut, MatchPlayerRead
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,update
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import   MatchPlayer, Question,Topic, User,Lobby
import string
import random
from ..websockets.ws_lobby import broadcast
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

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
        raise HTTPException(status_code=404, detail="Không tim thấy phòng chơi")
    if lobby.status != "waiting":
        raise HTTPException(status_code=400, detail="Phòng đang chơi hoặc đã kết thúc")
    if lobby.player_count_limit > 0 and lobby.player_count >= lobby.player_count_limit:
        raise HTTPException(status_code=400, detail="Phòng đã dầy người chơi")
    result = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == payload.match_id,
            MatchPlayer.user_id == currentUser.id
        )
        
    )
    
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Bạn đã ở trong phòng này rồi")

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
    await db.refresh(lobby)
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
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng chơi với mã này")
    if lobby.status != "waiting":
        raise HTTPException(status_code=400, detail="Phòng đang chơi hoặc đã kết thúc")

    if lobby.player_count_limit > 0 and lobby.player_count >= lobby.player_count_limit:
        raise HTTPException(status_code=400, detail="Phòng đã đầy người chơi")
    existing = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == lobby.id,
            MatchPlayer.user_id == current_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bạn đã tham gia phòng này rồi")
    
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
    await db.refresh(lobby)

    return player

@router.get("/{lobby_id}", response_model=LobbyOut)
async def get_lobby_by_id(
    lobby_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Lobby)
        .where(Lobby.id == lobby_id)
        .options(
            selectinload(Lobby.topic),
            selectinload(Lobby.host_user)
        )
    )
    lobby = result.scalar_one_or_none()
    
    if not lobby:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng chơi")
    
    return lobby

@router.get("/{lobby_id}/players", response_model=list[MatchPlayerRead])
async def list_lobby_players(
    lobby_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    lobby = await db.get(Lobby, lobby_id)
    if not lobby:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng chơi")
    
    players = await db.execute(
        select(MatchPlayer)
        .where(MatchPlayer.match_id == lobby_id, MatchPlayer.status != "left")
        .options(selectinload(MatchPlayer.user))
    )
    
    return players.scalars().all()
@router.post("/{lobby_id}/ready", response_model=MatchPlayerOut)
async def player_ready(
    lobby_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    result = await db.execute(
        select(MatchPlayer)
        .where(
            MatchPlayer.match_id == lobby_id,
            MatchPlayer.user_id == current_user.id
        )
        .with_for_update()
    )
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Bạn không ở trong phòng này")
    
    if player.status == "ready":
        raise HTTPException(status_code=400, detail="Bạn đã ở trạng thái sẵn sàng")
    if player.status != "waiting":
        raise HTTPException(status_code=400, detail=f"Không thể chuyển trạng thái từ {player.status} sang ready")
    
    player.status = "ready"
    
    await db.commit()
    await db.refresh(player)
     
    await broadcast(lobby_id,{
        "event": "ready",
        "user_id": str(current_user.id)
    })
    
    return player

@router.post("/{lobby_id}/unready", response_model=MatchPlayerOut)
async def player_unready(
    lobby_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    result = await db.execute(
        select(MatchPlayer)
        .where(
            MatchPlayer.match_id == lobby_id,
            MatchPlayer.user_id == current_user.id
        )
        .with_for_update()
    )
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Bạn không ở trong phòng này")

    if player.status == "waiting":
        raise HTTPException(status_code=400, detail="Bạn đang ở trạng thái chờ")
    if player.status != "ready":
        raise HTTPException(status_code=400, detail=f"Không thể chuyển trạng thái từ {player.status} sang waiting")

    player.status = "waiting"

    await db.commit()
    await db.refresh(player)

    await broadcast(lobby_id, {
        "event": "ready",
        "user_id": str(current_user.id)
    })

    return player
@router.post("/{lobby_id}/start", response_model=LobbyOut)
async def start_game(
    lobby_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lobby)
        .where(Lobby.id == lobby_id)
        .with_for_update()
    )
    lobby = result.scalar_one_or_none()
    if not lobby:
        raise HTTPException(404, "Lobby not found")
    if lobby.host_user_id != current_user.id:
        raise HTTPException(403, "Only the host can start the game")
    if lobby.status != "waiting":
        raise HTTPException(400, "Game already started or finished")

    # update lobby status
    lobby.status = "playing"
    lobby.started_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lobby)
    
     # prepare random questions and link items
    questions = (await db.execute(
        select(Question).where(Question.topic_id == lobby.topic_id)
    )).scalars().all()
    create_question_cards(lobby.id, questions, db)
    
    await broadcast(lobby_id, {"event": "start", "by": str(current_user.id)})

    asyncio.create_task(end_game_after(lobby_id, lobby.match_time_sec))

    return lobby

async def end_game_after(lobby_id: UUID, duration: int):

    try:
        await asyncio.sleep(duration)
    except asyncio.CancelledError:
        return

    async with async_session() as session:
        # mark remaining players as finished
        await session.execute(
            update(MatchPlayer)
            .where(
                MatchPlayer.match_id == lobby_id,
                MatchPlayer.status != "left"
            )
            .values(status="finished")
        )
        # update lobby status
        result = await session.execute(select(Lobby).where(Lobby.id == lobby_id))
        lobby = result.scalar_one_or_none()
        if lobby:
            lobby.status = "finished"
            lobby.ended_at = datetime.utcnow()
            await session.commit()

    await broadcast(lobby_id, {"event": "end"})
def create_question_cards(match_id: UUID, questions: list[Question],  db: AsyncSession):

    random.shuffle(questions)
    
    count = min(len(questions))
    selected_qs = questions[:count]

    for idx, question in enumerate(selected_qs, start=1):
        mc = Match_Card(
            match_id=match_id,
            question_card_id=question.id,
            card_state="pending",
            owner_user_id=None,
            order_no=idx,
            is_initial=True,
            created_at=datetime.utcnow()
        )
        db.add(mc)    
@router.post("/{lobby_id}/start", response_model=LobbyOut)
async def start_game(
    lobby_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lobby)
        .where(Lobby.id == lobby_id)
        .with_for_update()
    )
    lobby = result.scalar_one_or_none()
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")
    if lobby.host_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the host can start the game")
    if lobby.status != "waiting":
        raise HTTPException(status_code=400, detail="Game already started or finished")

    lobby.status = "playing"
    lobby.started_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lobby)

    await broadcast(lobby_id, {"event": "start", "by": str(current_user.id)})

    asyncio.create_task(end_game_after(lobby_id, lobby.match_time_sec))

    return lobby
