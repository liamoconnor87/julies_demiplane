from demiplane.functions.functions import uuid
from demiplane.functions.validators import sanitize_optional_str, is_valid_uuid

from .constants import FEAT_TRAIT_MAX


class FeatsMixin:
    def save_feat_and_trait_values(self, character_id: str, request_form):
        table_name = 'feat_and_trait'

        # Update existing feats
        name_prefix = f'{table_name}-name-'
        desc_prefix = f'{table_name}-description-'
        existing_feat_ids = set()
        for field_name in request_form:
            if field_name.startswith(name_prefix):
                existing_feat_ids.add(field_name.replace(name_prefix, ''))
            if field_name.startswith(desc_prefix):
                existing_feat_ids.add(field_name.replace(desc_prefix, ''))

        for feat_id in existing_feat_ids:
            if not is_valid_uuid(feat_id):
                continue
            existing_feat = self.store.go_get_one('feat_and_trait', {'id': feat_id, 'character_id': character_id})
            if not existing_feat:
                continue
            updated_name = sanitize_optional_str(request_form.get(f'{name_prefix}{feat_id}'), max_len=255)
            updated_desc = sanitize_optional_str(request_form.get(f'{desc_prefix}{feat_id}'), max_len=2000)
            if updated_name:
                self.store.go_update('feat_and_trait', {
                    'id': feat_id,
                    'name': updated_name,
                    'description': updated_desc,
                    'character_id': character_id,
                })

        # Add new feat
        feat_and_trait_id = uuid()
        name = sanitize_optional_str(request_form.get(f'{table_name}-name'), max_len=255)
        description = sanitize_optional_str(request_form.get(f'{table_name}-description'), max_len=2000)

        if name:
            if self._count('feat_and_trait', {'character_id': character_id}) >= FEAT_TRAIT_MAX:
                return
            feat_and_trait = {
                "id": feat_and_trait_id,
                "name": name,
                "description": description,
                "character_id": character_id,
            }

            self.store.go_add_new('feat_and_trait', feat_and_trait)

    def update_single_feat(self, character_id: str, feat_id: str, name: str, description: str):
        """Update a single feat/trait and return the updated record, or None."""
        if not is_valid_uuid(feat_id):
            return None
        existing = self.store.go_get_one('feat_and_trait', {'id': feat_id, 'character_id': character_id})
        if not existing:
            return None
        clean_name = sanitize_optional_str(name, max_len=255)
        clean_desc = sanitize_optional_str(description, max_len=2000)
        if not clean_name:
            return existing
        self.store.go_update('feat_and_trait', {
            'id': feat_id,
            'name': clean_name,
            'description': clean_desc,
            'character_id': character_id,
        })
        return {'id': feat_id, 'name': clean_name, 'description': clean_desc, 'character_id': character_id}

    def add_single_feat(self, character_id: str, name: str, description: str):
        """Add a new feat/trait and return the new record, or None if at capacity or invalid."""
        clean_name = sanitize_optional_str(name, max_len=255)
        if not clean_name:
            return None
        if self._count('feat_and_trait', {'character_id': character_id}) >= FEAT_TRAIT_MAX:
            return None
        clean_desc = sanitize_optional_str(description, max_len=2000)
        feat_id = uuid()
        feat = {
            'id': feat_id,
            'name': clean_name,
            'description': clean_desc,
            'character_id': character_id,
        }
        self.store.go_add_new('feat_and_trait', feat)
        return feat

    def remove_feat_and_trait(self, character_id: str, feat_id: str):
        if not is_valid_uuid(feat_id):
            return
        existing = self.store.go_get_one('feat_and_trait', {'id': feat_id, 'character_id': character_id})
        if not existing:
            return
        self.store.go_delete_it('feat_and_trait', {'id': feat_id, 'character_id': character_id})
