import os


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).lower() in ('true', '1', 'yes', 'on')

secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    raise RuntimeError('SECRET_KEY environment variable must be set')
DEBUG = os.environ.get('DEBUG', 'false').lower() in ('true', '1', 'yes')
DB_ROUTE = os.environ.get('DB_ROUTE', '/app/db/data/demiplane.db')
DATABASE_URL = os.environ.get('DATABASE_URL')
SESSION_COOKIE_NAME = os.environ.get('SESSION_COOKIE_NAME', 'julies_demiplane_session')
SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', not DEBUG)
SESSION_FILE_DIR = os.environ.get('SESSION_FILE_DIR', './flask_session')
SESSION_LIFETIME_DAYS = _env_int('SESSION_LIFETIME_DAYS', 30)
SESSION_FILE_THRESHOLD = _env_int('SESSION_FILE_THRESHOLD', 2000)
RATE_LIMIT_STORAGE_URI = os.environ.get('RATE_LIMIT_STORAGE_URI', 'memory://')
FORCE_HTTPS = _env_bool('FORCE_HTTPS', not DEBUG)
HEADER_MONITOR_ENABLED = _env_bool('HEADER_MONITOR_ENABLED', True)
HEADER_SIZE_WARN_BYTES = max(1024, _env_int('HEADER_SIZE_WARN_BYTES', 12288))
HEADER_WARN_RATE_THRESHOLD_PCT = max(1, _env_int('HEADER_WARN_RATE_THRESHOLD_PCT', 2))
HEADER_MONITOR_WINDOW = max(20, _env_int('HEADER_MONITOR_WINDOW', 200))
HEADER_MONITOR_LOG_EVERY = max(10, _env_int('HEADER_MONITOR_LOG_EVERY', 100))
REQUEST_FORM_LOG_ENABLED = _env_bool('REQUEST_FORM_LOG_ENABLED', DEBUG)
REQUEST_FORM_LOG_INCLUDE_GET = _env_bool('REQUEST_FORM_LOG_INCLUDE_GET', DEBUG)
REQUEST_FORM_LOG_INCLUDE_ENDPOINT = _env_bool('REQUEST_FORM_LOG_INCLUDE_ENDPOINT', False)
REQUEST_FORM_LOG_INCLUDE_HTMX = _env_bool('REQUEST_FORM_LOG_INCLUDE_HTMX', False)
REQUEST_FORM_LOG_INCLUDE_VALUES = _env_bool('REQUEST_FORM_LOG_INCLUDE_VALUES', False)
REQUEST_FORM_LOG_MAX_VALUE_LEN = max(16, _env_int('REQUEST_FORM_LOG_MAX_VALUE_LEN', 160))
