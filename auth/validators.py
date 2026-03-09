"""
Pure validation helpers for auth forms.
Each returns (is_valid: bool, error_message: str | None).
"""
import re

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]+$')


def validate_username(value: str):
    value = (value or '').strip()
    if len(value) < 3:
        return False, 'Username must be at least 3 characters.'
    if len(value) > 30:
        return False, 'Username must be 30 characters or fewer.'
    if not _USERNAME_RE.match(value):
        return False, 'Username may only contain letters, numbers, and underscores.'
    return True, None


def validate_password(value: str):
    if len(value or '') < 8:
        return False, 'Password must be at least 8 characters.'
    return True, None


def validate_passwords_match(password: str, confirm: str):
    if password != confirm:
        return False, 'Passwords do not match.'
    return True, None
