from demiplane.functions.functions import uuid
from demiplane.functions.validators import sanitize_str, clamp_int, is_valid_uuid

from .constants import CUSTOM_BUFF_MAX


class CustomBuffsMixin:
    def fetch_custom_buffs_data(self):
        return self._get_custom_buffs()

    def _get_custom_buffs(self):
        custom_buffs = self._rows('custom_buff', {'character_id': self.character_id})
        custom_buff_tables = self._rows('custom_buff_to_stat_table', {'character_id': self.character_id})
        table_to_stats = self._rows('stat_table_to_stat', {'character_id': self.character_id})

        stats_by_table_id = {}
        for stat_record in table_to_stats:
            table_id = stat_record.get('stat_table_id')
            stat_name = str(stat_record.get('stat_name') or '').strip()
            if table_id and stat_name:
                stats_by_table_id.setdefault(table_id, []).append(stat_name)

        table_targets_by_buff_id = {}
        for table_mapping in custom_buff_tables:
            custom_buff_id = table_mapping.get('custom_buff_id')
            table_name = table_mapping.get('stat_table_name')
            table_id = table_mapping.get('stat_table_id')
            if not custom_buff_id or not table_name or not table_id:
                continue
            table_targets_by_buff_id.setdefault(custom_buff_id, []).append({
                'stat_table_name': table_name,
                'stat_table_id': table_id,
                'stat_names': stats_by_table_id.get(table_id, []),
            })

        for custom_buff in custom_buffs:
            custom_buff['targets'] = table_targets_by_buff_id.get(custom_buff.get('id'), [])

        return custom_buffs

    def save_custom_buff_values(self, character_id: str, request_form):
        table_name = 'custom_buff'
        name = sanitize_str(request_form.get(f'{table_name}-name'), max_len=255)
        value = clamp_int(request_form.get(f'{table_name}-value'), -999, 999, fallback=0)

        if not name:
            return

        if self._count('custom_buff', {'character_id': character_id}) >= CUSTOM_BUFF_MAX:
            return

        custom_stats = self._rows('custom_stat', {'character_id': character_id})
        feats_and_traits = self._rows('feat_and_trait', {'character_id': character_id})
        inventory = self._rows('inventory', {'character_id': character_id})
        buff_target_options = self._get_buff_target_options(custom_stats, feats_and_traits, inventory)

        selected_tables = []
        for field_name in request_form:
            if field_name.startswith(f'{table_name}-table-'):
                table_name_value = field_name.replace(f'{table_name}-table-', '')
                if table_name_value in buff_target_options:
                    selected_tables.append(table_name_value)

        if not selected_tables:
            return

        pending_table_targets = []
        for selected_table in selected_tables:
            selected_stats = []
            valid_values = self._get_valid_stat_values(buff_target_options, selected_table)
            stat_field_prefix = f'{table_name}-stat-{selected_table}-'
            for field_name in request_form:
                if not field_name.startswith(stat_field_prefix):
                    continue
                stat_value = str(request_form.get(field_name) or '').strip()
                if stat_value and stat_value in valid_values and stat_value not in selected_stats:
                    selected_stats.append(stat_value)

            if selected_stats:
                pending_table_targets.append({'table_name': selected_table, 'stats': selected_stats})

        if not pending_table_targets:
            return

        custom_buff_id = uuid()
        self.store.go_add_new('custom_buff', {
            'id': custom_buff_id,
            'name': name,
            'value': value,
            'character_id': character_id,
        })

        for pending_target in pending_table_targets:
            stat_table_id = uuid()
            self.store.go_add_new('custom_buff_to_stat_table', {
                'id': uuid(),
                'custom_buff_id': custom_buff_id,
                'stat_table_name': pending_target['table_name'],
                'stat_table_id': stat_table_id,
                'character_id': character_id,
            })
            for stat_name in pending_target['stats']:
                self.store.go_add_new('stat_table_to_stat', {
                    'id': uuid(),
                    'stat_table_id': stat_table_id,
                    'stat_name': stat_name,
                    'character_id': character_id,
                })

    def update_custom_buff_values(self, character_id: str, buff_id: str, request_form):
        if not is_valid_uuid(buff_id):
            return

        existing_buff = self.store.go_get_one('custom_buff', {'id': buff_id, 'character_id': character_id})
        if not existing_buff:
            return

        table_name = 'custom_buff'
        name = sanitize_str(request_form.get(f'{table_name}-name'), max_len=255)
        value = clamp_int(request_form.get(f'{table_name}-value'), -999, 999, fallback=0)

        if not name:
            return

        custom_stats = self._rows('custom_stat', {'character_id': character_id})
        feats_and_traits = self._rows('feat_and_trait', {'character_id': character_id})
        inventory = self._rows('inventory', {'character_id': character_id})
        buff_target_options = self._get_buff_target_options(custom_stats, feats_and_traits, inventory)

        selected_tables = []
        for field_name in request_form:
            if field_name.startswith(f'{table_name}-table-'):
                table_name_value = field_name.replace(f'{table_name}-table-', '')
                if table_name_value in buff_target_options:
                    selected_tables.append(table_name_value)

        if not selected_tables:
            return

        pending_table_targets = []
        for selected_table in selected_tables:
            selected_stats = []
            valid_values = self._get_valid_stat_values(buff_target_options, selected_table)
            stat_field_prefix = f'{table_name}-stat-{selected_table}-'
            for field_name in request_form:
                if not field_name.startswith(stat_field_prefix):
                    continue
                stat_value = str(request_form.get(field_name) or '').strip()
                if stat_value and stat_value in valid_values and stat_value not in selected_stats:
                    selected_stats.append(stat_value)

            if selected_stats:
                pending_table_targets.append({'table_name': selected_table, 'stats': selected_stats})

        if not pending_table_targets:
            return

        # Update the buff record itself
        self.store.go_update('custom_buff', {
            'id': buff_id,
            'name': name,
            'value': value,
            'character_id': character_id,
        })

        # Delete old target mappings
        old_tables = self._rows('custom_buff_to_stat_table', {'custom_buff_id': buff_id, 'character_id': character_id})
        for old_table in old_tables:
            old_stat_table_id = old_table.get('stat_table_id')
            if old_stat_table_id:
                for old_stat in self._rows('stat_table_to_stat', {'stat_table_id': old_stat_table_id, 'character_id': character_id}):
                    if old_stat.get('id'):
                        self.store.go_delete_it('stat_table_to_stat', {'id': old_stat['id']})
            if old_table.get('id'):
                self.store.go_delete_it('custom_buff_to_stat_table', {'id': old_table['id']})

        # Insert new target mappings
        for pending_target in pending_table_targets:
            stat_table_id = uuid()
            self.store.go_add_new('custom_buff_to_stat_table', {
                'id': uuid(),
                'custom_buff_id': buff_id,
                'stat_table_name': pending_target['table_name'],
                'stat_table_id': stat_table_id,
                'character_id': character_id,
            })
            for stat_name in pending_target['stats']:
                self.store.go_add_new('stat_table_to_stat', {
                    'id': uuid(),
                    'stat_table_id': stat_table_id,
                    'stat_name': stat_name,
                    'character_id': character_id,
                })
