from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from auth.models import UserTheme
from auth.validators import is_valid_css_colour


def register_user_theme_routes(app, db):
    user_theme_bp = Blueprint('user_theme_routes', __name__)

    @user_theme_bp.route('/user/theme/save', methods=['POST'])
    @login_required
    def save_user_theme():
        """Persist the user's colour theme and return an OOB style block update."""
        colour_fields = UserTheme.COLOUR_FIELDS
        colours = {}
        for field in colour_fields:
            value = (request.form.get(field) or '').strip()
            if not is_valid_css_colour(value):
                abort(400)
            colours[field] = value

        UserTheme.save(db, current_user.id, colours)
        return render_template('components/theme_vars_oob.html', colours=colours), 200

    app.register_blueprint(user_theme_bp)
