"""Service quản lý gói ngôn ngữ giao diện (`ui_translation_bundles`)."""


class UII18nService:
    async def get_ui_bundle(self, locale: str = "vi", namespace: str = "public") -> dict:
        return {
            "locale": locale,
            "namespace": namespace,
            "status": "ready",
            "translations": {},
        }


ui_i18n_service = UII18nService()
