import asyncio
from datetime import datetime
from typing import Dict, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.v1.endpoints.auth import require_roles,get_current_user

from app.core.schemas import LobbyCreate,LobbyOut, MatchPlayerCreate, MatchPlayerOut, MatchPlayerRead
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,update
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSess, get_db
from app.core.models import   Match_Card, MatchPlayer, Question,Topic, User,Lobby
import string
import random
from ..websockets.ws_lobby import broadcast
from ..websockets.ws_game  import broadcast as game_broadcast

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import  Depends

# 1) Nơi global (hoặc singleton) để lưu task theo lobby_id
_running_end_game_tasks: dict[UUID, asyncio.Task] = {}


def schedule_end_game(lobby_id: UUID, duration: int, db: AsyncSession = Depends(get_db)):
    # Nếu đã có task cũ, hủy trước
    old = _running_end_game_tasks.get(lobby_id)
    if old and not old.done():
        old.cancel()

    # Tạo task mới và lưu lại
    task = asyncio.create_task(end_game_after(lobby_id, duration, db))
    _running_end_game_tasks[lobby_id] = task
    print("Task status:", task, task.done(), task.cancelled())

    return task


def cancel_end_game(lobby_id: UUID):
    task = _running_end_game_tasks.pop(lobby_id, None)
    if task and not task.done():
        task.cancel()
        return True
    return False

async def end_game_after(lobby_id: UUID, duration: int ): 

    try:
        await asyncio.sleep(duration* 60)
    except asyncio.CancelledError:
        return

    print(f"Ending game for lobby {lobby_id} after {duration} minutes")
    async with AsyncSess() as db:
        await db.execute(
          update(MatchPlayer)
        .where(
            MatchPlayer.match_id == lobby_id,
            MatchPlayer.status != "left",
        )
        .values(status="finished")
        )
    # consult results and update user
        result = await db.execute(
            select(MatchPlayer).where(MatchPlayer.match_id == lobby_id)
        )
        match_players = result.scalars().all()
        for player in match_players:
                user = await db.get(User, player.user_id)
                if user:
                    user.score += player.score
                    user.token_balance += player.tokens_earned
                    await db.commit()
                    await db.refresh(user)
        # Cập nhật trạng thái lobby
        result = await db.execute(
        select(Lobby).where(Lobby.id == lobby_id)
         )
        lobby = result.scalar_one_or_none()
        if lobby:
         lobby.status = "finished"
         lobby.ended_at = datetime.utcnow()
         lobby.code = ''
        await db.commit()

    await game_broadcast(lobby_id, {"event": "end_game"})