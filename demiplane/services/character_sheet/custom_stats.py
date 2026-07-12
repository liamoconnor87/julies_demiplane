from demiplane.functions.functions import uuid
from demiplane.functions.validators import sanitize_optional_str, parse_optional_int, is_valid_uuid

from .constants import CUSTOM_STAT_MAX


class CustomStatsMixin:
    def fetch_custom_stats_data(self):
        return self._rows('custom_stat', {'character_id': self.character_id})

    def save_custom_stat_values(self, character_id: str, request_form):
        table_name = 'custom_stat'
        name_prefix = f'{table_name}-name-'
        value_prefix = f'{table_name}-value-'

        existing_custom_stat_ids = set()
        for field_name in request_form:
            if field_name.startswith(name_prefix):
                existing_custom_stat_ids.add(field_name.replace(name_prefix, ''))
            if field_name.startswith(value_prefix):
                existing_custom_stat_ids.add(field_name.replace(value_prefix, ''))

        for custom_stat_id in existing_custom_stat_ids:
            if not is_valid_uuid(custom_stat_id):
                continue

            existing_custom_stat = self.store.go_get_one('custom_stat', {'id': custom_stat_id, 'character_id': character_id})
            if not existing_custom_stat:
                continue

            raw_name = request_form.get(f'{table_name}-name-{custom_stat_id}')
            updated_name_candidate = sanitize_optional_str(raw_name, max_len=255)
            updated_name = updated_name_candidate if updated_name_candidate else existing_custom_stat.get('name')

            updated_value = request_form.get(f'{table_name}-value-{custom_stat_id}')
            parsed_updated_value = parse_optional_int(updated_value, fallback=existing_custom_stat.get('value', 0))

            self.store.go_update('custom_stat', {
                'id': custom_stat_id,
                'name': updated_name,
                'value': parsed_updated_value,
                'character_id': character_id,
            })

        name = sanitize_optional_str(request_form.get(f'{table_name}-name'), max_len=255)
        value = request_form.get(f'{table_name}-value')

        if not name:
            return

        if self._count('custom_stat', {'character_id': character_id}) >= CUSTOM_STAT_MAX:
            return

        parsed_value = parse_optional_int(value, fallback=0)

        custom_stat = {
            "id": uuid(),
            "name": name,
            "value": parsed_value,
            "character_id": character_id,
        }

        self.store.go_add_new('custom_stat', custom_stat)

    def update_single_custom_stat(self, character_id: str, custom_stat_id: str, name: str, value):
        """Update a single custom stat and return the updated record, or None."""
        if not is_valid_uuid(custom_stat_id):
            return None

        existing = self.store.go_get_one('custom_stat', {'id': custom_stat_id, 'character_id': character_id})
        if not existing:
            return None

        clean_name = sanitize_optional_str(name, max_len=255) or existing.get('name')
        parsed_value = parse_optional_int(value, fallback=existing.get('value', 0))

        self.store.go_update('custom_stat', {
            'id': custom_stat_id,
            'name': clean_name,
            'value': parsed_value,
            'character_id': character_id,
        })

        return {
            'id': custom_stat_id,
            'name': clean_name,
            'value': parsed_value,
            'character_id': character_id,
        }

    def remove_custom_stat(self, character_id: str, custom_stat_id: str):
        if not is_valid_uuid(custom_stat_id):
            return
        existing = self.store.go_get_one('custom_stat', {'id': custom_stat_id, 'character_id': character_id})
        if not existing:
            return
        self.store.go_delete_it('custom_stat', {'id': custom_stat_id, 'character_id': character_id})
