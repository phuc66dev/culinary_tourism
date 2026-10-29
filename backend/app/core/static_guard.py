"""StaticFiles with mandatory path traversal checks for maps, audio and images.

Starlette's get_path normalizes '..' components *before* lookup. We override it
and check the original mount-relative ASGI path so suspicious input is rejected
rather than being silently normalized into a different, valid file.
"""
from pathlib import Path
from fastapi import HTTPException
from starlette._utils import get_route_path
from starlette.staticfiles import StaticFiles

from app.core.path_security import resolve_safe_path


class GuardedStaticFiles(StaticFiles):
    _MEDIA_EXTENSIONS = {
        "audio": frozenset({".mp3"}),
        "maps": frozenset({".pmtiles", ".pbf", ".json", ".png", ".webp"}),
        "images": frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif"}),
    }

    def get_path(self, scope):
        original = get_route_path(scope)
        # get_route_path for an app mounted at /static begins with '/'. That
        # single framework-added delimiter is NOT part of the user path.
        relative = original[1:] if original.startswith("/") else original
        if not relative:
            return relative
        base = self.directory
        resolve_safe_path(base, relative)
        section, _, filename = relative.partition("/")
        allowed = self._MEDIA_EXTENSIONS.get(section)
        if allowed is None or not filename or Path(filename).suffix.lower() not in allowed:
            raise HTTPException(403, "Static file type is not allowed")
        return relative

    def lookup_path(self, path):
        # Defense in depth: Starlette also validates again during file lookup.
        if path:
            resolve_safe_path(self.directory, path)
        return super().lookup_path(path)

    async def get_response(self, path, scope):
        """Serve allowed assets with hardened browser interpretation headers.

        nosniff prevents content disguised with an image/audio extension from
        being interpreted as HTML/JS. CSP sandbox isolates an SVG opened as a
        document from the authenticated API origin.
        """
        response = await super().get_response(path, scope)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Content-Security-Policy", "sandbox; default-src 'none'")
        return response
