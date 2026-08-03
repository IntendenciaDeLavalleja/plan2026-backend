"""Read-only smoke test for the deployed backend and embedded admin panel."""

from __future__ import annotations

import json
import os
import re
import sys
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener


BASE_URL = os.environ.get("BACKEND_BASE_URL", "https://mapi.sgdm.lavalleja.uy").rstrip("/") + "/"
ADMIN_EMAIL = os.environ.get("ADMIN_SMOKE_EMAIL")
ADMIN_PASSWORD = os.environ.get("ADMIN_SMOKE_PASSWORD")
ADMIN_2FA_CODE = os.environ.get("ADMIN_SMOKE_2FA_CODE")


class SmokeFailure(RuntimeError):
    pass


def request(opener, path: str, *, method: str = "GET", payload=None, headers=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = {"Accept": "application/json"} if path.startswith("/api/") else {}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request_headers.update(headers or {})
    req = Request(urljoin(BASE_URL, path.lstrip("/")), data=body, method=method, headers=request_headers)
    try:
        response = opener.open(req, timeout=15)
    except HTTPError as error:
        response = error
    raw = response.read().decode("utf-8", errors="replace")
    return response.status, response.headers.get_content_type(), raw


def expect(opener, path: str, status: int, content_type: str, *, method: str = "GET", payload=None, headers=None):
    actual_status, actual_type, raw = request(opener, path, method=method, payload=payload, headers=headers)
    if actual_status != status or actual_type != content_type:
        raise SmokeFailure(f"{method} {path}: esperado {status} {content_type}; recibido {actual_status} {actual_type}; cuerpo={raw[:300]!r}")
    return raw


def main() -> int:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    expect(opener, "/healthz", 200, "application/json")
    login_page = expect(opener, "/admin/login", 200, "text/html")
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page)
    if not csrf_match:
        raise SmokeFailure("La página de login no expone el token CSRF para el cliente administrativo.")
    csrf_headers = {"X-CSRFToken": csrf_match.group(1)}
    captcha = json.loads(expect(opener, "/api/v1/admin/auth/captcha", 200, "application/json"))
    if not captcha.get("ok") or not captcha.get("data", {}).get("question") or "answer" in captcha.get("data", {}):
        raise SmokeFailure("Contrato CAPTCHA inválido o expone la respuesta.")
    expect(opener, "/api/v1/admin/auth/me", 401, "application/json")
    expect(opener, "/api/v1/public/tribute-types", 200, "application/json")
    expect(opener, "/api/v1/not-a-route", 404, "application/json")

    if ADMIN_EMAIL and ADMIN_PASSWORD and ADMIN_2FA_CODE:
        numbers = [int(value) for value in re.findall(r"\d+", captcha["data"]["question"])]
        if len(numbers) != 2:
            raise SmokeFailure("No se pudo resolver el formato esperado del CAPTCHA de smoke test.")
        login = json.loads(expect(
            opener,
            "/api/v1/admin/auth/login",
            200,
            "application/json",
            method="POST",
            payload={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "captcha": str(sum(numbers))},
            headers=csrf_headers,
        ))
        if not login.get("data", {}).get("requires_2fa"):
            raise SmokeFailure("El login no inició el segundo factor.")
        expect(opener, "/api/v1/admin/auth/verify-2fa", 200, "application/json", method="POST", payload={"code": ADMIN_2FA_CODE}, headers=csrf_headers)
        for path in (
            "/api/v1/admin/auth/me",
            "/api/v1/admin/dashboard",
            "/api/v1/admin/appointments",
            "/api/v1/admin/tribute-types",
            "/api/v1/admin/locations",
            "/api/v1/admin/availability/rules",
            "/api/v1/admin/availability/slots",
            "/api/v1/admin/availability/holidays",
        ):
            expect(opener, path, 200, "application/json")
    else:
        print("INFO: smoke autenticado omitido; defina ADMIN_SMOKE_EMAIL, ADMIN_SMOKE_PASSWORD y ADMIN_SMOKE_2FA_CODE.")

    print(f"OK: smoke test superado contra {BASE_URL.rstrip('/')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeFailure as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
