"""Guest-session helpers and storage adapter.

Guest character data lives in server-side session storage under a table-like
schema so CharacterSheet can use the same save/read contract for guest and
authenticated flows.
"""

from typing import Dict, Optional

from flask import session

from demiplane.functions.functions import uuid
from demiplane.functions.validators import clamp_int, is_valid_uuid, parse_optional_int, sanitize_optional_str
from go_get_it.go_get_it import GoGetDB

ggi = GoGetDB()

_SESSION_KEY = 'guest_character'
_SCHEMA_VERSION = 2

ABILITY_TO_SKILL_MAPPING = {
    'strength': ['athletics'],
    'dexterity': ['acrobatics', 'sleight_of_hand', 'stealth'],
    'constitution': [],
    'intelligence': ['arcana', 'history', 'investigation', 'nature', 'religion'],
    'wisdom': ['animal_handling', 'insight', 'medicine', 'perception', 'survival'],
    'charisma': ['deception', 'intimidation', 'performance', 'persuasion'],
}

_ABILITY_TABLES = tuple(ABILITY_TO_SKILL_MAPPING.keys())
_SKILL_TABLES = tuple(f'{ability}_skills' for ability in _ABILITY_TABLES)

_TABLES = (
    'character',
    'class_to_character',
    'feat_and_trait',
    'custom_stat',
    'inventory',
    'custom_buff',
    'custom_buff_to_stat_table',
    'stat_table_to_stat',
    *_ABILITY_TABLES,
    *_SKILL_TABLES,
)

_CHARACTER_BOUND_TABLES = {
    'class_to_character',
    'feat_and_trait',
    'custom_stat',
    'inventory',
    'custom_buff',
    'custom_buff_to_stat_table',
    'stat_table_to_stat',
    *_ABILITY_TABLES,
}


def _mark_modified() -> None:
    session.modified = True


def _coerce_character_id(value) -> str:
    if is_valid_uuid(value):
        return str(value)
    return uuid()


def _default_character_row(character_id: str) -> dict:
    return {
        'id': character_id,
        'name': None,
        'level': 0,
        'race': None,
        'background': None,
        'alignment': None,
        'armour_class': None,
        'initiative': None,
        'speed': None,
        'proficiency': None,
        'passive_wisdom': None,
        'xp': None,
        'health_points': None,
        'hit_dice': None,
        'temporary_hit_points': None,
    }


def _blank_ability_rows(ability_name: str, character_id: str) -> tuple[dict, dict]:
    ability_id = uuid()
    skill_table = {
        'id': uuid(),
        f'{ability_name}_id': ability_id,
        'saving_throw': 0,
    }
    for skill in ABILITY_TO_SKILL_MAPPING[ability_name]:
        skill_table[skill] = 0
        skill_table[f'{skill}_proficient'] = 0

    ability_table = {
        'id': ability_id,
        'character_id': character_id,
        'value': 10,
        'modifier': 0,
        'proficient': 0,
    }

    return ability_table, skill_table


def _build_blank_payload(character_id: str) -> dict:
    tables = {table_name: [] for table_name in _TABLES}
    tables['character'] = [_default_character_row(character_id)]

    for ability_name in _ABILITY_TABLES:
        ability_row, skills_row = _blank_ability_rows(ability_name, character_id)
        tables[ability_name] = [ability_row]
        tables[f'{ability_name}_skills'] = [skills_row]

    return {
        'schema_version': _SCHEMA_VERSION,
        'character_id': character_id,
        'tables': tables,
    }


def _normalise_table_rows(rows) -> list:
    if not isinstance(rows, list):
        return []
    normalised = []
    for row in rows:
        if isinstance(row, dict):
            normalised.append(dict(row))
    return normalised


