from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.user import User, BirthData, Kundli, ChatMessage
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

router = APIRouter(prefix="/admin", tags=["Admin"])

# Simple admin key - change this to something secure
ADMIN_KEY = "jyotish_admin_secret_2024"

def verify_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key"
        )
    return True

# Response models
class UserListItem(BaseModel):
    id: UUID
    email: str
    name: str
    phone: Optional[str]
    is_premium: bool
    created_at: datetime
    has_birth_data: bool
    message_count: int

    class Config:
        from_attributes = True

class ChatMessageItem(BaseModel):
    id: UUID
    role: str
    content: str
    is_voice: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserDetailResponse(BaseModel):
    user: dict
    birth_data: Optional[dict]
    kundli_summary: Optional[str]
    messages: List[ChatMessageItem]

class StatsResponse(BaseModel):
    total_users: int
    users_with_birth_data: int
    total_messages: int
    premium_users: int

# Endpoints
@router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    admin: bool = Depends(verify_admin)
):
    total_users = db.query(User).count()
    users_with_birth_data = db.query(BirthData).count()
    total_messages = db.query(ChatMessage).count()
    premium_users = db.query(User).filter(User.is_premium == True).count()
    
    return {
        "total_users": total_users,
        "users_with_birth_data": users_with_birth_data,
        "total_messages": total_messages,
        "premium_users": premium_users
    }

@router.get("/users", response_model=List[UserListItem])
def get_all_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: bool = Depends(verify_admin)
):
    users = db.query(User).offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        has_birth = db.query(BirthData).filter(BirthData.user_id == user.id).first() is not None
        msg_count = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).count()
        
        result.append({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "phone": user.phone,
            "is_premium": user.is_premium,
            "created_at": user.created_at,
            "has_birth_data": has_birth,
            "message_count": msg_count
        })
    
    return result

@router.get("/users/{user_id}")
def get_user_detail(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: bool = Depends(verify_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    birth_data = db.query(BirthData).filter(BirthData.user_id == user_id).first()
    kundli = db.query(Kundli).filter(Kundli.user_id == user_id).first()
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == user_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "phone": user.phone,
            "is_premium": user.is_premium,
            "created_at": user.created_at.isoformat()
        },
        "birth_data": {
            "birth_date": birth_data.birth_date,
            "birth_time": birth_data.birth_time,
            "birth_place": birth_data.birth_place,
            "gender": birth_data.gender
        } if birth_data else None,
        "kundli_summary": kundli.formatted_for_ai if kundli else None,
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "is_voice": msg.is_voice,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }

@router.get("/chats")
def get_all_chats(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: bool = Depends(verify_admin)
):
    messages = db.query(ChatMessage).order_by(
        ChatMessage.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    result = []
    for msg in messages:
        user = db.query(User).filter(User.id == msg.user_id).first()
        result.append({
            "id": str(msg.id),
            "user_id": str(msg.user_id),
            "user_name": user.name if user else "Unknown",
            "user_email": user.email if user else "Unknown",
            "role": msg.role,
            "content": msg.content,
            "is_voice": msg.is_voice,
            "created_at": msg.created_at.isoformat()
        })
    
    return result

@router.delete("/users/{user_id}")
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: bool = Depends(verify_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete related data
    db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    db.query(Kundli).filter(Kundli.user_id == user_id).delete()
    db.query(BirthData).filter(BirthData.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    
    db.commit()
    
    return {"message": "User deleted successfully"}

@router.put("/users/{user_id}/premium")
def toggle_premium(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: bool = Depends(verify_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_premium = not user.is_premium
    db.commit()
    
    return {"message": f"User premium status: {user.is_premium}"}
