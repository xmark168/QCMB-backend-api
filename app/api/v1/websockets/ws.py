# app/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List
from uuid import UUID
from .ws_lobby import manager_connect, manager_disconnect, broadcast, connections
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.v1.endpoints.auth import require_roles,get_current_user

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.models import   MatchPlayer, User,Lobby


router = APIRouter()

@router.websocket("/ws/{lobby_id}/{username}")
async def websocket_lobby (ws: WebSocket,
    lobby_id: UUID,
    username: str,       
    db: AsyncSession = Depends(get_db),
):
    await ws.accept()
    result = await db.execute(select(Lobby).where(
    Lobby.status != "finished",
    Lobby.id == lobby_id
))      
    lobby = result.scalar_one_or_none()

    if lobby is None:
        await ws.close(code=1008)
        return
    await manager_connect(lobby_id, ws)

    # Broadcast to all
    await broadcast(lobby_id, {"event": "join", "user": username})
    try:
        while True:
            data = await ws.receive_json()
            data["user"] = username
            await broadcast(lobby_id, data)
    except WebSocketDisconnect:
        await manager_disconnect(lobby_id, ws)
        matchp = await db.execute(select(MatchPlayer).where(MatchPlayer.status == "waiting" 
                                                        , MatchPlayer.match_id == lobby_id
                                                        , MatchPlayer.user.has(User.username == username)))
        player_slot = matchp.scalar_one_or_none()
        if player_slot :
            ps = player_slot.user_id

            await db.delete(player_slot)
            await db.commit()
            result = await db.execute(select(Lobby).where(Lobby.id == lobby_id))       
            lobby = result.scalar_one_or_none()
            lobby.player_count = lobby.player_count - 1
            print(lobby.player_count)
            if lobby.player_count == 0:
                lobby.status = "finished"
                lobby.code = ''
            elif ps == lobby.host_user_id:
                newm = await db.execute(select(MatchPlayer).where(MatchPlayer.status != "left" 
                                                        , MatchPlayer.match_id == lobby_id))
                new_player = newm.scalar_one_or_none()
                lobby.host_user_id = new_player.user_id
            await db.commit()
            await db.refresh(lobby)
        await broadcast(lobby_id, {"event": "leave", "user": username})
        
        
