"""
Pure validation helpers for auth forms.
Each returns (is_valid: bool, error_message: str | None).
"""
import re

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]+$')

# Matches: #rgb, #rrggbb, #rrggbbaa, rgb(...), rgba(...), hsl(...), hsla(...),
# and plain CSS named colours (letters only).  Rejects semicolons, braces, and
# any other characters that could break out of a CSS value context.
_CSS_HEX_RE = re.compile(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')
_CSS_FUNC_RE = re.compile(
    r'^(rgba?|hsla?)\(\s*[\d.]+%?\s*,\s*[\d.]+%?\s*,\s*[\d.]+%?(\s*,\s*[\d.]+%?)?\s*\)$'
)
_CSS_NAMED_RE = re.compile(r'^[a-zA-Z]+$')


def is_valid_css_colour(value: str) -> bool:
    """Return True if value is a safe, well-formed CSS colour string."""
    if not value or len(value) > 80:
        return False
    v = value.strip()
    return bool(
        _CSS_HEX_RE.match(v) or
        _CSS_FUNC_RE.match(v) or
        _CSS_NAMED_RE.match(v)
    )


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

def generate_captcha_image(challenge: str):
    """
    Generate the base64 encoded captcha image
    """
    import base64

    from captcha.image import ImageCaptcha

    image = ImageCaptcha(width=240, height=50)

    data = image.generate(challenge)
    return base64.b64encode(data.getvalue()).decode("utf-8")