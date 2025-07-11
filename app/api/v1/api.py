from fastapi import APIRouter
from .endpoints import users,auth,question,topic,store

router = APIRouter()
router.include_router(users.router) 
router.include_router(auth.router)  
router.include_router(topic.router)
router.include_router(question.router)
router.include_router(store.router)