from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List

connections_game: Dict[str, List[WebSocket]] = {}

async def manager_connect(lobby_id: UUID, ws: WebSocket):
    connections_game.setdefault(lobby_id, []).append(ws)
    
async def manager_disconnect(lobby_id: UUID, ws: WebSocket):
    connections_game[lobby_id].remove(ws)

async def broadcast(lobby_id: str, message: dict):
    for ws in connections_game.get(lobby_id, []):
        await ws.send_json(message)
        