from demiplane.functions.functions import uuid
from demiplane.functions.validators import clamp_int, is_valid_uuid


class ClassesMixin:
    def save_class_to_character_values(self, character_id: str, request_form):
        table_name = 'class_to_character'

        class_id = request_form.get(f'{table_name}-class_id')
        level_raw = request_form.get(f'{table_name}-level')

        # Validate: class_id must be a known class; level must be 1-20
        if level_raw and class_id:
            level = clamp_int(level_raw, 1, 20, fallback=1)
            existing_class = self.store.go_get_one('class', {'id': class_id})
            if existing_class:
                class_to_character = {
                    "id": uuid(),
                    "character_id": character_id,
                    "class_id": class_id,
                    "level": level,
                }
                self.store.go_add_new('class_to_character', class_to_character)

        for field_name in request_form:
            if field_name.startswith('classes-level-'):
                class_to_character_id = field_name.replace('classes-level-', '')
                new_level_raw = request_form.get(field_name)

                if new_level_raw and is_valid_uuid(class_to_character_id):
                    # Verify this record belongs to the current character
                    existing = self.store.go_get_one('class_to_character', {
                        'id': class_to_character_id,
                        'character_id': character_id,
                    })
                    if existing:
                        self.store.go_update('class_to_character', {
                            'id': class_to_character_id,
                            'level': clamp_int(new_level_raw, 1, 20, fallback=existing.get('level', 1))
                        })

    def remove_class(self, character_id: str, class_id: str):
        if not is_valid_uuid(class_id):
            return
        existing = self.store.go_get_one('class_to_character', {'id': class_id, 'character_id': character_id})
        if not existing:
            return
        self.store.go_delete_it('class_to_character', {'id': class_id, 'character_id': character_id})
