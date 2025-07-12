from datetime import datetime
from typing import Annotated, List, Optional
from app.core.enums import UserRole, PaymentStatus
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
        from_attributes = True

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
    avatar_url: Optional[str] = None
    token_balance: int
    score: Optional[int] = 0

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
    created_at: Optional[datetime]
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
        from_attributes = True

# -------- Card --------
class CardRead(BaseModel):
    id: UUID
    type: str
    question_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# -------- Inventory --------
class InventoryRead(BaseModel):
    id: UUID
    user_id: int
    card_id: UUID
    quantity: int
    created_at: datetime

    card: Optional[CardRead] = None

    class Config:
        from_attributes = True

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
    -1: {"name": "Items", "price": 0, "description": "", "effect_type": "HEADER_ITEMS"},

    1: {"name": "Skip Turn", "price": 50, "description": "Bỏ lượt của đối thủ hiện tại", "effect_type": "SKIP_TURN"},
    2: {"name": "Reverse", "price": 60, "description": "Đảo ngược thứ tự lượt chơi", "effect_type": "REVERSE_ORDER"},
    3: {"name": "Double Score", "price": 80, "description": "Nhân đôi điểm số của lượt hiện tại", "effect_type": "DOUBLE_SCORE"},
    4: {"name": "Extra Time", "price": 40, "description": "Thêm thời gian trả lời câu hỏi", "effect_type": "EXTRA_TIME"},

    -2: {"name": "Gói Nạp Token", "price": 0, "description": "", "effect_type": "HEADER_PACKAGES"},
    
    1001: {"name": "Gói 1,000 Token", "price": 100_000, "description": "Nạp 1.000 token", "effect_type": "TOKEN_PACKAGE_1000"},
    1002: {"name": "Gói 5,000 Token", "price": 450_000, "description": "Nạp 5.000 token", "effect_type": "TOKEN_PACKAGE_5000"},
    1003: {"name": "Gói 10,000 Token", "price": 800_000, "description": "Nạp 10.000 token", "effect_type": "TOKEN_PACKAGE_10000"},
}
class LobbyCreate(BaseModel):
    name: str
    topic_id: UUID
    max_items_per_player: Optional[int] = 5
    initial_hand_size: Optional[int] = 3
    match_time_sec: Optional[int] = 300
    player_count_limit: Optional[int] = 2

# -------- PayOS Payment Schemas --------
class TokenPackageType(str, Enum):
    PACKAGE_1000 = "TOKEN_PACKAGE_1000"
    PACKAGE_5000 = "TOKEN_PACKAGE_5000" 
    PACKAGE_10000 = "TOKEN_PACKAGE_10000"

class PayOSItemData(BaseModel):
    """Item data cho PayOS payment"""
    name: str
    quantity: int
    price: int

class CreatePaymentRequest(BaseModel):
    """Request để tạo payment với PayOS"""
    package_id: int = Field(..., description="ID của gói token (1001, 1002, 1003)")

    class Config:
        json_schema_extra = {
            "example": {
                "package_id": 1001
            }
        }

class PayOSPaymentData(BaseModel):
    """PayOS payment data structure"""
    orderCode: int
    amount: int
    description: str
    cancelUrl: str
    returnUrl: str
    items: List[PayOSItemData]

class CreatePaymentResponse(BaseModel):
    """Response khi tạo payment thành công"""
    payment_id: str
    order_code: int
    checkout_url: str
    package_info: dict
    amount: int
    status: str

class PaymentWebhookData(BaseModel):
    """Webhook data từ PayOS"""
    orderCode: int
    amount: int
    description: str
    accountNumber: Optional[str] = None
    reference: Optional[str] = None
    transactionDateTime: Optional[str] = None
    currency: str = "VND"
    paymentLinkId: str
    code: str = "00"
    desc: str = "success"
    counterAccountBankId: Optional[str] = None
    counterAccountBankName: Optional[str] = None
    counterAccountName: Optional[str] = None
    counterAccountNumber: Optional[str] = None
    virtualAccountName: Optional[str] = None
    virtualAccountNumber: Optional[str] = None

class PaymentStatusResponse(BaseModel):
    """Response cho việc check payment status"""
    payment_id: str
    order_code: int
    status: PaymentStatus
    amount: int
    description: str
    created_at: datetime
    paid_at: Optional[datetime] = None

class TokenPurchaseResponse(BaseModel):
    """Response khi mua token thành công"""
    message: str
    package_info: dict
    tokens_added: int
    new_balance: int
    payment_id: str

# Token packages data
TOKEN_PACKAGES = {
    1001: {
        "name": "Gói 1,000 Token",
        "price": 100_000,  # 100,000 VND
        "tokens": 1_000,
        "description": "Nạp 1.000 token vào tài khoản",
        "type": "TOKEN_PACKAGE_1000"
    },
    1002: {
        "name": "Gói 5,000 Token", 
        "price": 450_000,  # 450,000 VND (giảm 10%)
        "tokens": 5_000,
        "description": "Nạp 5.000 token vào tài khoản",
        "type": "TOKEN_PACKAGE_5000"
    },
    1003: {
        "name": "Gói 10,000 Token",
        "price": 800_000,  # 800,000 VND (giảm 20%)
        "tokens": 10_000,
        "description": "Nạp 10.000 token vào tài khoản", 
        "type": "TOKEN_PACKAGE_10000"
    }
} 


# -------- Leaderboard --------
class LeaderboardEntry(BaseModel):
    user: UserOut
    total_score: int
    rank: int

    class Config:
        from_attributes = True

class LeaderboardResponse(BaseModel):
    data: List[LeaderboardEntry]
    your_rank: Optional[int] = None

    class Config:
        from_attributes = True