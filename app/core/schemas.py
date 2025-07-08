from datetime import datetime
from typing import Annotated, Optional
from app.core.enums import UserRole
from pydantic import BaseModel, ConfigDict, EmailStr, Field
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
    avatar_url: Optional[str] = None
    role: str
    token_balance: int
    score: Optional[int] = 0
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginInput(BaseModel):
    username: str
    password: str


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead

class UserOut(BaseModel):
    id: int
    name: str
    username: str
    email: EmailStr
    role: str
    avatar_url: str
    token_balance: int
    score: int

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

# -------- Forgot password --------
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOtpInput(BaseModel):
    email: EmailStr
    otp: Annotated[str, Field(min_length=6, max_length=6)]
    otp_token: str

class ResetWithVerifiedToken(BaseModel):
    email: EmailStr
    verified_token: str
    new_password: str

class GenericMessage(BaseModel):
    detail: str

class ForgotPasswordResponse(GenericMessage):
    otp_token: Optional[str] = None


class VerifyOtpResponse(BaseModel):
    verified_token: str

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
    wrong_answer_1: Optional[str] = None
    wrong_answer_2: Optional[str] = None
    wrong_answer_3: Optional[str] = None

class QuestionCreate(QuestionBase):
    pass

class QuestionUpdate(BaseModel):
    content: Optional[str] = None
    difficulty: Optional[int] = None
    correct_answer: Optional[str] = None
    wrong_answer_1: Optional[str] = None
    wrong_answer_2: Optional[str] = None
    wrong_answer_3: Optional[str] = None

class QuestionOut(QuestionBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True

