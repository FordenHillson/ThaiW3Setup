"""HTTPS verification: system store plus certifi's Mozilla CA bundle."""
import os, ssl, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import net
from core.osutil import WINDOWS

# --- macOS .app stand-in: OpenSSL pointed at a CA file that does not exist -------------------------
# On Windows, create_default_context() still loads the system store even with SSL_CERT_FILE set.
os.environ["SSL_CERT_FILE"] = os.devnull
os.environ["SSL_CERT_DIR"] = os.devnull
if not WINDOWS:
    assert ssl.create_default_context().cert_store_stats()["x509_ca"] == 0, "the stand-in for the bundle trusts nothing"
net.ssl_context.cache_clear()
assert net.ssl_context().cert_store_stats()["x509_ca"] > 100, "certifi's authorities are loaded on top"

# --- every request goes through that context ---------------------------------------------------------
seen = {}
orig = urllib.request.urlopen
try:
    urllib.request.urlopen = lambda req, timeout, context=None: seen.update(timeout=timeout, context=context)
    net.urlopen(urllib.request.Request("https://example.invalid/"), 7)
finally:
    urllib.request.urlopen = orig
assert seen == {"timeout": 7, "context": net.ssl_context()}, seen

# --- telling a certificate failure apart from being offline ------------------------------------------
cert = urllib.error.URLError(ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"))
assert net.is_certificate_error(cert)
assert not net.is_certificate_error(urllib.error.URLError("timed out"))
assert not net.is_certificate_error(urllib.error.URLError(OSError(8, "nodename nor servname provided")))

# --- the real thing, when there is a network ----------------------------------------------------------
try:
    with net.urlopen(urllib.request.Request("https://api.github.com/", headers={"User-Agent": "test_net"}), 15) as r:
        assert r.status == 200
    print("live HTTPS ok with system store + certifi")
except urllib.error.URLError as exc:
    assert not net.is_certificate_error(exc), exc
    print("live HTTPS skipped:", exc)

print("test_net ok")
