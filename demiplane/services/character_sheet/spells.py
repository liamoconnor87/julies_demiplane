from demiplane.functions.functions import uuid


class SpellsMixin:
    def fetch_known_spell_ids(self) -> set:
        """Fetch the set of spell ids this character has marked as known."""
        rows = self._rows('spell_to_character', {'character_id': self.character_id})
        return {row['spell_id'] for row in rows}

    def fetch_known_spells_data(self):
        """Fetch full rows for this character's known spells only, for use as buff targets."""
        known_ids = self.fetch_known_spell_ids()
        if not known_ids:
            return []
        return [spell for spell in self.fetch_all_spells() if spell.get('id') in known_ids]

    def fetch_prepared_spell_ids(self) -> set:
        """Fetch the set of spell ids this character has marked as prepared today."""
        rows = self._rows('spell_to_character', {'character_id': self.character_id})
        return {row['spell_id'] for row in rows if row.get('prepared')}

    def toggle_spell_known(self, spell_id: str) -> bool:
        """Flip whether this character knows the given spell. Returns the new known state."""
        existing = self.store.go_get_one('spell_to_character', {'character_id': self.character_id, 'spell_id': spell_id})
        if existing:
            self.store.go_delete_it('spell_to_character', {'id': existing['id']})
            self._remove_buff_targets_for('spell', spell_id)
            return False
        self.store.go_add_new('spell_to_character', {
            'id': uuid(),
            'character_id': self.character_id,
            'spell_id': spell_id,
            'prepared': 0,
        })
        return True

    def toggle_spell_prepared(self, spell_id: str) -> bool:
        """Flip whether a known spell is prepared. No-op (returns False) if it isn't known."""
        existing = self.store.go_get_one('spell_to_character', {'character_id': self.character_id, 'spell_id': spell_id})
        if not existing:
            return False
        now_prepared = not existing.get('prepared')
        self.store.go_update('spell_to_character', {
            'id': existing['id'],
            'prepared': int(now_prepared),
        })
        return now_prepared
