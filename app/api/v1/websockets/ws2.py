# app/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List
from uuid import UUID
from .ws_game import manager_connect, manager_disconnect, broadcast, connections_game
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.v1.endpoints.auth import require_roles,get_current_user

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.models import   MatchPlayer, User,Lobby


router = APIRouter()

@router.websocket("/wsgame/{lobby_id}/{username}")
async def websocket_lobby (ws: WebSocket,
    lobby_id: UUID,
    username: str,       
    db: AsyncSession = Depends(get_db),
):
    await ws.accept()
    print(f"WebSocket connection established for lobby {lobby_id} with user {username}")
    await manager_connect(lobby_id, ws)
    try:
        while True:
            data = await ws.receive_json()
            data["user"] = username
            await broadcast(lobby_id, data)
    except WebSocketDisconnect:
        await manager_disconnect(lobby_id, ws)