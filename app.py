from datetime import timedelta
import logging
import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

from go_get_it.go_get_it import GoGetDB
from demiplane.auth import setup_auth
from db.config import (
    DEBUG,
    FORCE_HTTPS,
    secret_key,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_FILE_DIR,
    SESSION_LIFETIME_DAYS,
    SESSION_FILE_THRESHOLD,
    RATE_LIMIT_STORAGE_URI,
)
from db.monitoring import register_monitoring
from demiplane.routes.admin import register_admin_routes
from demiplane.routes.dnd_character_sheet import register_dnd_character_sheet_routes
from demiplane.routes.errors import register_error_handlers
from demiplane.routes.fragments import register_fragment_routes
from demiplane.routes.main import register_main_routes
from demiplane.routes.user_theme import register_user_theme_routes

# ── App creation ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = secret_key

# Under Gunicorn, align Flask logger handlers so request-form logs are visible.
_gunicorn_error_logger = logging.getLogger('gunicorn.error')
if _gunicorn_error_logger.handlers:
    app.logger.handlers = _gunicorn_error_logger.handlers
    app.logger.propagate = False

# ── Request size limit (16 KB) ────────────────────────────────────────────────
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024

# ── Server-side sessions (filesystem) ─────────────────────────────────────────
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_NAME'] = SESSION_COOKIE_NAME
app.config['SESSION_FILE_DIR'] = SESSION_FILE_DIR
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=SESSION_LIFETIME_DAYS)
app.config['SESSION_FILE_THRESHOLD'] = SESSION_FILE_THRESHOLD
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
Session(app)

register_monitoring(app)

# ── CSRF ──────────────────────────────────────────────────────────────────────
CSRFProtect(app)

# ── Rate limiting ─────────────────────────────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=['60/minute'],
    storage_uri=RATE_LIMIT_STORAGE_URI,
)

# ── Security headers (Talisman) ──────────────────────────────────────────────
csp = {
    'default-src': "'self'",
    'base-uri': "'self'",
    'form-action': "'self'",
    'frame-ancestors': "'none'",
    'object-src': "'none'",
    'script-src': [
        "'self'",
        'https://cdn.jsdelivr.net',
        'https://unpkg.com',
    ],
    'style-src': [
        "'self'",
        "'unsafe-inline'",
        'https://cdn.jsdelivr.net',
        'https://fonts.googleapis.com',
    ],
    'font-src': [
        "'self'",
        'https://cdn.jsdelivr.net',
        'https://fonts.gstatic.com',
    ],
    'img-src': "'self' data:",
}
Talisman(
    app,
    force_https=FORCE_HTTPS,
    content_security_policy=csp,
    session_cookie_secure=SESSION_COOKIE_SECURE,
)

# ── Static asset cache-busting ────────────────────────────────────────────────
@app.context_processor
def inject_static_version():
    js_path = os.path.join(app.static_folder, 'scripts', 'dnd_sheet.js')
    version = int(os.path.getmtime(js_path)) if os.path.exists(js_path) else 1
    return {'static_version': version}

@app.after_request
def no_cache_html(response):
    if 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
    return response

# ── Database, auth & routes ───────────────────────────────────────────────────
db = GoGetDB()
db.go_create_db()
setup_auth(app, db, limiter)
register_error_handlers(app, db)
register_user_theme_routes(app, db)
register_dnd_character_sheet_routes(app, db, limiter)
register_admin_routes(app, db)
register_fragment_routes(app, db, limiter)
register_main_routes(app, db)

if __name__ == '__main__':
    db.go_create_db()
    db.go_sync_schema()
    db.go_seed_db()
    app.run(host='0.0.0.0', port=8888, debug=DEBUG)
