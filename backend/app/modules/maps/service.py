"""
MapsService — Quản lý manifest bản đồ ngoại tuyến PMTiles (Quận 4) và kiểm tra Path Guard.
Phụ trách: Bảo (Task 1.10) & Vũ (Task 3.11)
"""


class MapsService:
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
