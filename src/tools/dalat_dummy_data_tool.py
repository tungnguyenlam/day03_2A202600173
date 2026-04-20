"""
Deterministic dummy data for the Đà Lạt travel agent.

This tool is meant for demos, tests, and prompt evaluation when we want the
agent to reason over realistic-but-fake hotel and weather data without hitting
external services.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


_DUMMY_DATA: Dict[str, Any] = {
    "city": "Da Lat",
    "date": "2026-04-12",
    "weather": {
        "summary": "Light rain in the afternoon, cool and humid",
        "temp_c": {"low": 15, "high": 19},
        "humidity_pct": 84,
        "wind_kph": 11,
        "clothing_tip": "Bring a light jacket and closed shoes.",
    },
    "hotels": [
        {
            "hotel_id": "ngoc_lan_hotel",
            "name": "Ngọc Lan Hotel",
            "area": "Near Da Lat Market",
            "price_vnd_per_night": 650000,
            "rating": 4.5,
            "reviews": 320,
            "availability": "available",
            "highlights": ["clean rooms", "good view", "parking"],
        },
        {
            "hotel_id": "mimosa_boutique",
            "name": "Mimosa Boutique",
            "area": "Central hillside",
            "price_vnd_per_night": 750000,
            "rating": 4.2,
            "reviews": 180,
            "availability": "available",
            "highlights": ["quiet", "boutique decor", "good breakfast"],
        },
        {
            "hotel_id": "green_valley_inn",
            "name": "Green Valley Inn",
            "area": "Xuan Huong Lake",
            "price_vnd_per_night": 790000,
            "rating": 4.1,
            "reviews": 96,
            "availability": "limited",
            "highlights": ["lake access", "family-friendly", "fast wifi"],
        },
        {
            "hotel_id": "pine_hill_resort",
            "name": "Pine Hill Resort",
            "area": "Outskirts",
            "price_vnd_per_night": 980000,
            "rating": 4.7,
            "reviews": 240,
            "availability": "available",
            "highlights": ["forest view", "spa", "breakfast included"],
        },
    ],
}


def _matches_city(city: str) -> bool:
    normalized = city.lower().strip()
    return normalized in ("da lat", "dalat", "đà lạt", "đà lạt") or "da lat" in normalized


def get_dummy_travel_data(city: str, date: str, max_price: Optional[int] = None) -> str:
    """Return a realistic mock snapshot of travel data for the requested city."""
    if not _matches_city(city):
        payload = {
            "city": city,
            "date": date,
            "error": f"No dummy dataset prepared for {city}.",
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    hotels: List[Dict[str, Any]] = []
    for hotel in _DUMMY_DATA["hotels"]:
        if max_price is not None and int(hotel["price_vnd_per_night"]) > int(max_price):
            continue
        hotels.append(hotel)

    payload = {
        "city": _DUMMY_DATA["city"],
        "date": date,
        "weather": _DUMMY_DATA["weather"],
        "hotels": hotels,
        "note": (
            "This is dummy data for agent evaluation. Prices, ratings, and availability are simulated."
        ),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def get_tool_specs_dummy_data() -> List[Dict[str, Any]]:
    return [
        {
            "name": "get_dummy_travel_data",
            "description": (
                "Return a realistic dummy data snapshot for Da Lat travel planning. "
                "Args: city (string), date (YYYY-MM-DD), max_price (optional integer VND). "
                "Use this when you need mock weather plus hotel inventory in one call."
            ),
            "uses_kwargs": True,
            "run": get_dummy_travel_data,
        }
    ]
