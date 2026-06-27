from flask import render_template
from flask_login import current_user

from auth.models import UserTheme
from routes.helpers import is_htmx_request


def register_error_handlers(app, db):
    def _get_error_page_theme():
        try:
            if not current_user.is_authenticated:
                return None
            return UserTheme.get_by_user_id(db, current_user.id)
        except Exception:
            app.logger.exception('Could not load user theme for error page')
            return None

    def _error_response(status_code: int, title: str, message: str):
        if is_htmx_request():
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
