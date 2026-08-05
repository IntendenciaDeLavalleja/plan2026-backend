import os

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_marshmallow import Marshmallow
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
ma = Marshmallow()
limiter = Limiter(key_func=get_remote_address)
talisman = Talisman()
csrf = CSRFProtect()
cors = CORS()
jwt = JWTManager()

login_manager.login_view = None  # we manage login via the API
# "strong" invalida la sesion cuando cambia el identificador (X-Forwarded-For + User-Agent).
# Detras de Traefik/Cloudflare esa IP cambia entre requests y la sesion se borra sola.
login_manager.session_protection = os.environ.get("SESSION_PROTECTION", "basic").strip().lower() or None
if login_manager.session_protection == "none":
    login_manager.session_protection = None
