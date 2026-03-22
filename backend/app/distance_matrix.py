from __future__ import annotations

import httpx

from .schemas import Location


async def get_distance_km_google(
    origin: Location,
    destination: Location,
    api_key: str,
) -> float:
    params = {
        "origins": f"{origin.lat},{origin.lng}",
        "destinations": f"{destination.lat},{destination.lng}",
        "key": api_key,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            params=params,
        )
        response.raise_for_status()

    payload = response.json()
    element = payload["rows"][0]["elements"][0]
    meters = element["distance"]["value"]
    return meters / 1000.0
