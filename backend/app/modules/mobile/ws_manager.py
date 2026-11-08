from datetime import datetime
import json
import logging
from typing import Dict, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Quản lý kết nối WebSocket và đếm người dùng online trong thời gian thực."""

    def __init__(self):
        # Lưu kết nối active: {device_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Lưu thông tin online: {device_id: user_info}
        self.online_users: Dict[str, dict] = {}

    async def connect(
        self,
        websocket: WebSocket,
        device_id: str,
        user_id: Optional[str] = None,
        platform: Optional[str] = None,
    ):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        self.online_users[device_id] = {
            "device_id": device_id,
            "user_id": user_id,
            "platform": platform,
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }
        logger.info(f"User connected: {device_id}, Total: {len(self.online_users)}")
        await self.broadcast_online_count()

    def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
        if device_id in self.online_users:
            del self.online_users[device_id]
        logger.info(f"User disconnected: {device_id}, Total: {len(self.online_users)}")

    async def broadcast_online_count(self):
        mobile_users = {
            k: v for k, v in self.online_users.items() if not k.startswith("admin-")
        }
        count = len(mobile_users)

        message = {
            "type": "online_count",
            "count": count,
            "timestamp": datetime.utcnow().isoformat(),
            "users": list(mobile_users.values()),
        }

        disconnected_users = []
        for device_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {device_id}: {e}")
                disconnected_users.append(device_id)

        for device_id in disconnected_users:
            self.disconnect(device_id)

    async def send_personal_message(self, message: str, device_id: str):
        if device_id in self.active_connections:
            try:
                await self.active_connections[device_id].send_text(message)
            except Exception as e:
                logger.error(f"Error sending personal message to {device_id}: {e}")
                self.disconnect(device_id)

    def get_online_count(self) -> int:
        return len({k: v for k, v in self.online_users.items() if not k.startswith("admin-")})

    def get_online_users(self) -> list:
        mobile_users = {
            k: v for k, v in self.online_users.items() if not k.startswith("admin-")
        }
        return list(mobile_users.values())


manager = ConnectionManager()

