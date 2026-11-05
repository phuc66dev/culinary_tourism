"""Validate local asset paths independently of FastAPI/DB imports.

A valid path is *relative*, has no hidden/parent components and never crosses a
symbolic link. Do not convert user-controlled paths to strings and concatenate
with a directory to open them elsewhere without this validation.
"""
from pathlib import Path
from urllib.parse import unquote

from fastapi import HTTPException, status

_WINDOWS_RESERVED = frozenset({"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
                               *(f"COM{i}" for i in range(1, 10)),
                               *(f"LPT{i}" for i in range(1, 10))})


def _deny() -> None:
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid static asset path")


def resolve_safe_path(base_dir: str | Path, requested_path: str) -> Path:
    """Resolve paths under *base_dir* or raise 403 on traversal/ambiguous input.

    Rejects ../, absolute and Windows paths, backslashes, URL-encoded variants,
    NUL/control characters, dotfiles and *any* symlink on the path. The latter
    also rejects symlinks pointing inside the permitted folder to keep policy
    simple and avoid accidental cross-directory data exposure.
    """
    if not isinstance(requested_path, str) or not requested_path:
        _deny()
    if any(ord(c) < 32 or ord(c) == 127 for c in requested_path):
        _deny()
    if "\\" in requested_path or ":" in requested_path or "%" in requested_path:
        _deny()
    # Static paths are URI paths. Percent escapes may already have been decoded
    # by the ASGI server, but never accept a second encoding layer.
    if unquote(requested_path) != requested_path:
        _deny()
    if requested_path.startswith("/") or "//" in requested_path:
        _deny()
    components = requested_path.split("/")
    if any(
        c in ("", ".", "..") or c.startswith(".") or c.endswith((".", " "))
        or c.split(".", 1)[0].rstrip(" ").upper() in _WINDOWS_RESERVED
        for c in components
    ):
        _deny()
    base = Path(base_dir).resolve()
    candidate = base.joinpath(*components)
    # Check each existing part. This forbids links even if they point back into base.
    current = base
    for part in components:
        current = current / part
        if current.is_symlink():
            _deny()
    target = candidate.resolve(strict=False)
    if not target.is_relative_to(base):
        _deny()
    return target
