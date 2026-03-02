from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

# Auth
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    phone: Optional[str]
    is_premium: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Birth Data
class BirthDataCreate(BaseModel):
    birth_date: str      # YYYY-MM-DD
    birth_time: str      # HH:MM
    birth_place: str
    latitude: float
    longitude: float
    timezone_offset: float = 5.5
    gender: Optional[str] = None

class BirthDataResponse(BaseModel):
    id: UUID
    birth_date: str
    birth_time: str
    birth_place: str
    latitude: float
    longitude: float
    timezone_offset: float
    gender: Optional[str]
    
    class Config:
        from_attributes = True
