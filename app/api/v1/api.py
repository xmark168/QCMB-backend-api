from app.api.v1.websockets import ws,ws2
from fastapi import APIRouter
from .endpoints import users,auth,question,topic,store,game,leaderboard, payment,lobby

router = APIRouter()
router.include_router(users.router) 
router.include_router(auth.router)  
router.include_router(topic.router)
router.include_router(question.router)
router.include_router(store.router)
router.include_router(payment.router)
router.include_router(leaderboard.router)
router.include_router(lobby.router)
router.include_router(game.router)
router.include_router(ws.router)
router.include_router(ws2.router)