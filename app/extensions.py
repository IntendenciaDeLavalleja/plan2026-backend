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

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
ma = Marshmallow()
limiter = Limiter(key_func=get_remote_address)
talisman = Talisman()
csrf = CSRFProtect()
cors = CORS()

login_manager.login_view = None  # we manage login via the API
login_manager.session_protection = "strong"