def _normalise_new_payload(payload: dict) -> tuple[dict, bool]:
    changed = False
    raw_character_id = payload.get('character_id')
    character_id = _coerce_character_id(raw_character_id)
    if not is_valid_uuid(raw_character_id):
        changed = True
        character_row = None
        tables = payload.get('tables')
        if isinstance(tables, dict):
            character_rows = tables.get('character')
            if isinstance(character_rows, list) and character_rows and isinstance(character_rows[0], dict):
                character_row = character_rows[0]
        candidate = character_row.get('id') if isinstance(character_row, dict) else None
        character_id = _coerce_character_id(candidate)

    incoming_tables = payload.get('tables')
    if not isinstance(incoming_tables, dict):
        return _build_blank_payload(character_id), True

    tables = {table_name: _normalise_table_rows(incoming_tables.get(table_name, [])) for table_name in _TABLES}

    if not tables['character']:
        tables['character'] = [_default_character_row(character_id)]
        changed = True

    character_row = tables['character'][0]
    defaults = _default_character_row(character_id)
    for key, fallback in defaults.items():
        if key not in character_row:
            character_row[key] = fallback
            changed = True

    if character_row.get('id') != character_id:
        character_row['id'] = character_id
        changed = True

    if parse_optional_int(character_row.get('level'), fallback=0) != 0:
        character_row['level'] = 0
        changed = True

    for table_name, rows in tables.items():
        if table_name == 'character':
            continue
        for row in rows:
            row_id = row.get('id')
            if not is_valid_uuid(row_id):
                row['id'] = uuid()
                changed = True
            if table_name in _CHARACTER_BOUND_TABLES and row.get('character_id') != character_id:
                row['character_id'] = character_id
                changed = True

    for ability_name in _ABILITY_TABLES:
        skill_table_name = f'{ability_name}_skills'

        if not tables[ability_name]:
            ability_row, skill_row = _blank_ability_rows(ability_name, character_id)
            tables[ability_name] = [ability_row]
            tables[skill_table_name] = [skill_row]
            changed = True
            continue

        ability_row = tables[ability_name][0]
        if not is_valid_uuid(ability_row.get('id')):
            ability_row['id'] = uuid()
            changed = True
        ability_row['character_id'] = character_id
        ability_row['value'] = clamp_int(ability_row.get('value'), 1, 30, fallback=10)
        ability_row['modifier'] = parse_optional_int(ability_row.get('modifier'), fallback=0)
        ability_row['proficient'] = 1 if ability_row.get('proficient') else 0

        if not tables[skill_table_name]:
            _, skill_row = _blank_ability_rows(ability_name, character_id)
            skill_row[f'{ability_name}_id'] = ability_row['id']
            tables[skill_table_name] = [skill_row]
            changed = True
            continue

        skill_row = tables[skill_table_name][0]
        if not is_valid_uuid(skill_row.get('id')):
            skill_row['id'] = uuid()
            changed = True
        if skill_row.get(f'{ability_name}_id') != ability_row['id']:
            skill_row[f'{ability_name}_id'] = ability_row['id']
            changed = True
        skill_row['saving_throw'] = parse_optional_int(skill_row.get('saving_throw'), fallback=0)
        for skill in ABILITY_TO_SKILL_MAPPING[ability_name]:
            skill_row[skill] = parse_optional_int(skill_row.get(skill), fallback=0)
            skill_row[f'{skill}_proficient'] = 1 if skill_row.get(f'{skill}_proficient') else 0

    normalised = {
        'schema_version': _SCHEMA_VERSION,
        'character_id': character_id,
        'tables': tables,
    }
    return normalised, changed


def _convert_legacy_payload(payload: dict) -> dict:
    character = payload.get('character') or {}
    character_id = _coerce_character_id(character.get('id') if isinstance(character, dict) else None)

    migrated = _build_blank_payload(character_id)
    tables = migrated['tables']
    character_row = tables['character'][0]

    if isinstance(character, dict):
        for key in character_row:
            if key == 'id':
                continue
            if key in character:
                character_row[key] = character.get(key)
    character_row['level'] = 0

    for cls in payload.get('classes') or []:
        if not isinstance(cls, dict):
            continue
        class_id = cls.get('class_id')
        if not class_id:
            continue
        tables['class_to_character'].append({
            'id': cls.get('id') if is_valid_uuid(cls.get('id')) else uuid(),
            'character_id': character_id,
            'class_id': class_id,
            'level': clamp_int(cls.get('level'), 1, 20, fallback=1),
        })

    for feat in payload.get('feats_and_traits') or []:
        if not isinstance(feat, dict):
            continue
        name = sanitize_optional_str(feat.get('name'), max_len=255)
        if not name:
            continue
        tables['feat_and_trait'].append({
            'id': feat.get('id') if is_valid_uuid(feat.get('id')) else uuid(),
            'character_id': character_id,
            'name': name,
            'description': sanitize_optional_str(feat.get('description'), max_len=2000),
        })

    for stat in payload.get('custom_stats') or []:
        if not isinstance(stat, dict):
            continue
        name = sanitize_optional_str(stat.get('name'), max_len=255)
        if not name:
            continue
        tables['custom_stat'].append({
            'id': stat.get('id') if is_valid_uuid(stat.get('id')) else uuid(),
            'character_id': character_id,
            'name': name,
            'value': parse_optional_int(stat.get('value'), fallback=0),
        })

    abilities_by_name: Dict[str, dict] = {}
    for ability_entry in payload.get('abilities') or []:
        if not isinstance(ability_entry, dict):
            continue
        ability_name = str(ability_entry.get('ability_name') or '').strip().lower()
        if ability_name in ABILITY_TO_SKILL_MAPPING:
            abilities_by_name[ability_name] = ability_entry

    for ability_name in _ABILITY_TABLES:
        source = abilities_by_name.get(ability_name)
        if not source:
            continue

        source_ability = source.get('ability') or {}
        source_skills = source.get('skills') or {}

        ability_row = tables[ability_name][0]
        if is_valid_uuid(source_ability.get('id')):
            ability_row['id'] = source_ability['id']
        ability_row['character_id'] = character_id
        ability_row['value'] = clamp_int(source_ability.get('value'), 1, 30, fallback=10)
        ability_row['modifier'] = parse_optional_int(source_ability.get('modifier'), fallback=0)
        ability_row['proficient'] = 1 if source_ability.get('proficient') else 0

        skill_row = tables[f'{ability_name}_skills'][0]
        if is_valid_uuid(source_skills.get('id')):
            skill_row['id'] = source_skills['id']
        skill_row[f'{ability_name}_id'] = ability_row['id']
        skill_row['saving_throw'] = parse_optional_int(source_skills.get('saving_throw'), fallback=0)
        for skill in ABILITY_TO_SKILL_MAPPING[ability_name]:
            skill_row[skill] = parse_optional_int(source_skills.get(skill), fallback=0)
            skill_row[f'{skill}_proficient'] = 1 if source_skills.get(f'{skill}_proficient') else 0

    return migrated


