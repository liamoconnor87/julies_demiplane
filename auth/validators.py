"""
Pure validation helpers for auth forms.
Each returns (is_valid: bool, error_message: str | None).
"""
import re

from go_get_it.go_get_it import GoGetDB

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]+$')


def validate_username(value: str):
    value = (value or '').strip()
    if len(value) < 3:
        return False, 'Username must be at least 3 characters.'
    if len(value) > 30:
        return False, 'Username must be 30 characters or fewer.'
    if not _USERNAME_RE.match(value):
        return False, 'Username may only contain letters, numbers, and underscores.'

    ggi = GoGetDB()
    all_users = ggi.go_get_all('users')
    if all_users and any(user['username'].lower() == value.lower() for user in all_users):
        return False, 'Username is already taken.'
    return True, None


def validate_password(value: str):
    if len(value or '') < 8:
        return False, 'Password must be at least 8 characters.'
    return True, None


def validate_passwords_match(password: str, confirm: str):
    if password != confirm:
        return False, 'Passwords do not match.'
    return True, None

def generate_captcha_image(challenge: str):
    """
    Generate the base64 encoded captcha image
    """
    import base64

    from captcha.image import ImageCaptcha

    image = ImageCaptcha(width=240, height=50)

    data = image.generate(challenge)
    return base64.b64encode(data.getvalue()).decode("utf-8")