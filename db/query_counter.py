"""Dev-only DB round-trip counter, gated behind QUERY_DEBUG.

Patches the go_get_it backend classes (not a single db instance) since the app
creates several independent GoGetDB() instances (character_sheet, guest_character,
custom_buff, app.py's own db) that all share the same underlying pooled connection
for Postgres but are otherwise separate objects — instance-level patching would
undercount whichever instances it missed.
"""
import functools

from flask import g, request

from go_get_it.go_get_it import SQLiteGoGetDB

try:
    from go_get_it.pg_backend import PostgreSQLGoGetDB
except ImportError:
    PostgreSQLGoGetDB = None

_INSTRUMENTED_METHODS = ('go_get_one', 'go_get_all', 'go_add_new', 'go_update', 'go_delete_it')


def _instrument(cls):
    for method_name in _INSTRUMENTED_METHODS:
        original = getattr(cls, method_name, None)
        if original is None or getattr(original, '_query_counted', False):
            continue

        @functools.wraps(original)
        def wrapper(self, *args, _orig=original, **kwargs):
            if hasattr(g, 'query_count'):
                g.query_count += 1
            return _orig(self, *args, **kwargs)

        wrapper._query_counted = True
        setattr(cls, method_name, wrapper)


def register_query_counting(app):
    _instrument(SQLiteGoGetDB)
    if PostgreSQLGoGetDB is not None:
        _instrument(PostgreSQLGoGetDB)

    @app.before_request
    def _reset_query_count():
        g.query_count = 0

    @app.after_request
    def _log_query_count(response):
        count = getattr(g, 'query_count', None)
        if count is not None:
            app.logger.info('Query count: %s %s -> %s queries', request.method, request.path, count)
        return response
