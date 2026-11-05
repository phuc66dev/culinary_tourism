"""Deterministic provenance of audio translations derived from Vietnamese POI text."""
import hashlib


def source_fingerprint(name: str, description: str) -> str:
    # This is a freshness identifier, NOT an authentication/security digest.
    return hashlib.sha256(((name or "") + "\0" + (description or "")).encode("utf-8")).hexdigest()
