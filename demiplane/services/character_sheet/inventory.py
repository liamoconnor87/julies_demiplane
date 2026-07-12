from demiplane.functions.functions import uuid
from demiplane.functions.validators import sanitize_str, sanitize_optional_str, clamp_int, parse_optional_int, is_valid_uuid

from .constants import INVENTORY_MAX


class InventoryMixin:
    def save_inventory_values(self, character_id: str, request_form):
        table_name = 'inventory'
        name = sanitize_optional_str(request_form.get(f'{table_name}-name'), max_len=255)
        description = sanitize_optional_str(request_form.get(f'{table_name}-description'), max_len=2000)
        quantity = request_form.get(f'{table_name}-quantity')
        action = sanitize_str(request_form.get('inventory-action'), max_len=20)
        update_id = request_form.get('inventory-update-id')
        step_value = request_form.get('inventory-step')

        # Guard: only accept known action values
        if action and action not in ('add', 'update', 'step'):
            return

        # Guard: update/step ids must be valid UUIDs
        if update_id and not is_valid_uuid(update_id):
            return

        def update_inventory_by_id(inventory_id: str):
            existing_inventory = self.store.go_get_one('inventory', {'id': inventory_id, 'character_id': character_id})
            if not existing_inventory:
                return

            quantity_value = request_form.get(f'inventory-quantity-{inventory_id}')

            if quantity_value is None or str(quantity_value).strip() == '':
                self.store.go_delete_it('inventory', {
                    'id': inventory_id,
                    'character_id': character_id,
                })
                return

            try:
                parsed_quantity = int(quantity_value)
            except (TypeError, ValueError):
                parsed_quantity = existing_inventory.get('quantity', 1)

            if parsed_quantity <= 0:
                self.store.go_delete_it('inventory', {
                    'id': inventory_id,
                    'character_id': character_id,
                })
                return

            self.store.go_update('inventory', {
                'id': inventory_id,
                'name': existing_inventory.get('name'),
                'description': existing_inventory.get('description'),
                'quantity': parsed_quantity,
                'character_id': character_id,
            })

        def step_inventory_by_id(inventory_id: str, step: int):
            existing_inventory = self.store.go_get_one('inventory', {'id': inventory_id, 'character_id': character_id})
            if not existing_inventory:
                return

            current_quantity = existing_inventory.get('quantity')
            parsed_current_quantity = parse_optional_int(current_quantity, fallback=1)
            if parsed_current_quantity is None:
                parsed_current_quantity = 1

            next_quantity = parsed_current_quantity + step
            if next_quantity <= 0:
                self.store.go_delete_it('inventory', {
                    'id': inventory_id,
                    'character_id': character_id,
                })
                return

            self.store.go_update('inventory', {
                'id': inventory_id,
                'name': existing_inventory.get('name'),
                'description': existing_inventory.get('description'),
                'quantity': next_quantity,
                'character_id': character_id,
            })

        if action == 'add' and name:
            if self._count('inventory', {'character_id': character_id}) >= INVENTORY_MAX:
                return
            parsed_quantity = clamp_int(quantity, 1, 9999, fallback=1)
            inventory = {
                "id": uuid(),
                "name": name,
                "description": description,
                "quantity": parsed_quantity,
                "character_id": character_id,
            }

            self.store.go_add_new('inventory', inventory)

        if action == 'update' and update_id:
            update_inventory_by_id(update_id)
            return

        if action == 'step' and update_id:
            # Clamp step to ±100 to prevent runaway quantity changes
            parsed_step = clamp_int(step_value, -100, 100, fallback=0)

            if parsed_step != 0:
                step_inventory_by_id(update_id, parsed_step)
            return

        if action:
            return

        for field_name in request_form:
            if not field_name.startswith('inventory-quantity-'):
                continue

            inventory_id = field_name.replace('inventory-quantity-', '')
            if not is_valid_uuid(inventory_id):
                continue
            update_inventory_by_id(inventory_id)

    def update_single_inventory_item(self, character_id: str, inventory_id: str, name: str, description: str):
        """Update a single inventory item's name/description and return the updated record, or None."""
        if not is_valid_uuid(inventory_id):
            return None
        existing = self.store.go_get_one('inventory', {'id': inventory_id, 'character_id': character_id})
        if not existing:
            return None
        clean_name = sanitize_optional_str(name, max_len=255)
        clean_desc = sanitize_optional_str(description, max_len=2000)
        if not clean_name:
            return existing
        self.store.go_update('inventory', {
            'id': inventory_id,
            'name': clean_name,
            'description': clean_desc,
            'quantity': existing.get('quantity', 1),
            'character_id': character_id,
        })
        return {'id': inventory_id, 'name': clean_name, 'description': clean_desc, 'quantity': existing.get('quantity', 1), 'character_id': character_id}

    def add_single_inventory_item(self, character_id: str, name: str, description: str, quantity):
        """Add a new inventory item and return the new record, or None if at capacity or invalid."""
        clean_name = sanitize_optional_str(name, max_len=255)
        if not clean_name:
            return None
        if self._count('inventory', {'character_id': character_id}) >= INVENTORY_MAX:
            return None
        clean_desc = sanitize_optional_str(description, max_len=2000)
        parsed_quantity = clamp_int(quantity, 1, 9999, fallback=1)
        inventory_id = uuid()
        item = {
            'id': inventory_id,
            'name': clean_name,
            'description': clean_desc,
            'quantity': parsed_quantity,
            'character_id': character_id,
        }
        self.store.go_add_new('inventory', item)
        return item

    def step_single_inventory_item(self, character_id: str, inventory_id: str, step: int):
        """Apply +/- quantity to a single inventory item.

        Returns the updated row dict. Returns None when the item is deleted or invalid.
        """
        if not is_valid_uuid(inventory_id):
            return None

        existing = self.store.go_get_one('inventory', {'id': inventory_id, 'character_id': character_id})
        if not existing:
            return None

        current_quantity = parse_optional_int(existing.get('quantity'), fallback=1)
        if current_quantity is None:
            current_quantity = 1

        next_quantity = current_quantity + int(step)
        if next_quantity <= 0:
            self.store.go_delete_it('inventory', {
                'id': inventory_id,
                'character_id': character_id,
            })
            return None

        self.store.go_update('inventory', {
            'id': inventory_id,
            'name': existing.get('name'),
            'description': existing.get('description'),
            'quantity': next_quantity,
            'character_id': character_id,
        })

        return {
            'id': inventory_id,
            'name': existing.get('name'),
            'description': existing.get('description'),
            'quantity': next_quantity,
            'character_id': character_id,
        }
