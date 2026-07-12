from datetime import datetime, timezone
import sqlite3
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from demiplane.functions.functions import uuid


class User(UserMixin):
    """Lightweight user model backed by the GoGetDB 'user' table."""

    MAX_CHARACTERS = 10

    def __init__(self, id: str, username: str, is_admin: bool = False):
        self.id = id
        self.username = username
        self.is_admin = is_admin

    # ── Lookup helpers ────────────────────────────────────────────────────

    @staticmethod
    def get_by_id(db, user_id: str):
        row = db.go_get_one('user', {'id': user_id})
        if row:
            return User(id=row['id'], username=row['username'], is_admin=bool(row.get('admin')))
        return None

    @staticmethod
    def get_by_username(db, username: str):
        row = db.go_get_one('user', {'username': username})
        if row:
            return User(id=row['id'], username=row['username'], is_admin=bool(row.get('admin')))
        return None

    # ── Mutation helpers ──────────────────────────────────────────────────

    @staticmethod
    def create(db, username: str, password: str):
        """Hash the password, insert a new user row, return the User."""
        user_id = uuid()
        try:
            db.go_add_new('user', {
                'id': user_id,
                'username': username,
                'password_hash': generate_password_hash(password),
                'created_at': datetime.now(timezone.utc).isoformat(),
            })
        except sqlite3.IntegrityError:
            return None
        return User(id=user_id, username=username)

    @staticmethod
    def verify_password(db, username: str, password: str):
        """Return a User if credentials are valid, else None."""
        row = db.go_get_one('user', {'username': username})
        if row and check_password_hash(row['password_hash'], password):
            return User(id=row['id'], username=row['username'], is_admin=bool(row.get('admin')))
        return None

    # ── Character helpers ─────────────────────────────────────────────────

    @staticmethod
    def get_characters(db, user_id: str):
        """Return list of {'id': ..., 'name': ...} for this user's characters."""
        links = db.go_get_all('user_to_character', {'user_id': user_id}) or []
        characters = []
        for link in links:
            char = db.go_get_one('character', {'id': link['character_id']})
            if char:
                characters.append({
                    'id': char['id'],
                    'name': char.get('name') or 'Unnamed',
                })
        return characters

    @staticmethod
    def owns_character(db, user_id: str, character_id: str) -> bool:
        """Return True if user_to_character link exists."""
        link = db.go_get_one('user_to_character', {
            'user_id': user_id,
            'character_id': character_id,
        })
        return link is not None

    @staticmethod
    def character_count(db, user_id: str) -> int:
        """Return the number of characters owned by this user."""
        return db.go_get_all('user_to_character', {'user_id': user_id}, count=True) or 0

    @staticmethod
    def at_character_limit(db, user_id: str) -> bool:
        """Return True if user has reached MAX_CHARACTERS."""
        return User.character_count(db, user_id) >= User.MAX_CHARACTERS

    @staticmethod
    def delete_character(db, user_id: str, character_id: str):
        """Delete a character and ALL related data (except user table).

        Tables with a direct character_id column are purged first,
        then ability-skill tables (which reference via <ability>_id),
        and finally the character row itself.
        """
        # Tables with a direct character_id foreign key
        direct_tables = [
            'inventory', 'class_to_character', 'feat_and_trait',
            'custom_stat', 'custom_buff', 'custom_buff_to_stat_table',
            'stat_table_to_stat', 'user_to_character',
        ]
        for table in direct_tables:
            db.go_delete_by(table, {'character_id': character_id})

        # Ability tables + their linked skill tables
        ability_skill_pairs = [
            ('strength', 'strength_skills', 'strength_id'),
            ('dexterity', 'dexterity_skills', 'dexterity_id'),
            ('constitution', 'constitution_skills', 'constitution_id'),
            ('intelligence', 'intelligence_skills', 'intelligence_id'),
            ('wisdom', 'wisdom_skills', 'wisdom_id'),
            ('charisma', 'charisma_skills', 'charisma_id'),
        ]
        for ability_table, skill_table, fk_col in ability_skill_pairs:
            ability_rows = db.go_get_all(ability_table, {'character_id': character_id}) or []
            for row in ability_rows:
                db.go_delete_by(skill_table, {fk_col: row['id']})
            db.go_delete_by(ability_table, {'character_id': character_id})

        # Finally, delete the character row
        db.go_delete_it('character', {'id': character_id})


# ── Default colour values ─────────────────────────────────────────────────────

THEME_DEFAULTS = {
    'background_colour':  '#b8a8cd',
    'border_colour':      'rgb(0, 189, 91)',
    'label_colour':       'rgb(255, 255, 255)',
    'critical_colour':    'rgb(220, 50, 50)',
    'success_colour':     'rgb(0, 189, 91)',
    'tracker_fill_colour': 'rgb(0, 153, 74)',
    'asterisk_colour':    'rgb(255, 0, 234)',
    'field_text_colour':  'rgb(255, 255, 255)',
    'level_colour':       'rgb(255, 0, 234)',
    'button_icon_colour': 'rgb(255, 255, 255)',
    'title_colour':       'rgb(0, 0, 0)',
    'field_bg_colour':    'rgba(0, 0, 0, 0.85)',
}


class UserTheme:
    """Per-user colour theme backed by the 'user_theme' table."""

    COLOUR_FIELDS = list(THEME_DEFAULTS.keys())

    @staticmethod
    def get_by_user_id(db, user_id: str):
        """Return the theme row dict for this user, or None if not set."""
        return db.go_get_one('user_theme', {'user_id': user_id})

    @staticmethod
    def save(db, user_id: str, colours: dict):
        """Upsert the theme for this user."""
        existing = db.go_get_one('user_theme', {'user_id': user_id})
        if existing:
            row = {'id': existing['id'], 'user_id': user_id}
            row.update(colours)
            db.go_update('user_theme', row)
        else:
            row = {'id': uuid(), 'user_id': user_id}
            row.update(colours)
            db.go_add_new('user_theme', row)
