from datetime import datetime, timedelta
import hashlib
import secrets
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from typing import Optional

SECRET_KEY = "CHANGE_ME_LONG_RANDOM"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",         
    bearerFormat="JWT"                
)
# =========================
# Khởi tạo Bcrypt (OWASP khuyên dùng)
# =========================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Băm mật khẩu bằng bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """So khớp mật khẩu."""
    return pwd_context.verify(plain, hashed)

# =========================
# Access-Token cho đăng nhập
# =========================
def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """
    Tạo JWT cho đăng nhập.
    - `data`: payload (VD: {"sub": user.id, "role": user.role})
    - `expires_delta`: số phút sống; mặc định = ACCESS_TOKEN_EXPIRE_MINUTES
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Giải mã access-token; trả None nếu lỗi / hết hạn."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    
# =============================================================
# ======  OTP  –  Quên mật khẩu (stateless, không cần DB) ======
# =============================================================
OTP_LEN         = 6   # 6 số
OTP_TTL_MIN     = 10  # OTP & otp_token sống 10 phút
VERIFIED_TTL_MIN = 5  # verified_token sống 5 phút

# ---------- Sinh & băm OTP ----------
def generate_raw_otp() -> str:
    """Tạo OTP 6 chữ số ngẫu nhiên (CSPRNG)."""
    return f"{secrets.randbelow(10**OTP_LEN):0{OTP_LEN}}"

def hash_otp(otp: str) -> str:
    """Băm OTP bằng SHA-256 (đủ cho chuỗi ngắn)."""
    return hashlib.sha256(otp.encode()).hexdigest()

# ---------- JWT cho OTP ----------
def _build_jwt(payload: dict, minutes: int) -> str:
    """Hàm giúp tạo JWT ngắn hạn."""
    payload = payload.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=minutes)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_otp_token(user_id: int, otp_hash: str) -> str:
    """
    Tạo otp_token mang:
      - sub   : user_id
      - scope : password_reset_otp
      - otp_hash : SHA-256 của OTP
    Sống trong OTP_TTL_MIN phút.
    """
    return _build_jwt(
        {
            "sub": str(user_id),
            "scope": "password_reset_otp",
            "otp_hash": otp_hash,
        },
        minutes=OTP_TTL_MIN,
    )

def create_verified_token(user_id: int) -> str:
    """
    Sau khi OTP hợp lệ, tạo verified_token:
      - scope : otp_verified
    Sống trong VERIFIED_TTL_MIN phút.
    """
    return _build_jwt(
        {
            "sub": str(user_id),
            "scope": "otp_verified",
        },
        minutes=VERIFIED_TTL_MIN,
    )

# ---------- Giải mã & kiểm tra token ----------
def decode_token(token: str) -> dict:
    """
    Giải mã otp_token hoặc verified_token.
    Ném ValueError nếu token hết hạn / không hợp lệ.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Token không hợp lệ hoặc đã hết hạn") from exc