from collections import deque
from datetime import timedelta
from functools import wraps
import logging
from threading import Lock
from urllib.parse import urlparse

from flask import Flask, abort, render_template, request
from flask_wtf.csrf import CSRFProtect
from flask_login import current_user
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

from character_sheet.character_sheet import CharacterSheet, TRACKER_MAX, TRACKER_ENTRY_MAX
from character_sheet.custom_buff import BuffProcessor
from character_sheet import guest_character as guest
from go_get_it.go_get_it import GoGetDB
from auth import setup_auth
from auth.models import User
from auth.models import UserTheme
from routes.admin import register_admin_routes
from routes.dnd_character_sheet import register_dnd_character_sheet_routes
from routes.fragments import get_trackers_for_character, register_fragment_routes
from routes.user_theme import register_user_theme_routes
from misc.config import (
    DEBUG,
    FORCE_HTTPS,
    HEADER_MONITOR_ENABLED,
    HEADER_MONITOR_LOG_EVERY,
    HEADER_MONITOR_WINDOW,
    HEADER_SIZE_WARN_BYTES,
    HEADER_WARN_RATE_THRESHOLD_PCT,
    secret_key,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_FILE_DIR,
    SESSION_LIFETIME_DAYS,
    SESSION_FILE_THRESHOLD,
    RATE_LIMIT_STORAGE_URI,
    REQUEST_FORM_LOG_ENABLED,
    REQUEST_FORM_LOG_INCLUDE_GET,
    REQUEST_FORM_LOG_INCLUDE_ENDPOINT,
    REQUEST_FORM_LOG_INCLUDE_HTMX,
    REQUEST_FORM_LOG_INCLUDE_VALUES,
    REQUEST_FORM_LOG_MAX_VALUE_LEN,
)  # type: ignore

# ── App creation ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = secret_key

# Under Gunicorn, align Flask logger handlers so request-form logs are visible.
_gunicorn_error_logger = logging.getLogger('gunicorn.error')
if _gunicorn_error_logger.handlers:
    app.logger.handlers = _gunicorn_error_logger.handlers
    app.logger.propagate = False

# Request form logging is a diagnostic feature; ensure INFO lines are emitted.
if REQUEST_FORM_LOG_ENABLED:
    app.logger.setLevel(logging.INFO)
    app.logger.info(
        'Request form logging enabled: include_get=%s include_endpoint=%s include_htmx=%s include_values=%s max_value_len=%s',
        REQUEST_FORM_LOG_INCLUDE_GET,
        REQUEST_FORM_LOG_INCLUDE_ENDPOINT,
        REQUEST_FORM_LOG_INCLUDE_HTMX,
        REQUEST_FORM_LOG_INCLUDE_VALUES,
        REQUEST_FORM_LOG_MAX_VALUE_LEN,
    )

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


# ── Request-header monitoring (early warning) ────────────────────────────────
_header_monitor_lock = Lock()
_header_monitor = {
    'total_requests': 0,
    'window_large': 0,
    'window': deque(maxlen=HEADER_MONITOR_WINDOW),
}

_SENSITIVE_FORM_KEYS = {
    'password',
    'passphrase',
    'secret',
    'token',
    'access_token',
    'refresh_token',
    'api_key',
    'authorization',
    'csrf_token',
}


def _estimate_request_header_bytes() -> int:
    total = 2  # final CRLF
    for header_name, header_value in request.headers.items():
        total += len(header_name.encode('utf-8', errors='ignore')) + 2
        total += len(header_value.encode('utf-8', errors='ignore')) + 2
    return total


def _truncate_for_log(value: str) -> str:
    if len(value) <= REQUEST_FORM_LOG_MAX_VALUE_LEN:
        return value
    return f"{value[:REQUEST_FORM_LOG_MAX_VALUE_LEN]}..."


