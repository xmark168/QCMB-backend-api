from pydantic import BaseModel, EmailStr

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