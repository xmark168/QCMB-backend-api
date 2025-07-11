from datetime import datetime
import uuid
from app.core.enums import UserRole
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

class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id            = Column(UUID(as_uuid=True), primary_key=True,
                           default=default_uuid, index=True, unique=True)
    user_id       = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    order_code    = Column(BigInteger, nullable=False)
    plan_id       = Column(String)
    amount        = Column(Integer, nullable=False)
    status        = Column(String, nullable=False, default="PENDING")
    token_amount  = Column(Integer, nullable=False, default=0)
    payment_url   = Column(Text)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())
    expired_at    = Column(DateTime(timezone=True))
    payment_link_id = Column(Text)
    transaction_id = Column(Text)

    user          = relationship("User")

    
class Lobby(Base):
 __tablename__ = "lobbies"

 id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid, index=True, unique=True)
 name = Column(String(100), nullable=False) 
 code = Column(String(20), unique=True, nullable=False)
 host_user_id = Column(UUID(as_uuid=True), nullable=False)
 topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"))
 status = Column(String(50), default="waiting") # waiting, in_progress, completed 
 max_items_per_player = Column(Integer, default=5)
 initial_hand_size = Column(Integer, default=3)
 match_time_sec = Column(Integer, default=300)
 player_count_limit = Column(Integer, default=0) # ✅ Thêm số người chơi
 started_at = Column(DateTime, nullable=True)
 ended_at = Column(DateTime, nullable=True)
 created_at = Column(DateTime, default=datetime.utcnow)