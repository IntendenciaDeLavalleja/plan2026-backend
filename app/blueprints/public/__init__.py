from flask import Blueprint

public_bp = Blueprint("public_api", __name__)

from . import routes  # noqa: E402,F401
