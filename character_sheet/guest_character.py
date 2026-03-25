"""
Guest character sheet — stores character data in a server-side session
instead of the database.  Mirrors the data contract of CharacterSheet.create_form()
so the same Jinja2 templates can render guest and registered characters identically.

Excluded for guests: inventory, custom buffs (and BuffProcessor).
"""
import math
from typing import Optional
from flask import session
from go_get_it.go_get_it import GoGetDB
from functions.functions import uuid
from functions.validators import (
    sanitize_optional_str,
    clamp_int, parse_optional_int,
    is_valid_uuid,
)
from character_sheet.character_sheet import (
    CharacterSheet,
    FEAT_TRAIT_MAX,
    CUSTOM_STAT_MAX,
)

ggi = GoGetDB()

# ── Session key ───────────────────────────────────────────────────────────────
_SESSION_KEY = 'guest_character'


def _mark_modified():
    """Tell Flask-Session the session dict has been mutated."""
    session.modified = True


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_guest() -> bool:
    """Return True when the current request belongs to an active guest session."""
    return _SESSION_KEY in session


def get_guest_character_id() -> Optional[str]:
    """Return the guest character_id or None."""
    guest = session.get(_SESSION_KEY)
    if guest:
        return guest.get('character', {}).get('id')
    return None


