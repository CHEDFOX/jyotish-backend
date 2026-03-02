from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, BirthData, Kundli
from app.schemas.user import UserResponse, BirthDataCreate, BirthDataResponse
from app.services.astrology import generate_kundli, format_kundli_for_ai

router = APIRouter(prefix="/user", tags=["User"])

@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/birth-data", response_model=BirthDataResponse)
def save_birth_data(
    data: BirthDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if birth data already exists
    existing = db.query(BirthData).filter(BirthData.user_id == current_user.id).first()
    
    if existing:
        # Update existing
        for key, value in data.model_dump().items():
            setattr(existing, key, value)
        birth_data = existing
    else:
        # Create new
        birth_data = BirthData(user_id=current_user.id, **data.model_dump())
        db.add(birth_data)
    
    db.commit()
    db.refresh(birth_data)
    
    # Generate Kundli
    date_parts = data.birth_date.split("-")
    time_parts = data.birth_time.split(":")
    
    kundli_data = generate_kundli(
        name=current_user.name,
        year=int(date_parts[0]),
        month=int(date_parts[1]),
        day=int(date_parts[2]),
        hour=int(time_parts[0]),
        minute=int(time_parts[1]),
        latitude=data.latitude,
        longitude=data.longitude,
        timezone=data.timezone_offset,
        gender=data.gender
    )
    
    formatted = format_kundli_for_ai(kundli_data)
    
    # Save Kundli
    existing_kundli = db.query(Kundli).filter(Kundli.user_id == current_user.id).first()
    
    if existing_kundli:
        existing_kundli.kundli_data = json.dumps(kundli_data)
        existing_kundli.formatted_for_ai = formatted
    else:
        kundli = Kundli(
            user_id=current_user.id,
            kundli_data=json.dumps(kundli_data),
            formatted_for_ai=formatted
        )
        db.add(kundli)
    
    db.commit()
    
    return birth_data

@router.get("/birth-data", response_model=BirthDataResponse)
def get_birth_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    birth_data = db.query(BirthData).filter(BirthData.user_id == current_user.id).first()
    
    if not birth_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Birth data not found. Please complete onboarding."
        )
    
    return birth_data

@router.get("/kundli")
def get_kundli(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    kundli = db.query(Kundli).filter(Kundli.user_id == current_user.id).first()
    
    if not kundli:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kundli not found. Please save birth data first."
        )
    
    return json.loads(kundli.kundli_data)
