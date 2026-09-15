from demiplane.functions.functions import uuid
from demiplane.functions.validators import clamp_int

CURRENCY_FIELDS = ('copper', 'silver', 'electrum', 'gold', 'platinum')


class PurseMixin:
    def fetch_purse_data(self):
        """Return the character's purse row, or an all-zero default if none exists yet."""
        row = self.store.go_get_one('purse', {'character_id': self.character_id})
        if row:
            return row
        return {field: 0 for field in CURRENCY_FIELDS}

    def save_purse_values(self, character_id: str, request_form):
        """Upsert all 5 currency fields from a request form in one call, and return them."""
        values = {
            field: clamp_int(request_form.get(f'purse-{field}'), 0, 999_999_999, fallback=0)
            for field in CURRENCY_FIELDS
        }

        existing = self.store.go_get_one('purse', {'character_id': character_id})
        if existing:
            row = {'id': existing['id'], 'character_id': character_id, **values}
            self.store.go_update('purse', row)
        else:
            row = {'id': uuid(), 'character_id': character_id, **values}
            self.store.go_add_new('purse', row)

        return values
