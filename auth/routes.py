from flask import Blueprint, abort, current_app, make_response, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from typing import Optional

from auth.models import User
from auth.validators import validate_username, validate_password, validate_passwords_match
from character_sheet import guest_character as guest

auth_bp = Blueprint('auth', __name__)

_MASQUERADE_ADMIN_ID_KEY = 'masquerade_admin_id'
_MASQUERADE_ADMIN_USERNAME_KEY = 'masquerade_admin_username'


def _get_db():
    return current_app.config['AUTH_DB']


def _clear_masquerade_session():
    session.pop(_MASQUERADE_ADMIN_ID_KEY, None)
    session.pop(_MASQUERADE_ADMIN_USERNAME_KEY, None)


def _auth_error_response(error: Optional[str], active_tab: str = 'login'):
    """
    Return the auth dropdown fragment with an error message.
    The dropdown stays open so the user sees what went wrong.
    """
    return render_template(
        'components/auth/auth_dropdown.html',
        auth_error=error,
        active_tab=active_tab,
    )


def _redirect(url: str = '/'):
    """Redirect for both HTMX and standard form submits."""
    if (request.headers.get('HX-Request') or '').lower() != 'true':
        return redirect(url)

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
    if not user:
        return _auth_error_response('Username is already taken.', active_tab='signup')
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
    _clear_masquerade_session()
    logout_user()
    return _redirect('/')


@auth_bp.route('/masquerade/start/<user_id>', methods=['POST'])
@login_required
def start_masquerade(user_id: str):
    db = _get_db()

    if not current_user.is_admin:
        abort(403)

    if session.get(_MASQUERADE_ADMIN_ID_KEY):
        abort(400)

    if current_user.id == user_id:
        return _redirect(url_for('admin_home'))

    target_user = User.get_by_id(db, user_id)
    if not target_user:
        abort(404)

    session[_MASQUERADE_ADMIN_ID_KEY] = current_user.id
    session[_MASQUERADE_ADMIN_USERNAME_KEY] = current_user.username
    login_user(target_user)

    return _redirect(url_for('character_sheet'))


@auth_bp.route('/masquerade/stop', methods=['POST'])
@login_required
def stop_masquerade():
    db = _get_db()
    admin_user_id = session.get(_MASQUERADE_ADMIN_ID_KEY)
    _clear_masquerade_session()

    if not admin_user_id:
        return _redirect(url_for('character_sheet'))

    admin_user = User.get_by_id(db, admin_user_id)
    if not admin_user or not admin_user.is_admin:
        logout_user()
        return _redirect(url_for('character_sheet'))

    login_user(admin_user)
    return _redirect(url_for('admin_home'))
