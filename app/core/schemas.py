from datetime import datetime
from typing import Annotated, Optional
from app.core.enums import UserRole
from app.core.models import User
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

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None

class AvatarUpdateRequest(BaseModel):
    avatar_url: str = Field(..., max_length=500)

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=3, max_length=100)

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

# -------- Card --------
class CardRead(BaseModel):
    id: UUID
    type: str
    question_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True

# -------- Inventory --------
class InventoryRead(BaseModel):
    id: UUID
    user_id: int
    card_id: UUID
    quantity: int
    created_at: datetime

    card: Optional[CardRead] = None

    class Config:
        orm_mode = True

# -------- Purchase (hardcode store items) --------
class PurchaseRequest(BaseModel):
    item_id: int  # Hardcode ID (1=Skip Turn, 2=Reverse...)
    quantity: int = 1

class PurchaseItemData(BaseModel):
    item: dict  # Hardcode item info
    new_balance: int
    inventory_quantity: int

class PurchaseResponse(BaseModel):
    data: PurchaseItemData

# Hardcode store items
STORE_ITEMS = {
    1: {"name": "Skip Turn", "price": 50, "description": "Bỏ lượt của đối thủ hiện tại", "effect_type": "SKIP_TURN"},
    2: {"name": "Reverse", "price": 60, "description": "Đảo ngược thứ tự lượt chơi", "effect_type": "REVERSE_ORDER"},
    3: {"name": "Double Score", "price": 80, "description": "Nhân đôi điểm số của lượt hiện tại", "effect_type": "DOUBLE_SCORE"},
    4: {"name": "Extra Time", "price": 40, "description": "Thêm thời gian trả lời câu hỏi", "effect_type": "EXTRA_TIME"},
}