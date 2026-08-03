"""Friendly reservation code generator: IDL-AF-2026-XXXXXX."""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone

from flask import current_app

_ALPHABET = string.ascii_uppercase + string.digits


def _alphabet_no_ambiguous() -> str:
    # remove confusing chars: 0/O, 1/I/L
    return "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_reservation_code() -> str:
    prefix = current_app.config.get("RESERVATION_CODE_PREFIX", "IDL-AF")
    year = datetime.now(timezone.utc).year
    alphabet = _alphabet_no_ambiguous()
    suffix = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"{prefix}-{year}-{suffix}"
