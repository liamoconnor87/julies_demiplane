from functools import wraps
from urllib.parse import urlparse

from flask import abort, request
from flask_login import current_user

from demiplane.services.character_sheet import CharacterSheet
from demiplane.services.custom_buff import BuffProcessor
from demiplane.services import guest_character as guest


def guest_or_login_required(f):
    """Allow authenticated users OR active guest sessions; 403 otherwise."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        if guest.is_guest():
            # Canonicalize to the active guest character id so stale URLs/forms
            # continue to work after guest session schema upgrades.
            guest_character_id = guest.get_guest_character_id()
            character_id = kwargs.get('character_id')
            if character_id and guest_character_id and character_id != guest_character_id:
                kwargs['character_id'] = guest_character_id
            return f(*args, **kwargs)
        abort(403)
    return decorated


def build_character_sheet_data(character_id: str):
    sheet = CharacterSheet(character_id=character_id)
    data = sheet.create_form()
    BuffProcessor(character_id).transform_out(data)
    return sheet, data


def build_guest_character_sheet_data(character_id):
    sheet = CharacterSheet(character_id=character_id, guest_character=True)
    data = sheet.create_form()
    return sheet, data


def normalise_internal_redirect(candidate: str, fallback: str):
    """Allow only local relative redirects to avoid open redirect issues."""
    value = (candidate or '').strip()
    if not value:
        return fallback
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return fallback
    if not value.startswith('/'):
        return fallback
    return value


def is_htmx_request() -> bool:
    return (request.headers.get('HX-Request') or '').lower() == 'true'
