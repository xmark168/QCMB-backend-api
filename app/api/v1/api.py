from fastapi import APIRouter

from app.api.v1.endpoints import leaderboard, payment
from .endpoints import users,auth,question,topic,store

router = APIRouter()
router.include_router(users.router) 
router.include_router(auth.router)  
router.include_router(topic.router)
router.include_router(question.router)
router.include_router(store.router)
router.include_router(payment.router)
router.include_router(leaderboard.router)