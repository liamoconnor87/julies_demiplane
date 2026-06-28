import os

from werkzeug.security import generate_password_hash


def _build_admin_seed():
    """Build optional admin seed from env vars.

    Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` to enable auto-seeding.
    If either is missing, no admin row is seeded.
    """
    username = (os.environ.get('ADMIN_USERNAME') or '').strip()
    password = os.environ.get('ADMIN_PASSWORD') or ''
    if not username or not password:
        return {}

    admin_user_id = (os.environ.get('ADMIN_USER_ID') or '').strip() or "019cce6214f366933d7a328ced71df53"
    created_at = (os.environ.get('ADMIN_CREATED_AT') or '').strip() or "2024-06-01T00:00:00+00:00"

    return {
        "user": [
            {
                admin_user_id: "id",
                username: "username",
                generate_password_hash(password): "password_hash",
                created_at: "created_at",
                1: "admin",
            }
        ],
    }


ADMIN_SEED = _build_admin_seed()