def ensure_guest_payload(create_if_missing: bool = False) -> Optional[dict]:
    payload = session.get(_SESSION_KEY)

    if payload is None:
        if not create_if_missing:
            return None
        fresh = _build_blank_payload(uuid())
        session[_SESSION_KEY] = fresh
        session.permanent = True
        _mark_modified()
        return fresh

    if isinstance(payload, dict) and isinstance(payload.get('tables'), dict):
        normalised, changed = _normalise_new_payload(payload)
        if changed:
            session[_SESSION_KEY] = normalised
            _mark_modified()
            return normalised
        # Keep returning the live session object so downstream mutations on
        # nested table rows persist when GuestSessionStore updates records.
        return payload

    migrated = _convert_legacy_payload(payload if isinstance(payload, dict) else {})
    session[_SESSION_KEY] = migrated
    _mark_modified()
    return migrated


def is_guest() -> bool:
    return _SESSION_KEY in session


def get_guest_character_id() -> Optional[str]:
    payload = ensure_guest_payload(create_if_missing=False)
    if not payload:
        return None
    return payload.get('character_id')


def create_blank() -> None:
    if is_guest():
        ensure_guest_payload(create_if_missing=False)
        return
    fresh = _build_blank_payload(uuid())
    session[_SESSION_KEY] = fresh
    session.permanent = True
    _mark_modified()


class GuestSessionStore:
    """GoGetDB-like interface backed by session tables."""

    def __init__(self, character_id: Optional[str] = None):
        payload = ensure_guest_payload(create_if_missing=True)
        resolved_character_id = payload.get('character_id') if payload else character_id
        self.character_id = _coerce_character_id(resolved_character_id)

    def _is_session_table(self, table: str) -> bool:
        return table in _TABLES

    def _tables(self) -> dict:
        payload = ensure_guest_payload(create_if_missing=True)
        if not payload:
            return {}
        self.character_id = _coerce_character_id(payload.get('character_id'))
        return payload.get('tables') or {}

    @staticmethod
    def _matches(row: dict, params: Optional[dict]) -> bool:
        if not params:
            return True
        for key, value in params.items():
            if row.get(key) != value:
                return False
        return True

    def go_get_all(self, table: str, params: Optional[dict] = None, count: bool = False):
        if not self._is_session_table(table):
            return ggi.go_get_all(table, params, count=count)

        rows = self._tables().get(table, [])
        filtered = [dict(row) for row in rows if self._matches(row, params)]

        if count:
            return len(filtered)
        return filtered or None

    def go_get_one(self, table: str, params: Optional[dict] = None):
        if not self._is_session_table(table):
            return ggi.go_get_one(table, params)

        rows = self.go_get_all(table, params=params, count=False)
        if not isinstance(rows, list) or not rows:
            return None
        return rows[0]

    def go_add_new(self, table: str, data: dict):
        if not self._is_session_table(table):
            return ggi.go_add_new(table, data)

        tables = self._tables()
        if table not in tables:
            tables[table] = []
        tables[table].append(dict(data))
        _mark_modified()

    def go_update(self, table: str, data: dict):
        if not self._is_session_table(table):
            return ggi.go_update(table, data)

        row_id = data.get('id')
        if not row_id:
            raise ValueError("go_update requires an 'id' key")

        tables = self._tables()
        rows = tables.get(table, [])
        for row in rows:
            if row.get('id') != row_id:
                continue
            for key, value in data.items():
                if key == 'id':
                    continue
                row[key] = value
            _mark_modified()
            return

    def go_delete_it(self, table: str, data: dict):
        if not self._is_session_table(table):
            return ggi.go_delete_it(table, data)

        row_id = data.get('id')
        if not row_id:
            raise ValueError("go_delete_it requires an 'id' key")

        tables = self._tables()
        rows = tables.get(table, [])
        kept = []
        removed = False
        for row in rows:
            if self._matches(row, data):
                removed = True
                continue
            kept.append(row)

        if removed:
            tables[table] = kept
            _mark_modified()


