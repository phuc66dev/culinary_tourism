"""
MapsService — Quản lý manifest bản đồ ngoại tuyến PMTiles (Quận 4) và kiểm tra Path Guard.
Phụ trách: Bảo (Task 1.10) & Vũ (Task 3.11)
"""

import asyncio
import json
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import settings
from app.modules.admin.schemas import POILocation


def _fetch_json(url: str, params: dict) -> dict:
    with urlopen(f"{url}?{urlencode(params)}", timeout=5) as response:
        return json.load(response)


def _goong_address(lat: float, lng: float) -> tuple[str, str]:
    data = _fetch_json("https://rsapi.goong.io/v2/geocode", {
        "latlng": f"{lat},{lng}", "limit": 1, "api_key": settings.GOONG_API_KEY.strip(),
    })
    results = data.get("results") or []
    result = results[0] if results else {}
    return (result.get("formatted_address") or "").strip(), (
        (result.get("compound") or {}).get("commune") or ""
    ).strip()


def _photon_address(lat: float, lng: float) -> tuple[str, str]:
    data = _fetch_json(f"{settings.PHOTON_BASE_URL.rstrip('/')}/reverse", {
        "lat": lat, "lon": lng, "limit": 1, "radius": 0.15,
    })
    features = data.get("features") or []
    return _format_photon_address(features[0]["properties"] if features else {})


def _format_photon_address(place: dict) -> tuple[str, str]:
    street = (place.get("street") or "").strip()
    if not street and place.get("type") == "street":
        street = (place.get("name") or "").strip()
    if not street:
        return "", ""
    house_number = (place.get("housenumber") or "").strip()
    street_address = f"{house_number} {street}".strip()
    ward = (place.get("district") or "").strip()
    parts = [street_address, ward, (place.get("city") or "").strip(), (place.get("state") or "").strip()]
    return ", ".join(dict.fromkeys(part for part in parts if part)), ward


class MapsService:
    async def search_address(self, query: str) -> dict:
        try:
            data = await asyncio.to_thread(_fetch_json, f"{settings.PHOTON_BASE_URL.rstrip('/')}/api", {
                "q": query, "lat": 10.7582, "lon": 106.7028, "zoom": 15, "limit": 5,
            })
            for feature in data.get("features") or []:
                address, ward = _format_photon_address(feature.get("properties") or {})
                if not address or len(address) > 400:
                    continue
                try:
                    location = POILocation.model_validate(feature.get("geometry"))
                except ValidationError:
                    continue
                return {
                    "address": address,
                    "ward": ward if 0 < len(ward) <= 80 else None,
                    "coordinates": location.coordinates,
                }
        except (OSError, ValueError, AttributeError, TypeError):
            raise HTTPException(502, "Không kết nối được dịch vụ tra địa chỉ") from None
        raise HTTPException(404, "Không tìm được địa chỉ trên bản đồ")

    async def reverse_geocode(self, lat: float, lng: float) -> dict:
        lookup = _goong_address if settings.GOONG_API_KEY.strip() else _photon_address
        try:
            address, ward = await asyncio.to_thread(lookup, lat, lng)
        except (OSError, ValueError, AttributeError, KeyError, TypeError):
            raise HTTPException(502, "Không kết nối được dịch vụ tra địa chỉ") from None

        if not address or len(address) > 400:
            raise HTTPException(404, "Không tìm được địa chỉ tại vị trí đã ghim")
        return {"address": address, "ward": ward if 0 < len(ward) <= 80 else None}

    async def get_offline_options(self) -> dict:
        return {
            "packs": [
                {
                    "id": "quan4-pmtiles-v1",
                    "name": "Bản đồ Vector Quận 4 (Offline PMTiles)",
                    "pmtiles_url": "/static/maps/quan4.pmtiles",
                    "bounds": [106.685, 10.745, 106.725, 10.772],
                    "center": [106.7028, 10.7582],
                }
            ]
        }


maps_service = MapsService()
