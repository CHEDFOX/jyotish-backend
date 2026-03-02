import httpx
from typing import List, Dict, Optional
from app.core.config import settings

async def autocomplete_place(query: str) -> List[Dict]:
    """
    Get place suggestions from Google Places API
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://maps.googleapis.com/maps/api/place/autocomplete/json",
            params={
                "input": query,
                "types": "(cities)",
                "key": settings.GOOGLE_PLACES_API_KEY
            }
        )
        
        data = response.json()
        
        if data.get("status") != "OK":
            return []
        
        return [
            {
                "place_id": p["place_id"],
                "description": p["description"]
            }
            for p in data.get("predictions", [])
        ]


async def get_place_details(place_id: str) -> Optional[Dict]:
    """
    Get latitude/longitude for a place
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={
                "place_id": place_id,
                "fields": "geometry,formatted_address,utc_offset",
                "key": settings.GOOGLE_PLACES_API_KEY
            }
        )
        
        data = response.json()
        
        if data.get("status") != "OK":
            return None
        
        result = data.get("result", {})
        location = result.get("geometry", {}).get("location", {})
        
        # Calculate timezone offset in hours
        utc_offset_minutes = result.get("utc_offset", 330)  # Default IST
        timezone_offset = utc_offset_minutes / 60
        
        return {
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "address": result.get("formatted_address"),
            "timezone_offset": timezone_offset
        }