def _blank_ability(ability_name: str, character_id: str):
    """Return a default ability + skills entry."""
    ability_id = uuid()
    skill_list = CharacterSheet.ABILITY_TO_SKILL_MAPPING[ability_name]

    skills = {
        'id': uuid(),
        f'{ability_name}_id': ability_id,
        'saving_throw': 0,
    }
    for skill in skill_list:
        skills[skill] = 0
        skills[f'{skill}_proficient'] = 0

    return {
        'ability_name': ability_name,
        'ability': {
            'id': ability_id,
            'character_id': character_id,
            'value': 10,
            'modifier': 0,
            'proficient': 0,
        },
        'skills': skills,
        'skill_list': skill_list,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def create_blank():
    """
    Initialise a brand-new guest character in the session.
    If a guest character already exists, this is a no-op.
    """
    if is_guest():
        return

    character_id = uuid()

    abilities = []
    for ability_name in CharacterSheet.ABILITY_TO_SKILL_MAPPING:
        abilities.append(_blank_ability(ability_name, character_id))

    session[_SESSION_KEY] = {
        'character': {
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
            'current_health_points': 0,
        },
        'classes': [],
        'abilities': abilities,
        'feats_and_traits': [],
        'custom_stats': [],
    }
    session.permanent = True
    _mark_modified()


def create_form():
    """
    Return a dict matching the shape of CharacterSheet.create_form() + BuffProcessor.transform_out()
    so the same templates can render it.  Inventory and buffs are stubbed out.
    """
    guest = session.get(_SESSION_KEY, {})
    character = dict(guest.get('character') or {})
    classes = list(guest.get('classes') or [])
    abilities = list(guest.get('abilities') or [])
    feats_and_traits = list(guest.get('feats_and_traits') or [])
    custom_stats = list(guest.get('custom_stats') or [])

    # Recompute aggregate level from base + class levels
    base_level = 0
    for cls in classes:
        base_level += cls.get('level', 0)
    character['level'] = base_level

    # Current health
    def _to_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    character['current_health_points'] = _to_int(character.get('health_points')) + _to_int(character.get('temporary_hit_points'))

    # Class options (from DB — read-only reference data)
    all_classes = ggi.go_get_all('class') or []
    if not isinstance(all_classes, list):
        all_classes = []
    assigned_class_ids = [c.get('class_id') for c in classes]
    class_options = [c for c in all_classes if c['id'] not in assigned_class_ids]

    # Sort classes same as registered path
    classes.sort(
        key=lambda c: (
            -(int(c.get('level') or 0)),
            (c.get('class_name') or '')
        )
    )

    # Buff-target options (needed by custom_stats_change_response template)
    buff_target_options = {
        table_name: columns[:]
        for table_name, columns in CharacterSheet.BUFF_TARGET_TABLE_COLUMNS.items()
    }
    custom_stat_names = sorted(set(
        str(s.get('name', '')).strip()
        for s in custom_stats
        if str(s.get('name', '')).strip()
    ))
    buff_target_options['custom_stat'] = custom_stat_names

    return {
        'character': character,
        'classes': classes,
        'class_options': class_options,
        'abilities': abilities,
        'feats_and_traits': feats_and_traits,
        'feats_and_traits_at_capacity': len(feats_and_traits) >= FEAT_TRAIT_MAX,
        'inventory': [],
        'inventory_at_capacity': True,
        'custom_stats': custom_stats,
        'custom_stats_at_capacity': len(custom_stats) >= CUSTOM_STAT_MAX,
        'custom_buffs': [],
        'custom_buffs_at_capacity': True,
        'buff_target_options': buff_target_options,
    }


# ── Save methods ──────────────────────────────────────────────────────────────

def save_character_values(request_form):
    """Parse character-info form fields and write to session."""
    guest = session.get(_SESSION_KEY)
    if not guest:
        return

    char = guest['character']
    char['name'] = sanitize_optional_str(request_form.get('character-name'), max_len=255)
    char['race'] = sanitize_optional_str(request_form.get('character-race'), max_len=255)
    char['background'] = sanitize_optional_str(request_form.get('character-background'), max_len=255)
    char['alignment'] = sanitize_optional_str(request_form.get('character-alignment'), max_len=255)
    char['armour_class'] = parse_optional_int(request_form.get('character-armour_class'))
    char['initiative'] = parse_optional_int(request_form.get('character-initiative'))
    char['speed'] = parse_optional_int(request_form.get('character-speed'))
    char['proficiency'] = parse_optional_int(request_form.get('character-proficiency'))
    char['health_points'] = parse_optional_int(request_form.get('character-health_points'))
    char['passive_wisdom'] = parse_optional_int(request_form.get('character-passive_wisdom'))
    char['temporary_hit_points'] = parse_optional_int(request_form.get('character-temporary_hit_points'))
    char['xp'] = parse_optional_int(request_form.get('character-xp'))
    char['hit_dice'] = sanitize_optional_str(request_form.get('character-hit_dice'), max_len=255)

    _mark_modified()


def save_class_to_character_values(request_form):
    """Add a new class or update existing class levels in session."""
    guest = session.get(_SESSION_KEY)
    if not guest:
        return

    classes = guest['classes']
    character_id = guest['character']['id']

    # Add new class
    class_id = request_form.get('class_to_character-class_id')
    level_raw = request_form.get('class_to_character-level')
    if level_raw and class_id:
        level = clamp_int(level_raw, 1, 20, fallback=1)
        # Verify class_id is a real class from the DB
        existing_class = ggi.go_get_one('class', {'id': class_id})
        if existing_class:
            classes.append({
                'id': uuid(),
                'character_id': character_id,
                'class_id': class_id,
                'class_name': existing_class.get('name', ''),
                'level': level,
            })

    # Update existing class levels
    for field_name in request_form:
        if not field_name.startswith('classes-level-'):
            continue
        ctc_id = field_name.replace('classes-level-', '')
        new_level_raw = request_form.get(field_name)
        if not new_level_raw or not is_valid_uuid(ctc_id):
            continue
        for cls in classes:
            if cls.get('id') == ctc_id:
                cls['level'] = clamp_int(new_level_raw, 1, 20, fallback=cls.get('level', 1))
                break

    _mark_modified()


def save_ability_values(request_form):
    """Parse ability/skill form fields and write to session."""
    guest = session.get(_SESSION_KEY)
    if not guest:
        return

    character = guest['character']
    character_proficiency = int(character.get('proficiency') or 0)

    for ability_entry in guest['abilities']:
        ability_name = ability_entry['ability_name']
        ability = ability_entry['ability']
        skills = ability_entry['skills']
        skill_list = ability_entry['skill_list']

        raw_value = request_form.get(f'{ability_name}-value')
        if not raw_value or str(raw_value).strip() == '':
            continue

        value = clamp_int(raw_value, 1, 30, fallback=10)
        modifier = math.floor((value - 10) / 2)

        saving_proficient = 0
        if request_form.get(f'{ability_name}-proficient') == '1':
            saving_proficient = 1

        ability['value'] = value
        ability['modifier'] = modifier
        ability['proficient'] = saving_proficient

        # Saving throw
        saving_proficient_score = 0
        if saving_proficient and character_proficiency:
            saving_proficient_score = character_proficiency
        skills['saving_throw'] = modifier + saving_proficient_score

        # Individual skills
        for skill in skill_list:
            skill_proficient = 0
            skill_proficient_score = 0
            if request_form.get(f'{ability_name}_skills-{skill}_proficient') == '1':
                skill_proficient = 1
                skill_proficient_score = character_proficiency

            skills[skill] = modifier + skill_proficient_score
            skills[f'{skill}_proficient'] = skill_proficient

    _mark_modified()


def save_feat_and_trait_values(request_form):
    """Add a new feat/trait or update existing ones in the session list."""
    guest = session.get(_SESSION_KEY)
    if not guest:
        return

    feats = guest['feats_and_traits']

    # Update existing feats
    name_prefix = 'feat_and_trait-name-'
    desc_prefix = 'feat_and_trait-description-'
    existing_feat_ids = set()
    for field_name in request_form:
        if field_name.startswith(name_prefix):
            existing_feat_ids.add(field_name.replace(name_prefix, ''))
        if field_name.startswith(desc_prefix):
            existing_feat_ids.add(field_name.replace(desc_prefix, ''))

    for feat_id in existing_feat_ids:
        if not is_valid_uuid(feat_id):
            continue
        for feat in feats:
            if feat['id'] == feat_id:
                updated_name = sanitize_optional_str(request_form.get(f'{name_prefix}{feat_id}'), max_len=255)
                updated_desc = sanitize_optional_str(request_form.get(f'{desc_prefix}{feat_id}'), max_len=500)
                if updated_name:
                    feat['name'] = updated_name
                    feat['description'] = updated_desc
                break
    _mark_modified()

    # Add new feat
    if len(feats) >= FEAT_TRAIT_MAX:
        return

    name = sanitize_optional_str(request_form.get('feat_and_trait-name'), max_len=255)
    description = sanitize_optional_str(request_form.get('feat_and_trait-description'), max_len=500)
    if not name:
        return

    feats.append({
        'id': uuid(),
        'character_id': guest['character']['id'],
        'name': name,
        'description': description,
    })
    _mark_modified()


def save_custom_stat_values(request_form):
    """Add/update custom stats in the session."""
    guest = session.get(_SESSION_KEY)
    if not guest:
        return

    custom_stats = guest['custom_stats']
    character_id = guest['character']['id']
    table_name = 'custom_stat'
    name_prefix = f'{table_name}-name-'
    value_prefix = f'{table_name}-value-'

    # Collect IDs of existing stats being updated
    existing_ids = set()
    for field_name in request_form:
        if field_name.startswith(name_prefix):
            existing_ids.add(field_name.replace(name_prefix, ''))
        if field_name.startswith(value_prefix):
            existing_ids.add(field_name.replace(value_prefix, ''))

    # Update existing
    for stat_id in existing_ids:
        if not is_valid_uuid(stat_id):
            continue
        stat = next((s for s in custom_stats if s.get('id') == stat_id), None)
        if not stat:
            continue

        raw_name = request_form.get(f'{table_name}-name-{stat_id}')
        updated_name = sanitize_optional_str(raw_name, max_len=255)
        if updated_name:
            stat['name'] = updated_name

        updated_value = request_form.get(f'{table_name}-value-{stat_id}')
        stat['value'] = parse_optional_int(updated_value, fallback=stat.get('value', 0))

    # Add new
    new_name = sanitize_optional_str(request_form.get(f'{table_name}-name'), max_len=255)
    if new_name and len(custom_stats) < CUSTOM_STAT_MAX:
        new_value = parse_optional_int(request_form.get(f'{table_name}-value'), fallback=0)
        custom_stats.append({
            'id': uuid(),
            'name': new_name,
            'value': new_value,
            'character_id': character_id,
        })

    _mark_modified()


# ── Remove methods ────────────────────────────────────────────────────────────

def remove_class(class_id: str):
    """Remove a class assignment by its class_to_character id."""
    guest = session.get(_SESSION_KEY)
    if not guest:
        return
    guest['classes'] = [c for c in guest['classes'] if c.get('id') != class_id]
    _mark_modified()


def remove_feat_and_trait(item_id: str):
    """Remove a feat/trait by id."""
    guest = session.get(_SESSION_KEY)
    if not guest:
        return
    guest['feats_and_traits'] = [f for f in guest['feats_and_traits'] if f.get('id') != item_id]
    _mark_modified()


def update_single_feat(feat_id: str, name: str, description: str):
    """Update a single feat/trait in the session and return it, or None."""
    guest = session.get(_SESSION_KEY)
    if not guest or not is_valid_uuid(feat_id):
        return None
    clean_name = sanitize_optional_str(name, max_len=255)
    clean_desc = sanitize_optional_str(description, max_len=500)
    if not clean_name:
        return None
    for feat in guest['feats_and_traits']:
        if feat['id'] == feat_id:
            feat['name'] = clean_name
            feat['description'] = clean_desc
            _mark_modified()
            return feat
    return None


def add_single_feat(name: str, description: str):
    """Add a new feat/trait to the session and return it, or None."""
    guest = session.get(_SESSION_KEY)
    if not guest:
        return None
    feats = guest['feats_and_traits']
    if len(feats) >= FEAT_TRAIT_MAX:
        return None
    clean_name = sanitize_optional_str(name, max_len=255)
    if not clean_name:
        return None
    clean_desc = sanitize_optional_str(description, max_len=500)
    feat = {
        'id': uuid(),
        'character_id': guest['character']['id'],
        'name': clean_name,
        'description': clean_desc,
    }
    feats.append(feat)
    _mark_modified()
    return feat


def remove_custom_stat(item_id: str):
    """Remove a custom stat by id."""
    guest = session.get(_SESSION_KEY)
    if not guest:
        return
    guest['custom_stats'] = [s for s in guest['custom_stats'] if s.get('id') != item_id]
    _mark_modified()


# ── Migration: guest → registered user ────────────────────────────────────────

def persist_guest_to_db(db, user_id: str) -> Optional[str]:
    """
    Write the guest character data from the session into the database,
    link it to the given user, and clear the session.
    Returns the migrated character_id or None.
    """
    guest = session.get(_SESSION_KEY)
    if not guest:
        return None

    character = guest.get('character', {})
    character_id = character.get('id')
    if not character_id:
        return None

    # 1. Insert character row
    db.go_add_new('character', {
        'id': character_id,
        'name': character.get('name'),
        'level': 0,  # base level is 0; total is computed from class levels
        'race': character.get('race'),
        'background': character.get('background'),
        'alignment': character.get('alignment'),
        'armour_class': character.get('armour_class'),
        'initiative': character.get('initiative'),
        'speed': character.get('speed'),
        'proficiency': character.get('proficiency'),
        'passive_wisdom': character.get('passive_wisdom'),
        'xp': character.get('xp'),
        'health_points': character.get('health_points'),
        'hit_dice': character.get('hit_dice'),
        'temporary_hit_points': character.get('temporary_hit_points'),
    })

    # 2. Link to user
    db.go_add_new('user_to_character', {
        'id': uuid(),
        'user_id': user_id,
        'character_id': character_id,
    })

    # 3. Abilities + skills
    for ability_entry in guest.get('abilities', []):
        ability_name = ability_entry['ability_name']
        ability = ability_entry['ability']
        skills = ability_entry['skills']

        db.go_add_new(ability_name, {
            'id': ability['id'],
            'character_id': character_id,
            'value': ability.get('value', 10),
            'modifier': ability.get('modifier', 0),
            'proficient': ability.get('proficient', 0),
        })

        skill_row = {'id': skills['id'], f'{ability_name}_id': ability['id']}
        skill_row['saving_throw'] = skills.get('saving_throw', 0)
        for skill in ability_entry['skill_list']:
            skill_row[skill] = skills.get(skill, 0)
            skill_row[f'{skill}_proficient'] = skills.get(f'{skill}_proficient', 0)
        db.go_add_new(f'{ability_name}_skills', skill_row)

    # 4. Classes
    for cls in guest.get('classes', []):
        db.go_add_new('class_to_character', {
            'id': cls['id'],
            'character_id': character_id,
            'class_id': cls['class_id'],
            'level': cls.get('level', 1),
        })

    # 5. Feats & traits
    for feat in guest.get('feats_and_traits', []):
        db.go_add_new('feat_and_trait', {
            'id': feat['id'],
            'character_id': character_id,
            'name': feat.get('name'),
            'description': feat.get('description'),
        })

    # 6. Custom stats
    for stat in guest.get('custom_stats', []):
        db.go_add_new('custom_stat', {
            'id': stat['id'],
            'name': stat.get('name'),
            'value': stat.get('value', 0),
            'character_id': character_id,
        })

    # 7. Clear guest session
    session.pop(_SESSION_KEY, None)
    _mark_modified()

    return character_id


def clear_guest():
    """Discard guest data from the session (used on login)."""
    session.pop(_SESSION_KEY, None)
    _mark_modified()
