"""SSL Certificate Support for Windows & Antivirus / Proxy Environments.

Merges OS-installed root certificates (Windows ROOT and CA certificate stores)
with Mozilla certifi bundle, ensuring Python applications (requests, httpx,
aiohttp, edge-tts) do not fail with SSLCertVerificationError.
"""
import os
import sys
import ssl
import logging
from pathlib import Path

logger = logging.getLogger("quan4.ssl")

_COMBINED_PEM_PATH: Path | None = None
_SSL_CONTEXT: ssl.SSLContext | None = None


def get_ssl_context(verify: bool = True) -> ssl.SSLContext:
    """Create an SSL context that trusts both certifi and system root certificates."""
    if not verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    global _SSL_CONTEXT
    if _SSL_CONTEXT is not None:
        return _SSL_CONTEXT

    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()

    if sys.platform == "win32":
        for store in ("ROOT", "CA"):
            try:
                for cert, enc, trust in ssl.enum_certificates(store):
                    if enc == "x509_asn":
                        try:
                            ctx.load_verify_locations(cdata=ssl.DER_cert_to_PEM_cert(cert))
                        except Exception:
                            pass
            except Exception:
                pass

    _SSL_CONTEXT = ctx
    return ctx


def ensure_ssl_certificates() -> Path | None:
    """Export combined cert bundle and configure environment variables."""
    global _COMBINED_PEM_PATH
    if _COMBINED_PEM_PATH is not None and _COMBINED_PEM_PATH.is_file():
        return _COMBINED_PEM_PATH

    try:
        import certifi
        base_cert_path = certifi.where()
        base_pem = Path(base_cert_path).read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not read certifi bundle: %s", exc)
        return None

    extra_pems: list[str] = []
    if sys.platform == "win32":
        for store in ("ROOT", "CA"):
            try:
                for cert, enc, trust in ssl.enum_certificates(store):
                    if enc == "x509_asn":
                        try:
                            extra_pems.append(ssl.DER_cert_to_PEM_cert(cert))
                        except Exception:
                            pass
            except Exception as exc:
                logger.warning("Failed to enum Windows store %s: %s", store, exc)

    target_dir = Path(__file__).resolve().parents[1] / "static"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "cacert_combined.pem"

    try:
        content = base_pem.rstrip() + "\n" + "\n".join(extra_pems) + "\n"
        target_file.write_text(content, encoding="utf-8")
        _COMBINED_PEM_PATH = target_file
        resolved = str(target_file.resolve())
        os.environ["SSL_CERT_FILE"] = resolved
        os.environ["REQUESTS_CA_BUNDLE"] = resolved
        logger.info("Configured combined SSL cert bundle with %d OS root certs", len(extra_pems))
    except Exception as exc:
        logger.warning("Failed to write combined cert bundle: %s", exc)
        return None

    # Patch edge-tts internal SSL context if edge-tts is imported
    try:
        import edge_tts.communicate
        edge_tts.communicate._SSL_CTX = get_ssl_context()
    except Exception:
        pass

    return target_file
