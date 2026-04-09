import secrets
import string

from flask import Flask, redirect, session, url_for
from flask_login import LoginManager, current_user

from auth.models import User
from auth.routes import auth_bp
from auth.validators import generate_captcha_image


def setup_auth(app: Flask, db, limiter=None):
    """
    Wire authentication into the Flask app.
    Call once after app and db are created.
    """
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.get_by_id(db, user_id)

    @login_manager.unauthorized_handler
    def unauthorized():
        """Redirect to home page when not authenticated."""
        return redirect(url_for('character_sheet'))

    # Make db available to the blueprint via app config
    app.config['AUTH_DB'] = db

    app.register_blueprint(auth_bp)

    @app.context_processor
    def inject_captcha():
        """Provide a stable CAPTCHA image for unauthenticated signup forms."""
        if current_user.is_authenticated:
            return {}

        # Keep the same challenge for the current session until it is consumed
        # by signup. This prevents unrelated fragment renders from invalidating
        # the value the user sees in the dropdown.
        challenge = session.get('captcha_answer')
        if not challenge:
            challenge = ''.join(
                secrets.choice(string.ascii_uppercase + string.digits)
                for _ in range(5)
            )
            session['captcha_answer'] = challenge

        return {'captcha_image': generate_captcha_image(challenge)}

    # Apply rate limits to auth endpoints if limiter is available
    if limiter:
        limiter.limit('10/minute')(app.view_functions['auth.signup'])
        limiter.limit('10/minute')(app.view_functions['auth.login'])
