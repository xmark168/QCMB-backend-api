from datetime import datetime
import uuid
from app.core.enums import UserRole, PaymentStatus
from sqlalchemy import Column, BigInteger, ForeignKey, DateTime, String, Text, Integer, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from sqlalchemy.dialects.postgresql import UUID

from .database import Base

def default_uuid() -> uuid.UUID:
    """Trả về UUID4 mỗi lần insert (tránh cố định giá trị)"""
    return uuid.uuid4()

class User(Base):
    __tablename__ = "users"

    id            = Column(BigInteger, primary_key=True, index=True)
    name          = Column(Text,  nullable=False)
    username      = Column(String(50),  unique=True, nullable=False, index=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password      = Column(Text,  nullable=False)         
    role          = Column(Enum(UserRole), nullable=False, default=UserRole.PLAYER)
    avatar_url    = Column(Text, nullable=True, default=None)
    token_balance = Column(Integer, nullable=False, default=0)
    score         = Column(BigInteger, nullable=True, default=0)
    created_at    = Column(DateTime(timezone=True),
                         server_default=func.now(),
                         onupdate=func.now())
    
    inventory     = relationship("Inventory", back_populates="user", cascade="all, delete")
    payments      = relationship("Payment", back_populates="user", cascade="all, delete")

class Topic(Base):
    __tablename__ = "topics"

    id            = Column(UUID(as_uuid=True), primary_key=True,
                        default=default_uuid, index=True, unique=True)
    name          = Column(String(100), unique=True, nullable=False)
    description   = Column(Text)
    created_at    = Column(DateTime, default=datetime.utcnow)
    questions     = relationship(
        "Question",
        back_populates="topic",
        cascade="all, delete",
    )


class Question(Base):
    __tablename__ = "questions"

    id              = Column(UUID(as_uuid=True), primary_key=True,
                           default=default_uuid, index=True, unique=True)
    topic_id        = Column(UUID(as_uuid=True), 
                           ForeignKey("topics.id", ondelete="CASCADE"),
                           nullable=False)
    content         = Column(Text, nullable=False)
    difficulty      = Column(Integer, default=1)
    correct_answer  = Column(Text, nullable=False)
    wrong_answer_1  = Column(Text)
    wrong_answer_2  = Column(Text)
    wrong_answer_3  = Column(Text)
    created_at      = Column(DateTime, default=datetime.utcnow)

    topic           = relationship("Topic", back_populates="questions")

class Card(Base):
    __tablename__ = "cards"

    id          = Column(UUID(as_uuid=True), primary_key=True,
                        default=default_uuid, index=True, unique=True)
    type        = Column(String(50), nullable=True)
    question_id = Column(UUID(as_uuid=True),
                        ForeignKey("questions.id", ondelete="CASCADE"),
                        nullable=True)
    title       = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    question = relationship(
        "Question",
        cascade="all, delete",
    )

class Inventory(Base):
    __tablename__  = "inventories"

    id             = Column(UUID(as_uuid=True), primary_key=True,
                        default=default_uuid, index=True, unique=True)
    user_id        = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    card_id        = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=True)
    quantity       = Column(Integer, nullable=True, default=0)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    user           = relationship("User", back_populates="inventory")
    card           = relationship("Card")

class Payment(Base):
    """Model để lưu trữ thông tin payment PayOS"""
    __tablename__ = "payments"

    id                = Column(UUID(as_uuid=True), primary_key=True,
                             default=default_uuid, index=True, unique=True)
    user_id           = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_code        = Column(BigInteger, unique=True, nullable=False, index=True)
    payos_payment_id  = Column(String(255), nullable=True, index=True)  # PayOS payment link ID
    package_id        = Column(Integer, nullable=False)  # 1001, 1002, 1003
    package_name      = Column(String(100), nullable=False)  # Tên gói
    amount            = Column(Integer, nullable=False)  # Số tiền VND
    tokens            = Column(Integer, nullable=False)  # Số token nhận được
    status            = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    checkout_url      = Column(Text, nullable=True)  # PayOS checkout URL
    description       = Column(Text, nullable=True)
    
    # Thông tin PayOS callback
    payos_reference   = Column(String(255), nullable=True)  # PayOS transaction reference
    payos_account_number = Column(String(50), nullable=True)
    transaction_datetime = Column(DateTime, nullable=True)  # Thời gian thanh toán thực tế
    
    # Timestamps
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at        = Column(DateTime, nullable=True)  # Thời gian hết hạn payment
    paid_at           = Column(DateTime, nullable=True)  # Thời gian thanh toán thành công

    # Relationship
    user              = relationship("User", back_populates="payments") 

    
class Lobby(Base):
    __tablename__ = "lobbies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid, index=True, unique=True)
    name = Column(String(100), nullable=False) 
    code = Column(String(20), unique=True, nullable=False)
    host_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"))
    status = Column(String(50), default="waiting") # waiting, in_progress, completed 
    max_items_per_player = Column(Integer, default=5)
    initial_hand_size = Column(Integer, default=3)
    match_time_sec = Column(Integer, default=300)
    player_count_limit = Column(Integer, default=0) # ✅ Thêm số người chơi
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    topic = relationship("Topic")
    player_count = Column(Integer, default=1) 
    host_user = relationship("User", foreign_keys=[host_user_id])
 
class MatchPlayer(Base):
    __tablename__ = "match_players"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    match_id = Column(UUID(as_uuid=True), ForeignKey("lobbies.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    score = Column(Integer, default=0)
    cards_left = Column(Integer, default=0)
    tokens_earned = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    match = relationship("Lobby", back_populates="players")
    user = relationship("User", back_populates="matches")