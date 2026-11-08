import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.modules.mobile.ws_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws")


@router.websocket("/online/{device_id}")
async def websocket_online_endpoint(device_id: str, websocket: WebSocket):
    """
    WebSocket endpoint theo dõi trạng thái online của thiết bị theo thời gian thực.
    """
    user_id = None
    platform = None
    is_admin = device_id.startswith("admin-")

    try:
        await manager.connect(websocket, device_id, user_id, platform)
        if is_admin:
            logger.info(f"Admin viewer connected: {device_id}")
        else:
            logger.info(f"Mobile device connected: {device_id}")

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except Exception:
                continue

            action = message.get("action")

            if action == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "online_count": manager.get_online_count(),
                })

            elif action == "update_user":
                if not is_admin:
                    user_id = message.get("user_id")
                    platform = message.get("platform")
                    if device_id in manager.online_users:
                        manager.online_users[device_id].update({
                            "user_id": user_id,
                            "platform": platform,
                        })
                    await manager.broadcast_online_count()

    except WebSocketDisconnect:
        manager.disconnect(device_id)
        if not is_admin:
            await manager.broadcast_online_count()

    except Exception as e:
        logger.error(f"WebSocket error for {device_id}: {e}")
        manager.disconnect(device_id)
        if not is_admin:
            await manager.broadcast_online_count()


@router.get("/online/count", tags=["Mobile Client (App)"], summary="Số lượng thiết bị đang online")
def get_online_count():
    count = manager.get_online_count()
    return {"online_count": count}


@router.get("/online/users", tags=["Mobile Client (App)"], summary="Danh sách thiết bị online")
def get_online_users(limit: int = 100):
    users = manager.get_online_users()
    if limit:
        users = users[:limit]
    return {
        "total": len(users),
        "users": users,
    }

