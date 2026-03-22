from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx


FuelType = Literal["diesel", "benzin", "autogas", "strom"]


@dataclass
class FuelQuote:
    fuel_type: FuelType
    price_eur_per_unit: float
    station_name: str
    station_address: str | None
    distance_km: float | None
    source: str
    note: str | None = None


class EControlFuelProvider:
    """
    Real-time Austrian fuel source powered by E-Control public API.
    """

    BASE_URL = "https://api.e-control.at/sprit/1.0/search/gas-stations/by-address"
    FUEL_MAP = {
        "diesel": "DIE",
        "benzin": "SUP",
        "autogas": "GAS",
    }

    async def get_cheapest_quote(
        self,
        lat: float,
        lng: float,
        fuel_type: FuelType,
    ) -> FuelQuote:
        if fuel_type == "strom":
            raise ValueError(
                "E-Control Sprit API liefert keine Strom-Ladepreise. "
                "Bitte energy_price_eur_per_unit fuer strom direkt setzen."
            )

        mapped_fuel = self.FUEL_MAP[fuel_type]
        params = {
            "fuelType": mapped_fuel,
            "latitude": lat,
            "longitude": lng,
            "includeClosed": "false",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
        stations = response.json()

        if not stations:
            raise ValueError("Keine Tankstellenpreise von E-Control gefunden.")

        cheapest_station = min(
            stations,
            key=lambda station: min(
                (
                    float(price["amount"])
                    for price in station.get("prices", [])
                    if price.get("fuelType") == mapped_fuel
                    and price.get("amount") is not None
                ),
                default=float("inf"),
            ),
        )
        matching_prices = [
            float(price["amount"])
            for price in cheapest_station.get("prices", [])
            if price.get("fuelType") == mapped_fuel and price.get("amount") is not None
        ]
        if not matching_prices:
            raise ValueError("Keine passenden Preiswerte fuer gewaehlten Treibstoff gefunden.")

        location = cheapest_station.get("location", {}) or {}
        return FuelQuote(
            fuel_type=fuel_type,
            price_eur_per_unit=min(matching_prices),
            station_name=cheapest_station.get("name", "Unbekannt"),
            station_address=location.get("address"),
            distance_km=cheapest_station.get("distance"),
            source="api.e-control.at",
        )
