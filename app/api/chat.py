from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, Kundli, ChatMessage
from app.schemas.chat import ChatMessageCreate, ChatMessageResponse, ChatResponse
from app.services.ai_chat import get_ai_response

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get user's kundli
    kundli = db.query(Kundli).filter(Kundli.user_id == current_user.id).first()
    
    if not kundli:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete your birth data first"
        )
    
    # Get chat history
    history = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()
    
    history_list = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(history)
    ]
    
    # Save user message
    user_msg = ChatMessage(
        user_id=current_user.id,
        role="user",
        content=message.content,
        is_voice=message.is_voice
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    
    # Get AI response
    try:
        ai_response = await get_ai_response(
            user_message=message.content,
            kundli_formatted=kundli.formatted_for_ai,
            chat_history=history_list
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}"
        )
    
    # Save assistant message
    assistant_msg = ChatMessage(
        user_id=current_user.id,
        role="assistant",
        content=ai_response,
        is_voice=False
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    
    return ChatResponse(
        user_message=user_msg,
        assistant_message=assistant_msg
    )

@router.get("/history", response_model=List[ChatMessageResponse])
def get_chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id
    ).order_by(ChatMessage.created_at.asc()).limit(limit).all()
    
    return messages

@router.delete("/history")
def clear_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Chat history cleared"}
