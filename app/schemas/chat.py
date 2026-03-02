from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ChatMessageCreate(BaseModel):
    content: str
    is_voice: bool = False

class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    is_voice: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
