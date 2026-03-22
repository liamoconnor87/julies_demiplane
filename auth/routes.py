from flask import Blueprint, current_app, make_response, render_template, request, session
from flask_login import login_user, logout_user

from typing import Optional

from auth.models import User
from auth.validators import validate_username, validate_password, validate_passwords_match
from character_sheet import guest_character as guest

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

    # Validate CAPTCHA
    captcha_input = (request.form.get('captcha') or '').strip().upper()
    expected = (session.pop('captcha_answer', '') or '').upper()
    if not captcha_input or captcha_input != expected:
        return _auth_error_response('CAPTCHA is incorrect.', active_tab='signup')

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

    # Migrate guest character to the new user account
    migrated_character_id = guest.persist_guest_to_db(db, user.id)
    if migrated_character_id:
        return _redirect(f'/?character_id={migrated_character_id}')

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

    # Discard any guest data when logging in to an existing account
    guest.clear_guest()

    # Redirect to first character if user has any
    characters = User.get_characters(db, user.id)
    if characters:
        return _redirect(f'/?character_id={characters[0]["id"]}')
    return _redirect('/')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return _redirect('/')
