from demiplane.functions.functions import uuid
from demiplane.functions.validators import sanitize_optional_str, parse_optional_int, is_valid_uuid
from demiplane.services import guest_character as guest_session


class CharacterInfoMixin:
    def save_character_values(self, request_form) -> str:
        table_name = 'character'
        submitted_character_id = request_form.get(f'{table_name}-id')
        character_id = self.character_id if self.guest_character else submitted_character_id

        # Reject a tampered/missing character id – fall through to create a new record
        if not is_valid_uuid(character_id):
            character_id = None

        existing = self.store.go_get_one('character', {'id': character_id}) if character_id else None

        def _has_field(field: str) -> bool:
            return f'{table_name}-{field}' in request_form

        def _optional_text(field: str, max_len: int):
            if _has_field(field):
                return sanitize_optional_str(request_form.get(f'{table_name}-{field}'), max_len=max_len)
            if existing:
                return existing.get(field)
            return None

        name = _optional_text('name', max_len=255)
        level = 0
        race = _optional_text('race', max_len=255)
        background = _optional_text('background', max_len=255)
        alignment = _optional_text('alignment', max_len=255)

        def _optional_int(field, fallback=None):
            if not _has_field(field):
                if existing:
                    return existing.get(field)
                return fallback
            raw = request_form.get(f'{table_name}-{field}')
            return parse_optional_int(raw, fallback)

        armour_class= _optional_int('armour_class')
        initiative= _optional_int('initiative')
        speed= _optional_int('speed')
        proficiency= _optional_int('proficiency')
        health_points= _optional_int('health_points')
        passive_wisdom= _optional_int('passive_wisdom')
        temporary_hit_points = _optional_int('temporary_hit_points')
        xp= _optional_int('xp')
        hit_dice = _optional_text('hit_dice', max_len=255)

        existing_proficiency = parse_optional_int(existing.get('proficiency'), fallback=0) if existing else 0
        if existing_proficiency is None:
            existing_proficiency = 0
        next_proficiency = parse_optional_int(proficiency, fallback=0)
        if next_proficiency is None:
            next_proficiency = 0
        proficiency_changed = next_proficiency != existing_proficiency

        character = {
            "id": character_id,
            "name": name,
            "level": level,
            "race": race,
            "background": background,
            "alignment": alignment,
            "armour_class": armour_class,
            "initiative": initiative,
            "speed": speed,
            "proficiency": proficiency,
            "health_points": health_points,
            "hit_dice": hit_dice,
            "passive_wisdom": passive_wisdom,
            "temporary_hit_points": temporary_hit_points,
            "xp": xp,
        }

        if self.guest_character:
            if not character_id:
                character_id = guest_session.get_guest_character_id()
            if not is_valid_uuid(character_id):
                character_id = uuid()

            character['id'] = character_id
            existing = self.store.go_get_one('character', {'id': character_id})
            if existing:
                self.store.go_update('character', character)
            else:
                self.store.go_add_new('character', character)

            if proficiency_changed:
                self._recalculate_ability_skill_scores(character_id)

            self.character_id = character_id
            return str(character_id)

        if character_id:
            self.store.go_update('character', character)
        else:
            character_id = uuid()
            character['id'] = character_id
            self.store.go_add_new('character', character)

        if proficiency_changed:
            self._recalculate_ability_skill_scores(character_id)

        return str(character_id)

    def save_combat_values(self, character_id: str, request_form):
        """Save only combat-related fields without touching other character data."""
        table_name = 'character'
        def _optional_int(field, fallback=None):
            raw = request_form.get(f'{table_name}-{field}')
            return parse_optional_int(raw, fallback)

        health_points = _optional_int('health_points')
        temporary_hit_points = _optional_int('temporary_hit_points')
        hit_dice = sanitize_optional_str(request_form.get(f'{table_name}-hit_dice'), max_len=255)

        existing = self.store.go_get_one('character', {'id': character_id})
        if not existing:
            return

        existing['health_points'] = health_points
        existing['temporary_hit_points'] = temporary_hit_points
        existing['hit_dice'] = hit_dice
        self.store.go_update('character', existing)
