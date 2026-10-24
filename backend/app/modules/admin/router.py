"""
Router cho phân hệ Admin & Auth (`/api/v1/admin/*`).
Phụ trách: Vũ (40 Admin Routes) & Phúc (Endpoint `/auth/register-owner`)
"""
from fastapi import APIRouter
from app.modules.admin.schemas import LoginRequest, OwnerRegisterRequest, ReviewDecisionRequest

router = APIRouter()


# ==========================================
# 1. Authentication & Public Owner Register
# ==========================================
@router.post("/auth/login")
async def login(payload: LoginRequest):
    """TODO (Vũ - Task 3.2): Xác thực và gắn httpOnly Cookie (`access_token`, `refresh_token`)."""
    return {"status": "todo", "endpoint": "POST /api/v1/admin/auth/login"}


@router.post("/auth/logout")
async def logout():
    """TODO (Vũ - Task 3.2): Xóa httpOnly Cookie."""
    return {"status": "todo", "endpoint": "POST /api/v1/admin/auth/logout"}


@router.get("/auth/me")
async def get_me():
    """TODO (Vũ - Task 3.2): Trả về thông tin tài khoản hiện tại + danh sách permissions."""
    return {"status": "todo", "endpoint": "GET /api/v1/admin/auth/me"}


@router.post("/auth/register-owner")
async def register_owner(payload: OwnerRegisterRequest):
    """
    TODO (Phúc - Task 2.1, 2.2):
    - Mã hóa `cccd_number` bằng Fernet (`v1:<encrypted>`).
    - Tạo user (`role="poi_owner"`, `is_poi_owner_verified=False`).
    - Tạo bản ghi `poi_owner_registrations` (`status="pending"`).
    """
    return {"status": "todo", "endpoint": "POST /api/v1/admin/auth/register-owner"}


# ==========================================
# 2. POI Management & Activation Gate
# ==========================================
@router.get("/pois")
async def list_admin_pois():
    """TODO (Vũ - Task 3.4): Danh sách toàn bộ POI cho Admin Dashboard."""
    return {"items": []}


@router.post("/pois")
async def create_poi(payload: dict):
    """TODO (Vũ - Task 3.4): Tạo mới POI và đẩy vào hàng đợi AudioTaskManager."""
    return {"status": "todo"}


# ==========================================
# 3. Kiểm duyệt Đơn Chủ Quán & POI Submissions
# ==========================================
@router.get("/registrations")
async def list_owner_registrations():
    """TODO (Vũ - Task 3.5): Danh sách đơn đăng ký chủ quán (`poi_owner_registrations`)."""
    return {"items": []}


@router.post("/registrations/{reg_id}/review")
async def review_owner_registration(reg_id: str, decision: ReviewDecisionRequest):
    """TODO (Vũ - Task 3.5): Duyệt hoặc từ chối đơn chủ quán kèm `admin_note`."""
    return {"status": "todo", "reg_id": reg_id}


@router.get("/submissions")
async def list_poi_submissions():
    """TODO (Vũ - Task 3.6): Danh sách đề xuất chỉnh sửa quán (`poi_submissions`)."""
    return {"items": []}


@router.post("/submissions/{sub_id}/review")
async def review_poi_submission(sub_id: str, decision: ReviewDecisionRequest):
    """TODO (Vũ - Task 3.6): Merge thay đổi vào `POI`, tăng `dataset_version` và gửi thông báo."""
    return {"status": "todo", "sub_id": sub_id}


# ==========================================
# 4. Audio Tasks & SSE Stream
# ==========================================
@router.get("/audio-tasks/stream")
async def stream_audio_tasks():
    """TODO (Vũ - Task 3.9): Server-Sent Events (SSE) phát tiến độ tạo audio thời gian thực."""
    return {"status": "todo", "stream": "sse"}


# ==========================================
# 5. Users, Roles & Audit Logs
# ==========================================
@router.get("/users")
async def list_users():
    return {"items": []}


@router.get("/roles")
async def list_roles():
    return {"items": []}


@router.get("/audit-logs")
async def list_audit_logs():
    return {"items": []}
