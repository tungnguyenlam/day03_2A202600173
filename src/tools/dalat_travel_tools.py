"""
Mock travel tools for Đà Lạt lab scenario (hotel + weather + reviews).
Data matches the instructor-style trace for reproducible demos.

Tool Spec Progression & Recommended Usage Flow:
1. `get_weather`: Query this to check the destination's weather (e.g., Da Lat) and date. 
It is recommended to call this before making clothing or activity suggestions.
2. `search_hotels`: Search for available accommodations by specifying city, check-in/out 
dates, and budget. This returns a list of hotels along with their respective `hotel_id`s.
3. `get_hotel_reviews`: After obtaining a `hotel_id` from `search_hotels`, use this tool 
to fetch specific reviews and ratings for that hotel to help the user make a final decision.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.tools.dalat_dummy_data_tool import get_tool_specs_dummy_data


def get_weather(city: str, date: str) -> str:
    c = city.lower()
    if "da lat" in c or "dalat" in c or "đà lạt" in city.lower():
        return (
            "Nhiệt độ 15-18°C, có mưa nhỏ chiều tối, độ ẩm 85%. "
            f"(Dữ liệu demo cho {city}, ngày {date}.)"
        )
    return f"Chưa có dữ liệu thời tiết demo cho {city} ({date})."


def search_hotels(city: str, check_in: str, check_out: str, max_price: int) -> str:
    c = city.lower()
    if "da lat" not in c and "dalat" not in c and "đà lạt" not in city.lower():
        return f"Không có inventory demo cho {city}."
    lines = [
        "[1] Ngọc Lan Hotel - 650000 VND/đêm - còn phòng (hotel_id: ngoc_lan_hotel)",
        "[2] Mimosa Boutique - 750000 VND/đêm - còn phòng (hotel_id: mimosa_boutique)",
        "[3] Sapa Lodge - 820000 VND/đêm - vượt ngân sách (hotel_id: sapa_lodge)",
        f"(check_in={check_in}, check_out={check_out}, max_price={max_price} VND)",
    ]
    return "\n".join(lines)


def get_hotel_reviews(hotel_id: str) -> str:
    hid = hotel_id.strip().lower().replace(" ", "_")
    if hid in ("ngoc_lan_hotel", "ngoc_lan", "1"):
        return (
            "Rating 4.5/5 - 320 đánh giá - Gần chợ Đà Lạt - "
            "Điểm nổi bật: sạch sẽ, view đẹp, có bãi đỗ xe."
        )
    if hid in ("mimosa_boutique", "mimosa", "2"):
        return "Rating 4.2/5 - 180 đánh giá - Yên tĩnh, decor boutique, bữa sáng ổn."
    if hid in ("sapa_lodge", "sapa", "3"):
        return "Rating 4.0/5 - 95 đánh giá - Note: listing name gây nhầm; giá thường >800k."
    return f"Không có review demo cho hotel_id={hotel_id}."


def get_tool_specs_dalat() -> List[Dict[str, Any]]:
    return [
        {
            "name": "get_weather",
            "description": (
                "Lấy dự báo thời tiết (demo). Tham số: city (tên thành phố, ví dụ 'Da Lat'), "
                "date (YYYY-MM-DD). Dùng trước khi gợi ý trang phục."
            ),
            "uses_kwargs": True,
            "run": get_weather,
        },
        {
            "name": "search_hotels",
            "description": (
                "Tìm phòng khách sạn (demo). Tham số: city, check_in (YYYY-MM-DD), "
                "check_out (YYYY-MM-DD), max_price (số VND/ngày, integer). "
                "Trả về danh sách có hotel_id để gọi get_hotel_reviews."
            ),
            "uses_kwargs": True,
            "run": search_hotels,
        },
        {
            "name": "get_hotel_reviews",
            "description": (
                "Lấy đánh giá tóm tắt (demo). Tham số: hotel_id (string, ví dụ 'ngoc_lan_hotel')."
            ),
            "uses_kwargs": True,
            "run": get_hotel_reviews,
        },
    ] + get_tool_specs_dummy_data()
