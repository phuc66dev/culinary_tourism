"""Authenticated APIs for the Owner Portal."""
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.rbac import require_permission
from app.core.security import get_current_user
from app.modules.owner import service
from app.modules.owner.notifications import list_notifications, read_notification
from app.modules.owner.schemas import (
    MenuItemRequest,
    MenuItemUpdateRequest,
    OwnerPOIAvailabilityRequest,
    POISubmissionRequest,
)

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/dashboard")
async def owner_dashboard(user: dict = Depends(require_permission("analytics:view_own"))):
    return await service.get_dashboard_summary(user)


@router.get("/registration-status")
async def get_registration_status(user: dict = Depends(require_permission("owner:access"))):
    return await service.get_registration_status(user)


@router.get("/pois/me")
async def get_my_pois(user: dict = Depends(require_permission("owner:manage_own_poi"))):
    return await service.list_my_pois(user)


@router.put("/pois/{poi_id}")
async def update_my_poi(
    poi_id: str,
    payload: OwnerPOIAvailabilityRequest,
    request: Request,
    user: dict = Depends(require_permission("owner:manage_own_poi")),
):
    return await service.update_poi_availability(poi_id, payload, user, _client_ip(request))


@router.get("/submissions")
async def list_my_submissions(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    review_status: Literal["pending", "approved", "rejected"] | None = None,
    q: str = Query("", max_length=120),
    sort_by: Literal["created_at", "reviewed_at"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    user: dict = Depends(require_permission("owner:submit_poi")),
):
    return await service.list_my_submissions(
        user, limit, skip, review_status=review_status, q=q, sort_by=sort_by, order=order,
    )


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
async def create_poi_submission(
    payload: POISubmissionRequest,
    request: Request,
    user: dict = Depends(require_permission("owner:submit_poi")),
):
    return await service.create_poi_submission(payload, user, _client_ip(request))


@router.get("/menu-items")
async def list_my_menu_items(
    poi_id: str,
    user: dict = Depends(require_permission("menu:read")),
):
    return await service.list_my_menu_items(poi_id, user)


@router.post("/menu-items/images", status_code=status.HTTP_201_CREATED)
async def upload_menu_image(
    poi_id: str,
    image: UploadFile = File(...),
    menu_item_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    permission = "menu:update" if menu_item_id else "menu:create"
    if permission not in user["permissions"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không có quyền tải ảnh món ăn")
    await service.authorize_menu_image_upload(poi_id, user, menu_item_id)
    content = await image.read(service.MENU_IMAGE_MAX_BYTES + 1)
    return {"image_url": await run_in_threadpool(service.store_menu_image, content)}


@router.post("/menu-items", status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    payload: MenuItemRequest,
    request: Request,
    user: dict = Depends(require_permission("menu:create")),
):
    return await service.create_menu_item(payload, user, _client_ip(request))


@router.patch("/menu-items/{menu_item_id}")
async def update_menu_item(
    menu_item_id: str,
    payload: MenuItemUpdateRequest,
    request: Request,
    user: dict = Depends(require_permission("menu:update")),
):
    return await service.update_menu_item(menu_item_id, payload, user, _client_ip(request))


@router.delete("/menu-items/{menu_item_id}")
async def delete_menu_item(
    menu_item_id: str,
    request: Request,
    user: dict = Depends(require_permission("menu:delete")),
):
    return await service.delete_menu_item(menu_item_id, user, _client_ip(request))


@router.get("/notifications")
async def list_owner_notifications(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    is_read: bool | None = Query(None),
    user: dict = Depends(require_permission("owner:access")),
):
    return await list_notifications(user, limit, skip, is_read)


@router.get("/notifications/{notification_id}")
async def get_owner_notification(
    notification_id: str,
    user: dict = Depends(require_permission("owner:access")),
):
    return await read_notification(notification_id, user)
