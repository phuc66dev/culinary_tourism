"""
Router cho phân hệ Owner Portal (`/api/v1/owner/*` — 12 Owner Routes).
Phụ trách: Phúc (Task 2.3 - 2.7)
"""
from fastapi import APIRouter, Depends, Query
from app.core.rbac import require_permission
from app.modules.owner.notifications import list_notifications, read_notification
from app.modules.owner.schemas import MenuItemRequest, POISubmissionRequest

router = APIRouter()


@router.get("/registration-status")
async def get_registration_status():
    """TODO (Phúc - Task 2.3): Kiểm tra trạng thái hồ sơ đăng ký chủ quán."""
    return {"status": "pending_verification", "is_poi_owner_verified": False}


@router.get("/pois/me")
async def get_my_pois():
    """TODO (Phúc - Task 2.4): Lấy thông tin quán ăn thuộc sở hữu của chủ quán hiện tại."""
    return {"items": []}


@router.put("/pois/{poi_id}")
async def update_my_poi(poi_id: str, payload: dict):
    """TODO (Phúc - Task 2.4): Cập nhật nhanh trạng thái mở cửa hoặc thông tin cơ bản."""
    return {"status": "todo", "poi_id": poi_id}


@router.post("/submissions")
async def create_poi_submission(payload: POISubmissionRequest):
    """TODO (Phúc - Task 2.6): Gửi đề xuất thay đổi thông tin quán (`poi_submissions`) chờ Admin duyệt."""
    return {"status": "pending", "message": "Đã gửi đề xuất chờ Admin phê duyệt"}


@router.get("/menu-items")
async def list_my_menu_items(poi_id: str):
    """TODO (Phúc - Task 2.5): Danh sách món ăn trong thực đơn của quán."""
    return {"items": []}


@router.post("/menu-items")
async def create_menu_item(payload: MenuItemRequest):
    """TODO (Phúc - Task 2.5): Thêm món ăn mới vào thực đơn."""
    return {"status": "todo"}


@router.get("/notifications")
async def list_owner_notifications(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    user: dict = Depends(require_permission("owner:access")),
):
    """Hộp thư kết quả duyệt đăng ký/đề xuất (chỉ dữ liệu chủ quán đăng nhập)."""
    return await list_notifications(user, limit, skip)


@router.get("/notifications/{notification_id}")
async def get_owner_notification(
    notification_id: str, user: dict = Depends(require_permission("owner:access")),
):
    """Đọc chi tiết + đánh dấu đã đọc (không cho xem thông báo của chủ quán khác)."""
    return await read_notification(notification_id, user)