def _sanitize_form_for_log(data) -> dict[str, str]:
    """Return form/query data with sensitive values redacted for logging."""
    safe: dict[str, str] = {}
    for key in data.keys():
        values = data.getlist(key)
        key_lower = str(key).strip().lower()
        is_sensitive = key_lower in _SENSITIVE_FORM_KEYS or 'password' in key_lower or 'token' in key_lower
        if is_sensitive:
            safe[key] = '[REDACTED]'
            continue

        if len(values) <= 1:
            safe[key] = _truncate_for_log(str(values[0])) if values else ''
            continue

        truncated_values = [_truncate_for_log(str(v)) for v in values]
        safe[key] = f"[{', '.join(truncated_values)}]"
    return safe


@app.before_request
def _monitor_request_headers_before():
    if HEADER_MONITOR_ENABLED:
        request.environ['header_bytes_estimate'] = _estimate_request_header_bytes()

    if REQUEST_FORM_LOG_ENABLED:
        should_log = request.method == 'POST' or (REQUEST_FORM_LOG_INCLUDE_GET and request.method == 'GET')
        if should_log:
            log_data: dict[str, object] = {
                'method': request.method,
                'path': request.path,
            }
            if REQUEST_FORM_LOG_INCLUDE_ENDPOINT:
                log_data['endpoint'] = request.endpoint
            if REQUEST_FORM_LOG_INCLUDE_HTMX:
                log_data['is_htmx'] = (request.headers.get('HX-Request') or '').lower() == 'true'
            if REQUEST_FORM_LOG_INCLUDE_VALUES:
                payload_source = request.form if request.method == 'POST' else request.args
                log_data['values'] = _sanitize_form_for_log(payload_source)

            app.logger.info('Request log: %s', log_data)

    return None


@app.after_request
def _monitor_request_headers_after(response):
    if not HEADER_MONITOR_ENABLED:
        return response

    header_bytes = int(request.environ.get('header_bytes_estimate', 0))
    if header_bytes <= 0:
        header_bytes = _estimate_request_header_bytes()

    is_large = 1 if header_bytes >= HEADER_SIZE_WARN_BYTES else 0

    with _header_monitor_lock:
        window = _header_monitor['window']
        if len(window) == window.maxlen:
            evicted = window.popleft()
            _header_monitor['window_large'] -= evicted

        window.append(is_large)
        _header_monitor['window_large'] += is_large
        _header_monitor['total_requests'] += 1

        total_requests = _header_monitor['total_requests']
        window_total = len(window)
        window_large = _header_monitor['window_large']
        window_rate_pct = (window_large / window_total * 100.0) if window_total else 0.0
        should_emit_summary = total_requests % HEADER_MONITOR_LOG_EVERY == 0

    if is_large:
        app.logger.warning(
            'Header monitor large-request: bytes=%s warn_bytes=%s method=%s path=%s ip=%s',
            header_bytes,
            HEADER_SIZE_WARN_BYTES,
            request.method,
            request.path,
            request.remote_addr,
        )

    if should_emit_summary:
        log_fn = app.logger.warning if window_rate_pct >= HEADER_WARN_RATE_THRESHOLD_PCT else app.logger.info
        log_fn(
            'Header monitor summary: total=%s window=%s large=%s rate=%.2f%% threshold=%s%% warn_bytes=%s',
            total_requests,
            window_total,
            window_large,
            window_rate_pct,
            HEADER_WARN_RATE_THRESHOLD_PCT,
            HEADER_SIZE_WARN_BYTES,
        )

    return response


def _is_htmx_request() -> bool:
    return (request.headers.get('HX-Request') or '').lower() == 'true'


def _get_error_page_theme():
    try:
        if not current_user.is_authenticated:
            return None
        return UserTheme.get_by_user_id(db, current_user.id)
    except Exception:
        app.logger.exception('Could not load user theme for error page')
        return None


def _error_response(status_code: int, title: str, message: str):
    if _is_htmx_request():
        return app.response_class(f'{title}: {message}\n', status=status_code, mimetype='text/plain')

    return render_template(
        'error.html',
        status_code=status_code,
        title=title,
        message=message,
        user_theme=_get_error_page_theme(),
    ), status_code


