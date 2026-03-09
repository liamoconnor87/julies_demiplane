from flask import Blueprint, current_app, make_response, render_template, request
from flask_login import login_user, logout_user

from typing import Optional

from auth.models import User
from auth.validators import validate_username, validate_password, validate_passwords_match

auth_bp = Blueprint('auth', __name__)


def _get_db():
    return current_app.config['AUTH_DB']


def _auth_error_response(error: Optional[str], active_tab: str = 'login'):
    """
    Return the auth dropdown fragment with an error message.
    The dropdown stays open so the user sees what went wrong.
    """
    return render_template(
        'components/auth_dropdown.html',
        auth_error=error,
        active_tab=active_tab,
    )


def _redirect(url: str = '/'):
    """Return an empty response with HX-Redirect so HTMX does a full page load."""
    resp = make_response('', 200)
    resp.headers['HX-Redirect'] = url
    return resp


@auth_bp.route('/signup', methods=['POST'])
def signup():
    db = _get_db()
    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    confirm = request.form.get('confirm_password') or ''

    # Validate
    ok, err = validate_username(username)
    if not ok:
        return _auth_error_response(err, active_tab='signup')

    ok, err = validate_password(password)
    if not ok:
        return _auth_error_response(err, active_tab='signup')

    ok, err = validate_passwords_match(password, confirm)
    if not ok:
        return _auth_error_response(err, active_tab='signup')

    # Check uniqueness
    if User.get_by_username(db, username):
        return _auth_error_response('Username is already taken.', active_tab='signup')

    # Create and log in
    user = User.create(db, username, password)
    login_user(user)
    return _redirect('/')


@auth_bp.route('/login', methods=['POST'])
def login():
    db = _get_db()
    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''

    user = User.verify_password(db, username, password)
    if not user:
        return _auth_error_response('Invalid username or password.')

    login_user(user)

    # Redirect to first character if user has any
    characters = User.get_characters(db, user.id)
    if characters:
        return _redirect(f'/?character_id={characters[0]["id"]}')
    return _redirect('/')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return _redirect('/')
