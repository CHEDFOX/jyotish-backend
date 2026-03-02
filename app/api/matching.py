from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, Kundli, Partner
from app.schemas.matching import PartnerCreate, PartnerResponse, MatchingResult
from app.services.astrology import generate_kundli, format_kundli_for_ai, calculate_matching
from app.services.ai_chat import get_matching_insights

router = APIRouter(prefix="/matching", tags=["Kundli Matching"])

@router.post("/partner", response_model=PartnerResponse)
def add_partner(
    data: PartnerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Generate partner's kundli
    date_parts = data.birth_date.split("-")
    time_parts = data.birth_time.split(":")
    
    partner_kundli = generate_kundli(
        name=data.name,
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
    
    # Create partner record
    partner = Partner(
        user_id=current_user.id,
        name=data.name,
        birth_date=data.birth_date,
        birth_time=data.birth_time,
        birth_place=data.birth_place,
        latitude=data.latitude,
        longitude=data.longitude,
        timezone_offset=data.timezone_offset,
        gender=data.gender,
        kundli_data=json.dumps(partner_kundli)
    )
    
    db.add(partner)
    db.commit()
    db.refresh(partner)
    
    return partner

@router.get("/partners", response_model=List[PartnerResponse])
def get_partners(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partners = db.query(Partner).filter(Partner.user_id == current_user.id).all()
    return partners

@router.post("/calculate/{partner_id}")
async def calculate_match(
    partner_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get user's kundli
    user_kundli_record = db.query(Kundli).filter(Kundli.user_id == current_user.id).first()
    if not user_kundli_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete your birth data first"
        )
    
    # Get partner
    partner = db.query(Partner).filter(
        Partner.id == partner_id,
        Partner.user_id == current_user.id
    ).first()
    
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found"
        )
    
    # Parse kundli data
    user_kundli = json.loads(user_kundli_record.kundli_data)
    partner_kundli = json.loads(partner.kundli_data)
    
    # Calculate matching
    match_result = calculate_matching(user_kundli, partner_kundli)
    
    # Get AI insights
    try:
        ai_insights = await get_matching_insights(
            matching_result=match_result,
            kundli1_formatted=user_kundli_record.formatted_for_ai,
            kundli2_formatted=format_kundli_for_ai(partner_kundli)
        )
        match_result["ai_insights"] = ai_insights
    except Exception as e:
        match_result["ai_insights"] = "Unable to generate detailed insights at this time."
    
    # Save result
    partner.matching_result = json.dumps(match_result)
    db.commit()
    
    return match_result

@router.get("/result/{partner_id}")
def get_match_result(
    partner_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = db.query(Partner).filter(
        Partner.id == partner_id,
        Partner.user_id == current_user.id
    ).first()
    
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found"
        )
    
    if not partner.matching_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matching not calculated yet"
        )
    
    return json.loads(partner.matching_result)
