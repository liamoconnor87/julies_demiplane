"""
Input validation helpers for form data submitted to the character sheet.
All functions are pure – they accept a raw value and return a safe, typed result.
"""
import re
from typing import Optional

# Matches the 32-char hex UUIDs produced by functions.uuid()
_UUID_RE = re.compile(r'^[0-9a-f]{32}$', re.IGNORECASE)

# Matches any HTML/script tag, e.g. <script>, </div>, <img onerror=...>
_HTML_TAG_RE = re.compile(r'<[^>]*>', re.IGNORECASE)

# ── String helpers ────────────────────────────────────────────────────────────

def strip_html(value: str) -> str:
    """
    Remove all HTML/XML tags from a string.
    This is a lightweight defence-in-depth measure against stored XSS;
    Jinja2 auto-escaping is the primary output-side protection.
    """
    return _HTML_TAG_RE.sub('', value)


def sanitize_str(value, max_len: int = 255) -> str:
    """
    Strip surrounding whitespace, remove HTML tags, and truncate to
    `max_len` characters.  Returns an empty string for None / non-string input.
    """
    if value is None:
        return ''
    text = strip_html(str(value).strip())
    return text[:max_len]


def sanitize_optional_str(value, max_len: int = 255) -> Optional[str]:
    """Same as sanitize_str but returns None when the result is empty."""
    result = sanitize_str(value, max_len)
    return result if result else None


# ── Integer helpers ───────────────────────────────────────────────────────────

def parse_int(value, fallback: int = 0) -> int:
    """Parse value as int, returning `fallback` on failure."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return fallback


def clamp_int(value, min_val: int, max_val: int, fallback: int = 0) -> int:
    """Parse value as int and clamp it to [min_val, max_val]."""
    parsed = parse_int(value, fallback)
    return max(min_val, min(max_val, parsed))


def parse_optional_int(value, fallback=None) -> Optional[int]:
    """
    Parse value as int. Returns `fallback` when value is None/blank.
    Returns 0 (not fallback) when parsing a non-blank value fails.
    """
    if value is None or str(value).strip() == '':
        return fallback
    return parse_int(value, 0)


# ── UUID helpers ──────────────────────────────────────────────────────────────

def is_valid_uuid(value) -> bool:
    """Return True only for non-empty 32-char hex strings (app's UUID format)."""
    if not value:
        return False
    return bool(_UUID_RE.match(str(value).strip()))
