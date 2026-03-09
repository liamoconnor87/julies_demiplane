from flask import Flask, redirect, url_for
from flask_login import LoginManager

from auth.models import User
from auth.routes import auth_bp


def setup_auth(app: Flask, db):
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
