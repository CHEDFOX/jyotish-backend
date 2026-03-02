from fastapi import APIRouter, HTTPException
from app.services.places import autocomplete_place, get_place_details

router = APIRouter(prefix="/places", tags=["Places"])

@router.get("/autocomplete")
async def search_places(query: str):
    if len(query) < 2:
        return []
    
    results = await autocomplete_place(query)
    return results

@router.get("/details/{place_id}")
async def place_details(place_id: str):
    details = await get_place_details(place_id)
    
    if not details:
        raise HTTPException(
            status_code=404,
            detail="Place not found"
        )
    
    return details
