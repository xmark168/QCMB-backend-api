import asyncio
from datetime import datetime
from uuid import UUID

from app.api.v1.endpoints.game_session import end_game_after, schedule_end_game, _running_end_game_tasks
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.v1.endpoints.auth import require_roles,get_current_user

from app.core.schemas import LobbyCreate,LobbyOut, MatchCardOut, MatchPlayerCreate, MatchPlayerOut, MatchPlayerRead, SubmitAnswerIn, SubmitAnswerOut
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,and_,func, desc,asc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import   MatchPlayer, Question,Topic, User,Lobby,Match_Card
from ..websockets.ws_game import broadcast
router = APIRouter(prefix="/game", tags=["game"])

@router.get("/{match_id}/players/me/card", response_model=list[MatchCardOut])
async def get_current_card(
    match_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
   
    q = select(Match_Card).where(
        and_(
            Match_Card.match_id == match_id,
            Match_Card.owner_user_id == current_user.id,
            Match_Card.card_state == "pending"
        )
        
    ).order_by(asc(Match_Card.order_no)).options(selectinload(Match_Card.question))
    res = await db.execute(q)
    card = res.scalars().all()
    return card
@router.post("/{match_id}/submit-answer", response_model=SubmitAnswerOut)
async def submit_answer(
    match_id: UUID,
    payload: SubmitAnswerIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q_player = (
        select(MatchPlayer)
        .where(
            MatchPlayer.match_id == match_id,
            MatchPlayer.user_id == current_user.id
        )
        .with_for_update()
    )
    res = await db.execute(q_player)
    player = res.scalar_one_or_none()
    if not player:
        raise HTTPException(404, "Bạn không ở trong phòng này")
    if player.status != "playing":
        raise HTTPException(400, "Trò chơi đã kết thúc")
    q_qc = await db.execute(
        select(Match_Card)
        .where(Match_Card.id == payload.match_card_id)
        .options(selectinload(Match_Card.question))
    )
    qc = q_qc.scalar_one_or_none()
    if not qc:
        raise HTTPException(404, "Không tìm thấy câu hỏi")

    is_correct = (payload.answer.strip().lower() == qc.question.correct_answer.strip().lower())
    
    score = qc.question.difficulty if is_correct else 0

    if not is_correct:
        m = await db.execute(
            select(Lobby).where(Lobby.id == match_id)
            .options(selectinload(Lobby.topic))
        )
        match = m.scalar_one()
        topic = match.topic_id
        q_rand = await db.execute(
            select(Question)
            .where(Question.topic_id == topic)
            .order_by(func.random())
            .limit(1)
        )
        max_res = await db.execute(
            select(func.coalesce(func.max(Match_Card.order_no), 0))
            .where(Match_Card.match_id == match_id)
        )
        current_max = max_res.scalar_one()
        question = q_rand.scalar_one_or_none()
        if question:
            new_card = Match_Card(
                match_id=match_id,
                question_card_id=question.id,
                owner_user_id = current_user.id,
                order_no = current_max + 1,
                card_state="pending"
            )
            db.add(new_card)
            await db.commit()
            await db.refresh(new_card)
    else:
        player.cards_left -= 1
    qc.card_state = "answered"
    player.score = player.score+ score
    player.tokens_earned = player.score // 10 if is_correct else 0
    
    # 6. Cập nhật tổng score của player
    if player.cards_left <= 0:
        # Schedule end game task
        old = _running_end_game_tasks.get(match_id)
        if old and not old.done():
             old.cancel()
        task = asyncio.create_task(end_game_after(match_id ,0))
        print("Task status 222:", task)
    await db.commit()
    await db.refresh(player)
    await db.refresh(qc)
    # 8. Broadcast sự kiện
    await broadcast(match_id, {
        "event": "update_score",
        "user_id": str(current_user.id),
       
    })

    return SubmitAnswerOut(
          correct=is_correct,
    )