def _skill_row_for_persist(row: dict, ability_name: str, ability_id: str) -> dict:
    data = {
        'id': row.get('id') if is_valid_uuid(row.get('id')) else uuid(),
        f'{ability_name}_id': ability_id,
        'saving_throw': parse_optional_int(row.get('saving_throw'), fallback=0),
    }
    for skill in ABILITY_TO_SKILL_MAPPING[ability_name]:
        data[skill] = parse_optional_int(row.get(skill), fallback=0)
        data[f'{skill}_proficient'] = 1 if row.get(f'{skill}_proficient') else 0
    return data


def persist_guest_to_db(db, user_id: str) -> Optional[str]:
    payload = ensure_guest_payload(create_if_missing=False)
    if not payload:
        return None

    character_id = payload.get('character_id')
    if not is_valid_uuid(character_id):
        return None

    tables = payload.get('tables') or {}
    character_rows = tables.get('character') or []
    if not character_rows:
        return None

    character = character_rows[0]
    db.go_add_new('character', {
        'id': character_id,
        'name': sanitize_optional_str(character.get('name'), max_len=255),
        'level': 0,
        'race': sanitize_optional_str(character.get('race'), max_len=255),
        'background': sanitize_optional_str(character.get('background'), max_len=255),
        'alignment': sanitize_optional_str(character.get('alignment'), max_len=255),
        'armour_class': parse_optional_int(character.get('armour_class')),
        'initiative': parse_optional_int(character.get('initiative')),
        'speed': parse_optional_int(character.get('speed')),
        'proficiency': parse_optional_int(character.get('proficiency')),
        'passive_wisdom': parse_optional_int(character.get('passive_wisdom')),
        'xp': parse_optional_int(character.get('xp')),
        'health_points': parse_optional_int(character.get('health_points')),
        'hit_dice': sanitize_optional_str(character.get('hit_dice'), max_len=255),
        'temporary_hit_points': parse_optional_int(character.get('temporary_hit_points')),
    })

    db.go_add_new('user_to_character', {
        'id': uuid(),
        'user_id': user_id,
        'character_id': character_id,
    })

    ability_ids: Dict[str, str] = {}
    for ability_name in _ABILITY_TABLES:
        ability_row = (tables.get(ability_name) or [{}])[0]
        ability_id = str(ability_row.get('id')) if is_valid_uuid(ability_row.get('id')) else uuid()
        ability_ids[ability_name] = ability_id
        db.go_add_new(ability_name, {
            'id': ability_id,
            'character_id': character_id,
            'value': clamp_int(ability_row.get('value'), 1, 30, fallback=10),
            'modifier': parse_optional_int(ability_row.get('modifier'), fallback=0),
            'proficient': 1 if ability_row.get('proficient') else 0,
        })

    for ability_name in _ABILITY_TABLES:
        skill_table_name = f'{ability_name}_skills'
        skill_row = (tables.get(skill_table_name) or [{}])[0]
        db.go_add_new(skill_table_name, _skill_row_for_persist(skill_row, ability_name, ability_ids[ability_name]))

    for cls in tables.get('class_to_character') or []:
        class_id = cls.get('class_id')
        if not class_id:
            continue
        db.go_add_new('class_to_character', {
            'id': cls.get('id') if is_valid_uuid(cls.get('id')) else uuid(),
            'character_id': character_id,
            'class_id': class_id,
            'level': clamp_int(cls.get('level'), 1, 20, fallback=1),
        })

    for feat in tables.get('feat_and_trait') or []:
        name = sanitize_optional_str(feat.get('name'), max_len=255)
        if not name:
            continue
        db.go_add_new('feat_and_trait', {
            'id': feat.get('id') if is_valid_uuid(feat.get('id')) else uuid(),
            'character_id': character_id,
            'name': name,
            'description': sanitize_optional_str(feat.get('description'), max_len=2000),
        })

    for stat in tables.get('custom_stat') or []:
        name = sanitize_optional_str(stat.get('name'), max_len=255)
        if not name:
            continue
        db.go_add_new('custom_stat', {
            'id': stat.get('id') if is_valid_uuid(stat.get('id')) else uuid(),
            'name': name,
            'value': parse_optional_int(stat.get('value'), fallback=0),
            'character_id': character_id,
        })

    clear_guest()
    return character_id


def clear_guest() -> None:
    session.pop(_SESSION_KEY, None)
    _mark_modified()
