from fastapi import APIRouter, Depends
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
async def list_users():
   return {"message": "List of users"}