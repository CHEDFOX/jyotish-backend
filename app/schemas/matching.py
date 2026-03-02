from pydantic import BaseModel
from typing import Optional, Dict
from uuid import UUID

class PartnerCreate(BaseModel):
    name: str
    birth_date: str
    birth_time: str
    birth_place: str
    latitude: float
    longitude: float
    timezone_offset: float = 5.5
    gender: Optional[str] = None

class PartnerResponse(BaseModel):
    id: UUID
    name: str
    birth_date: str
    birth_time: str
    birth_place: str
    
    class Config:
        from_attributes = True

class MatchingResult(BaseModel):
    person1: str
    person2: str
    scores: Dict[str, float]
    total: float
    max: int
    percentage: float
    verdict: str
