from enum import Enum

class UserRole(Enum):
    PLAYER = "PLAYER"
    ADMIN  = "ADMIN"

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
