from typing import Optional
from app.core.enums import UserRole
from pydantic import BaseModel, ConfigDict, EmailStr
from enum import Enum

class UserCreate(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    name: str
    username: str
    email: EmailStr
    role: str
    token_balance: int
    ranking_rate: int
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginInput(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    username: str
    email: EmailStr
    role: str
    token_balance: int
    ranking_rate: int

    model_config = ConfigDict(from_attributes=True)

class UserCreateAdmin(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.PLAYER
    token_balance: int = 0

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    token_balance: Optional[int] = None
    ranking_rate: Optional[int] = None

