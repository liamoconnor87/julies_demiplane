from collections import deque
import logging
from threading import Lock

from flask import request

from db.config import (
    HEADER_MONITOR_ENABLED,
    HEADER_MONITOR_LOG_EVERY,
    HEADER_MONITOR_WINDOW,
    HEADER_SIZE_WARN_BYTES,
    HEADER_WARN_RATE_THRESHOLD_PCT,
    REQUEST_FORM_LOG_ENABLED,
    REQUEST_FORM_LOG_INCLUDE_GET,
    REQUEST_FORM_LOG_INCLUDE_ENDPOINT,
    REQUEST_FORM_LOG_INCLUDE_HTMX,
    REQUEST_FORM_LOG_INCLUDE_VALUES,
    REQUEST_FORM_LOG_MAX_VALUE_LEN,
)

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


def _sanitize_form_for_log(data) -> dict:
    safe: dict = {}
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


def register_monitoring(app):
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

    @app.before_request
    def _monitor_request_headers_before():
        if HEADER_MONITOR_ENABLED:
            request.environ['header_bytes_estimate'] = _estimate_request_header_bytes()

        if REQUEST_FORM_LOG_ENABLED:
            should_log = request.method == 'POST' or (REQUEST_FORM_LOG_INCLUDE_GET and request.method == 'GET')
            if should_log:
                log_data: dict = {
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
