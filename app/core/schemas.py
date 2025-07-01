from datetime import datetime
from typing import Optional
from app.core.enums import UserRole
from pydantic import BaseModel, ConfigDict, EmailStr
from enum import Enum
from uuid import UUID

# -------- User --------
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

# -------- Topic --------
class TopicBase(BaseModel):
    name: str
    description: Optional[str] = None

class TopicCreate(TopicBase):
    pass

class TopicUpdate(TopicBase):
    pass

class TopicOut(TopicBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# -------- Question --------
class QuestionBase(BaseModel):
    topic_id: UUID
    content: str
    difficulty: int
    correct_answer: str
    Wrong_answer_1: Optional[str] = None
    Wrong_answer_2: Optional[str] = None
    Wrong_answer_3: Optional[str] = None

class QuestionCreate(QuestionBase):
    pass

class QuestionUpdate(BaseModel):
    content: Optional[str] = None
    difficulty: Optional[int] = None
    correct_answer: Optional[str] = None
    Wrong_answer_1: Optional[str] = None
    Wrong_answer_2: Optional[str] = None
    Wrong_answer_3: Optional[str] = None

class QuestionOut(QuestionBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True

