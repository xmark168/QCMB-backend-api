import asyncio
from datetime import datetime
import random
from uuid import UUID

from app.api.v1.endpoints.game_session import end_game_after, schedule_end_game, _running_end_game_tasks
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.v1.endpoints.auth import require_roles,get_current_user

from app.core.schemas import BringItemsRequest, LobbyCreate,LobbyOut, MatchCardOut, MatchPlayerCreate, MatchPlayerOut, MatchPlayerRead, SubmitAnswerIn, SubmitAnswerOut
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,and_,func, desc,asc,update
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import   Inventory, MatchPlayer, MatchPlayerItem, Question,Topic, User,Lobby,Match_Card
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
        
    ).order_by(asc(Match_Card.order_no)).options(selectinload(Match_Card.question)).options(selectinload(Match_Card.item))
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
    q_qc = await db.execute (
        select(Match_Card)
        .where(Match_Card.id == payload.match_card_id)
        .options(selectinload(Match_Card.question))
        .options(selectinload(Match_Card.item)
    ))
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
        player.score = player.score + score
        if qc.item:
          type = qc.item.type
          if type == 'DOUBLE_SCORE':
               player.score = player.score + score
          elif type == 'POWER_SCORE':
               player.score = player.score + (score // 2) 
          elif  type == 'GHOST_TURN':
           
            q_rand = await db.execute(
                select(Match_Card)
                .where(and_(Match_Card.match_id == match_id,
                            Match_Card.card_state == "pending",
                            Match_Card.owner_user_id == current_user.id)
                            )
                
                .order_by(func.random())
                .limit(1)
            )
            q= q_rand.scalar_one_or_none()
            if not q:
                 pass
            else:
                player.cards_left -= 1
                q.card_state = "answered"
                player.score = player.score + q.question.difficulty
          elif type == 'POINT_STEAL':
            target_query = await db.execute(
                select(MatchPlayer)
                .where(and_(
                    MatchPlayer.match_id == match_id,
                    MatchPlayer.user_id != current_user.id,
                    MatchPlayer.status == "playing"
                ))
                .order_by(desc(MatchPlayer.score))
                .with_for_update()  # Lock target player
                .limit(1)
            )
            target_player = target_query.scalar_one_or_none()
            if target_player:
                steal_amount = random.randint(1, 10)  
               
                target_player.score -= steal_amount
                player.score += steal_amount
                await db.commit()
                await db.refresh(target_player)
                    
    qc.card_state = "answered"
    
    player.tokens_earned = player.score // 10 if is_correct else 0
    
    if player.cards_left <= 0:
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
    
@router.post("/{match_id}/bring-items", response_model=str)
async def bring_items_to_match(
    match_id: UUID,
    request: BringItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lobby = await db.get(Lobby, match_id)
    if not lobby or lobby.status != "playing":
        raise HTTPException(
            status_code=400,
            detail="Trận chơi không hợp lệ"
        )
    match_player_query = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == match_id,
            MatchPlayer.user_id == current_user.id
        )
    )
    match_player = match_player_query.scalar_one_or_none()
    if not match_player:
        raise HTTPException(
            status_code=400,
            detail="User is not a player in this match"
        )
        
    available_cards_query = await db.execute(
        select(Match_Card).where(
            Match_Card.match_id == match_id,
            Match_Card.card_state == "pending",
            Match_Card.owner_user_id== current_user.id
        )
    )
    available_cards = available_cards_query.scalars().all()

    for item in request.items:
        if item.quantity <= 0:
            continue
        # Check inventory for the user and card
        inventory_query = await db.execute(
            select(Inventory).where(
                Inventory.user_id == current_user.id,
                Inventory.card_id == item.card_id
            )
        )
        inventory = inventory_query.scalar_one_or_none()

        if not inventory or inventory.quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient quantity for card {item.card_id}"
            )

        # Create MatchPlayerItem entry
        match_player_item = MatchPlayerItem(
            match_player_id=match_player.id,
            card_id=item.card_id,
            quantity_used=item.quantity
        )
        db.add(match_player_item)

        inventory.quantity -= item.quantity
        
        if available_cards:
            selected_card = random.choice(available_cards)
            # Update the Match_Card with the item and owner
            await db.execute(
                update(Match_Card)
                .where(Match_Card.id == selected_card.id)
                .values(
                    item_id=item.card_id
                )
            )
            available_cards.remove(selected_card)

    await db.commit()
    await db.refresh(match_player)
    
    
    return "Items brought successfully to the match"