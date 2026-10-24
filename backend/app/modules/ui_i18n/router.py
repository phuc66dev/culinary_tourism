"""Router cho phân hệ UI i18n Bundles (`/api/v1/ui-bundles/*`)."""
from fastapi import APIRouter, Query
from app.modules.ui_i18n.service import ui_i18n_service

router = APIRouter()


@router.get("")
async def get_ui_bundle(locale: str = Query("vi"), namespace: str = Query("public")):
    """Tải bundle chuỗi giao diện theo ngôn ngữ cho cơ chế Dual-Lane i18n."""
    return await ui_i18n_service.get_ui_bundle(locale=locale, namespace=namespace)
