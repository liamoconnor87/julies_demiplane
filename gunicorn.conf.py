import os


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


bind = os.getenv('GUNICORN_BIND', '0.0.0.0:8888')
workers = _int_env('GUNICORN_WORKERS', 2)
threads = _int_env('GUNICORN_THREADS', 4)

# Default Gunicorn header field size is 8190 bytes. Increase this to reduce
# rejections when clients/proxies send large Cookie or forwarded-* headers.
limit_request_field_size = _int_env('GUNICORN_LIMIT_REQUEST_FIELD_SIZE', 16384)
limit_request_fields = _int_env('GUNICORN_LIMIT_REQUEST_FIELDS', 100)


def when_ready(server):
    server.log.info(
        'Gunicorn header limits active: limit_request_field_size=%s, limit_request_fields=%s',
        limit_request_field_size,
        limit_request_fields,
    )
