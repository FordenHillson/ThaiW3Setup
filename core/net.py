"""HTTPS requests that verify against both the system store and certifi.

The macOS .app bundles python.org's Python, and its OpenSSL trusts no certificate authority until the
installer's "Install Certificates" step runs, which never happens inside a bundle. Windows usually
trusts the system store, but some machines are missing a public root or intermediate (e.g. GitHub's
chain) and then fail with CERTIFICATE_VERIFY_FAILED / unable to get local issuer certificate.
Loading certifi on top of create_default_context() keeps system CAs (including AV MITM roots) and
fills gaps with Mozilla's bundle.
"""
from __future__ import annotations

import functools
import logging
import ssl
import urllib.request

log = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(cafile=certifi.where())
    except (ImportError, OSError) as exc:  # still try what the system trusts
        log.warning("certifi unavailable, using the default certificate store: %s", exc)
    return ctx


def urlopen(req: urllib.request.Request, timeout: float):
    return urllib.request.urlopen(req, timeout=timeout, context=ssl_context())


def is_certificate_error(exc: BaseException) -> bool:
    """True when the connection worked but the server's certificate could not be verified."""
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc)
