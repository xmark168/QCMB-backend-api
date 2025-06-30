from app.core.enums import UserRole
from sqlalchemy import Column, BigInteger, DateTime, String, Text, Integer, Enum
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from .database import Base



class User(Base):
    __tablename__ = "users"

    id            = Column(BigInteger, primary_key=True, index=True)
    name          = Column(Text,  nullable=False)
    username      = Column(String(50),  unique=True, nullable=False, index=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password      = Column(Text,  nullable=False)         
    role          = Column(Enum(UserRole), nullable=False, default=UserRole.PLAYER)
    token_balance = Column(Integer, nullable=False, default=0)
    ranking_rate  = Column(Integer, nullable=False, default=0)
    created_at    = Column(DateTime(timezone=True),
                         server_default=func.now(),
                         onupdate=func.now())
    