@app.errorhandler(400)
def handle_400(_error):
    return _error_response(400, 'Bad Request', 'The request could not be processed.')


@app.errorhandler(403)
def handle_403(_error):
    return _error_response(403, 'Forbidden', 'You do not have permission to access this page.')


@app.errorhandler(404)
def handle_404(_error):
    return _error_response(404, 'Page Not Found', 'The page you requested does not exist.')


@app.errorhandler(431)
def handle_431(_error):
    return _error_response(
        431,
        'Request Headers Too Large',
        'Your browser sent too much header data. Clear site cookies and try again.',
    )


@app.errorhandler(500)
def handle_500(_error):
    return _error_response(500, 'Server Error', 'Something went wrong on our side. Please try again.')

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

# ── Database & auth ───────────────────────────────────────────────────────────
db = GoGetDB()
db.go_create_db()  # ensure tables exist regardless of how the app is started
setup_auth(app, db, limiter)
register_user_theme_routes(app, db)
register_dnd_character_sheet_routes(app, db, limiter)
register_admin_routes(app, db)


# ── Guest helpers ─────────────────────────────────────────────────────────────

def guest_or_login_required(f):
    """Allow authenticated users OR active guest sessions; 403 otherwise."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        if guest.is_guest():
            # Canonicalize to the active guest character id so stale URLs/forms
            # continue to work after guest session schema upgrades.
            guest_character_id = guest.get_guest_character_id()
            character_id = kwargs.get('character_id')
            if character_id and guest_character_id and character_id != guest_character_id:
                kwargs['character_id'] = guest_character_id
            return f(*args, **kwargs)
        abort(403)
    return decorated

def _build_character_sheet_data(character_id: str):
    sheet = CharacterSheet(character_id=character_id)
    data = sheet.create_form()
    BuffProcessor(character_id).transform_out(data)
    return sheet, data


def _build_guest_character_sheet_data(character_id):
    sheet = CharacterSheet(character_id=character_id, guest_character=True)
    data = sheet.create_form()
    return sheet, data


def _normalise_internal_redirect(candidate: str, fallback: str):
    """Allow only local relative redirects to avoid open redirect issues."""
    value = (candidate or '').strip()
    if not value:
        return fallback

    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return fallback
    if not value.startswith('/'):
        return fallback

    return value


register_fragment_routes(
    app,
    db,
    limiter,
    guest_or_login_required,
    _build_character_sheet_data,
    _build_guest_character_sheet_data,
)

@app.route('/', methods=['GET'])
def character_sheet():

    # ── Guest branch (auto-create on first visit) ──────────────────────────
    if not current_user.is_authenticated:
        guest.create_blank()  # no-op if guest session already exists
        character_id = guest.get_guest_character_id()
        if not character_id:
            guest.create_blank()
            character_id = guest.get_guest_character_id()
        sheet, data = _build_guest_character_sheet_data(character_id)
        character_id = sheet.character_id
        is_new_character = not data['character'].get('name')
        guest_name = str(data['character'].get('name') or '').strip()
        landing_requested = (request.args.get('landing') or '').strip() == '1'

        # Landing panel is visible for first-time guests, or when a named guest
        # explicitly returns to landing mode via the navbar title.
        show_guest_landing_panel = is_new_character or (landing_requested and bool(guest_name))
        show_guest_name_entry = is_new_character
        guest_show_sheet = not (landing_requested and bool(guest_name))

        return render_template(
            'index.html',
            characters=[],
            active_character_id=character_id,
            at_character_limit=True,
            is_new_character=is_new_character,
            is_guest=True,
            character_id=character_id,
            character=data['character'],
            classes=data['classes'],
            class_options=data['class_options'],
            abilities=data['abilities'],
            feats_and_traits=data['feats_and_traits'],
            feats_and_traits_at_capacity=data['feats_and_traits_at_capacity'],
            inventory=data['inventory'],
            inventory_at_capacity=data['inventory_at_capacity'],
            custom_stats=data['custom_stats'],
            custom_stats_at_capacity=data['custom_stats_at_capacity'],
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            trackers=[],
            show_guest_landing_panel=show_guest_landing_panel,
            show_guest_name_entry=show_guest_name_entry,
            guest_show_sheet=guest_show_sheet,
            guest_character_name=guest_name,
        )

    characters = User.get_characters(db, current_user.id)
    at_character_limit = User.at_character_limit(db, current_user.id)
    user_theme = UserTheme.get_by_user_id(db, current_user.id)
    character_id = request.args.get('character_id')

    # If no character_id specified, default to first owned character
    if not character_id and characters:
        character_id = characters[0]['id']

    # Verify ownership
    if character_id and not User.owns_character(db, current_user.id, character_id):
        abort(403)

    active_character_id = character_id

    # ── Unsaved new character (no DB row yet) ──────────────────────────────
    if request.args.get('new') == 'true':
        blank_character = {
            'id': None, 'name': None, 'level': 0,
            'race': None, 'background': None, 'alignment': None,
            'armour_class': None, 'initiative': None, 'speed': None,
            'proficiency': None, 'passive_wisdom': None, 'xp': None,
            'health_points': None, 'hit_dice': None,
            'temporary_hit_points': None,
        }
        return render_template(
            'index.html',
            characters=characters,
            active_character_id=None,
            at_character_limit=at_character_limit,
            is_new_character=True,
            is_unsaved=True,
            is_guest=False,
            character_id=None,
            character=blank_character,
            classes=[],
            class_options=[],
            abilities=[],
            feats_and_traits=[],
            feats_and_traits_at_capacity=False,
            inventory=[],
            inventory_at_capacity=False,
            custom_stats=[],
            custom_stats_at_capacity=False,
            custom_buffs=[],
            custom_buffs_at_capacity=False,
            buff_target_options={},
            trackers=[],
            user_theme=user_theme,
        )

    if not character_id:
        return render_template(
            'index.html',
            characters=characters,
            active_character_id=active_character_id,
            at_character_limit=at_character_limit,
            is_guest=False,
            character=None,
            trackers=[],
            user_theme=user_theme,
        )

    _, character_sheet_data = _build_character_sheet_data(character_id)
    trackers = get_trackers_for_character(db, character_id)

    # Detect if this is a brand-new character (no name set yet)
    is_new_character = not character_sheet_data['character'].get('name')

    return render_template(
        'index.html',
        characters=characters,
        active_character_id=active_character_id,
        at_character_limit=at_character_limit,
        is_new_character=is_new_character,
        is_guest=False,
        character_id=character_id,
        character=character_sheet_data['character'],
        classes=character_sheet_data['classes'],
        class_options=character_sheet_data['class_options'],
        abilities=character_sheet_data['abilities'],
        feats_and_traits=character_sheet_data['feats_and_traits'],
        feats_and_traits_at_capacity=character_sheet_data['feats_and_traits_at_capacity'],
        inventory=character_sheet_data['inventory'],
        inventory_at_capacity=character_sheet_data['inventory_at_capacity'],
        custom_stats=character_sheet_data['custom_stats'],
        custom_stats_at_capacity=character_sheet_data['custom_stats_at_capacity'],
        custom_buffs=character_sheet_data['custom_buffs'],
        custom_buffs_at_capacity=character_sheet_data['custom_buffs_at_capacity'],
        buff_target_options=character_sheet_data['buff_target_options'],
        trackers=trackers,
        trackers_at_capacity=len(trackers) >= TRACKER_MAX,
        tracker_max=TRACKER_MAX,
        tracker_entry_max=TRACKER_ENTRY_MAX,
        user_theme=user_theme,
    )


if __name__ == '__main__':
    # Create the database
    db.go_create_db()
    # Sync the database schema
    db.go_sync_schema()
    # Seed the database
    db.go_seed_db()
    # Run the Flask app on port 8888
    app.run(host='0.0.0.0', port=8888, debug=DEBUG)
