from __future__ import annotations

from flask import jsonify, render_template, request
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


def ok(data=None, status: int = 200, **meta):
    payload: dict = {"ok": True, "data": data}
    if meta:
        payload["meta"] = meta
    return jsonify(payload), status


def fail(message: str, status: int = 400, code: str | None = None, errors=None):
    payload: dict = {"ok": False, "error": {"message": message, "code": code or "bad_request"}}
    if errors is not None:
        payload["error"]["errors"] = errors
    return jsonify(payload), status


def paginated(items, page: int, per_page: int, total: int):
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page if per_page else 1,
    }


def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def _on_validation(err: ValidationError):
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)

    @app.errorhandler(HTTPException)
    def _on_http(err: HTTPException):
        if err.code == 404 and not request.path.startswith("/api/"):
            return render_template("errors/404.html", path=request.path), 404
        return fail(err.description or err.name, err.code or 500, code=(err.name or "http_error").lower().replace(" ", "_"))

    @app.errorhandler(Exception)
    def _on_unexpected(err: Exception):  # pragma: no cover - safety net
        app.logger.exception("Unexpected error: %s", err)
        return fail("Error interno del servidor", 500, code="internal_error")
