"""End-to-end check of the dashboard cross-origin flow against the running API.

Run inside the api container:
    docker compose exec -T api sh -c "cd /app && PYTHONPATH=/app python scripts/dashboard_flow_check.py"
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import urllib.error
from http.cookiejar import CookieJar

from flask import Flask
from flask.sessions import SecureCookieSessionInterface

from app import create_app

BASE = os.environ.get("REPRO_BASE_URL", "http://127.0.0.1:5000").rstrip("/") + "/"
EMAIL = os.environ.get("REPRO_EMAIL", "dash-test@plan2026.local")
PASSWORD = os.environ.get("REPRO_PASSWORD", "test-password-123")
ORIGIN = os.environ.get("REPRO_ORIGIN", "http://localhost:8080")


def _decode_session(cookie_value: str) -> dict:
    app = create_app()
    serializer = SecureCookieSessionInterface().get_signing_serializer(app)
    if serializer is None:
        return {}
    try:
        return serializer.loads(cookie_value)
    except Exception:
        return {}


def _request(opener, path: str, *, method: str = "GET", payload=None, headers=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req_headers = {"Accept": "application/json", "Origin": ORIGIN}
    if body is not None:
        req_headers["Content-Type"] = "application/json"
    req_headers.update(headers or {})
    req = urllib.request.Request(BASE + path.lstrip("/"), data=body, method=method, headers=req_headers)
    started = time.perf_counter()
    try:
        resp = opener.open(req, timeout=45)
    except urllib.error.HTTPError as exc:
        resp = exc
    raw = resp.read().decode("utf-8", errors="replace")
    ms = int((time.perf_counter() - started) * 1000)
    return resp.status, resp.headers, raw, ms


def _mailpit_code() -> str:
    try:
        with urllib.request.urlopen("http://mailpit:8025/api/v1/messages?limit=1", timeout=5) as r:
            msgs = json.loads(r.read().decode("utf-8")).get("messages", [])
        if not msgs or not msgs[0].get("ID"):
            return ""
        with urllib.request.urlopen(f"http://mailpit:8025/api/v1/message/{msgs[0]['ID']}/raw", timeout=5) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except Exception:
        return ""
    m = re.search(r"\b(\d{6})\b", raw)
    return m.group(1) if m else ""


def main() -> int:
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(("PASS" if cond else "FAIL"), name, detail)
        ok = ok and cond

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    # 1. CSRF token endpoint (cross-origin GET).
    s, h, body, ms = _request(opener, "api/v1/admin/auth/csrf-token")
    check("csrf-token 200", s == 200 and body, f"{s} {ms}ms")
    csrf = json.loads(body).get("data", {}).get("csrf_token", "")
    check("csrf-token present", bool(csrf))
    check("CORS allow-origin reflects dashboard origin", h.get("Access-Control-Allow-Origin") == ORIGIN)
    check("CORS allow-credentials", h.get("Access-Control-Allow-Credentials", "").lower() == "true")

    # 2. Captcha and session decode.
    s, _, body, _ = _request(opener, "api/v1/admin/auth/captcha")
    check("captcha 200", s == 200)
    jar = next((getattr(hh, "cookiejar", None) for hh in opener.handlers if getattr(hh, "cookiejar", None)), None)
    session_cookie = next((c.value for c in jar if c.name == "session"), None) if jar else None
    answer = str(_decode_session(session_cookie or "").get("captcha_result", ""))
    check("captcha answer decoded", bool(answer))

    # 3. Login with CSRF header.
    s, _, body, ms = _request(
        opener, "api/v1/admin/auth/login", method="POST",
        payload={"email": EMAIL, "password": PASSWORD, "captcha": answer},
        headers={"X-CSRFToken": csrf},
    )
    check("login 200 requires_2fa", s == 200 and "requires_2fa" in body, f"{s} {ms}ms")

    # 4. Verify 2FA with code from mailpit, then re-bind the CSRF token.
    code = _mailpit_code()
    check("2FA code delivered to mailpit", bool(code))
    s, _, body, ms = _request(
        opener, "api/v1/admin/auth/verify-2fa", method="POST",
        payload={"code": code},
        headers={"X-CSRFToken": csrf},
    )
    check("verify-2fa 200", s == 200 and '"user"' in body, f"{s} {ms}ms")
    s, _, body, _ = _request(opener, "api/v1/admin/auth/csrf-token")
    csrf = json.loads(body).get("data", {}).get("csrf_token", "")
    check("csrf re-bound after 2FA", bool(csrf))

    # 5. Authenticated endpoints.
    s, _, body, ms = _request(opener, "api/v1/admin/tickets/current-hour")
    check("current-hour 200", s == 200 and "tickets" in body, f"{s} {ms}ms")
    s, _, body, ms = _request(opener, "api/v1/admin/dashboard/today")
    check("dashboard/today 200", s == 200 and "buckets" in body, f"{s} {ms}ms")
    s, _, body, ms = _request(opener, "api/v1/admin/tickets")
    check("tickets list 200", s == 200 and "items" in body, f"{s} {ms}ms")

    # 6. Status change with audit (only if a pending ticket exists).
    tickets = json.loads(body).get("data", {}).get("items", [])
    pending = next((t for t in tickets if t["status"] in ("reserved", "confirmed")), None)
    if pending:
        s, _, body, ms = _request(
            opener, f"api/v1/admin/tickets/{pending['id']}/status", method="PATCH",
            payload={"status": "called", "note": "Chequeo E2E"},
            headers={"X-CSRFToken": csrf},
        )
        check("status change to called", s == 200 and '"called"' in body, f"{s} {ms}ms")
        s, _, body, _ = _request(opener, f"api/v1/admin/tickets/{pending['id']}/history")
        check("history recorded", s == 200 and "called" in body, body[:200])
    else:
        print("INFO no pending ticket available for mutation test")

    print("RESULT", "ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
