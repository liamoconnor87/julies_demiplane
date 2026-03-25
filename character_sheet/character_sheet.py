from typing import Optional
from go_get_it.go_get_it import GoGetDB
from functions.functions import uuid
from functions.validators import (
    sanitize_str, sanitize_optional_str,
     clamp_int, parse_optional_int,
    is_valid_uuid,
)
ggi = GoGetDB()

INVENTORY_MAX = 50
CUSTOM_STAT_MAX = 20
CUSTOM_BUFF_MAX = 20
FEAT_TRAIT_MAX = 15

class CharacterSheet:
    ABILITY_TO_SKILL_MAPPING = {
        "strength": ["athletics"],
        "dexterity": ["acrobatics", "sleight_of_hand", "stealth"],
        "constitution": [],
        "intelligence": ["arcana", "history", "investigation", "nature", "religion"],
        "wisdom": ["animal_handling", "insight", "medicine", "perception", "survival"],
        "charisma": ["deception", "intimidation", "performance", "persuasion"],
    }

    BUFF_TARGET_TABLE_COLUMNS = {
        "character": [
            "armour_class",
            "initiative",
            "speed",
            "proficiency",
            "passive_wisdom",
        ],
        "strength": ["value", "modifier"],
        "dexterity": ["value", "modifier"],
        "constitution": ["value", "modifier"],
        "intelligence": ["value", "modifier"],
        "wisdom": ["value", "modifier"],
        "charisma": ["value", "modifier"],
        "strength_skills": ["saving_throw", "athletics"],
        "dexterity_skills": ["saving_throw", "acrobatics", "sleight_of_hand", "stealth"],
        "constitution_skills": ["saving_throw"],
        "intelligence_skills": ["saving_throw", "arcana", "history", "investigation", "nature", "religion"],
        "wisdom_skills": ["saving_throw", "animal_handling", "insight", "medicine", "perception", "survival"],
        "charisma_skills": ["saving_throw", "deception", "intimidation", "performance", "persuasion"],
    }

    # TODO: Add validation
    def __init__(self, character_id: Optional[str] = None):
        self.character_id = character_id

    def create_form(self):
        """
        Returns structured data for the character sheet instead of HTML strings.
        This data will be passed to Jinja2 templates for rendering.
        """
        # Get character data
        character = ggi.go_get_one('character', {'id': self.character_id}) if self.character_id else {}

        def _to_int(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        # Calculate total character level from base + class levels
        if character:
            characters_class_levels = ggi.go_get_all('class_to_character', {'character_id': character.get('id')})
            character_level = character.get('level', 0)

            for char_class in characters_class_levels or []:
                character_level += char_class.get('level', 0)

            character['level'] = character_level
            character['current_health_points'] = _to_int(character.get('health_points')) + _to_int(character.get('temporary_hit_points'))

        # Get abilities and skills data
        abilities_data = []
        for ability_name in self.ABILITY_TO_SKILL_MAPPING:
            ability = ggi.go_get_one(ability_name, {"character_id": self.character_id}) or {}

            # Get skills for this ability
            skills = {}
            if ability.get('id'):
                skills = ggi.go_get_one(f"{ability_name}_skills", {f"{ability_name}_id": ability['id']}) or {}

            # Get skill list for this ability
            skill_list = self.ABILITY_TO_SKILL_MAPPING[ability_name]

            abilities_data.append({
                'ability_name': ability_name,
                'ability': ability,
                'skills': skills,
                'skill_list': skill_list
            })

        # Classes
        all_classes = ggi.go_get_all('class') or []
        if not isinstance(all_classes, list):
            all_classes = []

        classes = ggi.go_get_all('class_to_character', {'character_id': self.character_id}) or []
        if not isinstance(classes, list):
            classes = []

        # Get IDs of classes already assigned to this character
        assigned_class_ids = [char_class['class_id'] for char_class in classes]

        # Filter out classes that are already assigned
        class_options = [c for c in all_classes if c['id'] not in assigned_class_ids]

        # Match class IDs to class names
        for char_class in classes:
            matching_class = next((c for c in all_classes if c['id'] == char_class['class_id']), None)
            if matching_class:
                char_class['class_name'] = matching_class['name']

        classes.sort(
            key=lambda char_class: (
                -(int(char_class.get('level') or 0)),
                (char_class.get('class_name') or '')
            )
        )

        # Feats & Traits
        feats_and_traits = ggi.go_get_all('feat_and_trait', {'character_id': self.character_id}) or []

        # Inventory
        inventory = ggi.go_get_all('inventory', {'character_id': self.character_id}) or []

        # Custom Stats
        custom_stats = ggi.go_get_all('custom_stat', {'character_id': self.character_id}) or []

        buff_target_options = self._get_buff_target_options(custom_stats, feats_and_traits, inventory)
        custom_buffs = self._get_custom_buffs()

        return {
            'character': character,
            'classes': classes,
            'class_options': class_options,
            'abilities': abilities_data,
            'feats_and_traits': feats_and_traits,
            'feats_and_traits_at_capacity': len(feats_and_traits) >= FEAT_TRAIT_MAX,
            'inventory': inventory,
            'inventory_at_capacity': len(inventory) >= INVENTORY_MAX,
            'custom_stats': custom_stats,
            'custom_stats_at_capacity': len(custom_stats) >= CUSTOM_STAT_MAX,
            'custom_buffs': custom_buffs,
            'custom_buffs_at_capacity': len(custom_buffs) >= CUSTOM_BUFF_MAX,
            'buff_target_options': buff_target_options,
        }

    def _parse_int(self, value, fallback=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _get_buff_target_options(self, custom_stats, feats_and_traits=None, inventory=None):
        options = {
            table_name: columns[:]
            for table_name, columns in self.BUFF_TARGET_TABLE_COLUMNS.items()
        }

        custom_stat_ids = []
        seen_cs_ids = set()
        for custom_stat in custom_stats or []:
            cs_id = custom_stat.get('id')
            stat_name = str(custom_stat.get('name') or '').strip()
            if not cs_id or not stat_name:
                continue
            if cs_id not in seen_cs_ids:
                seen_cs_ids.add(cs_id)
                custom_stat_ids.append({'id': cs_id, 'name': stat_name})

        custom_stat_ids.sort(key=lambda x: x['name'])
        options['custom_stat'] = custom_stat_ids

        feat_ids = []
        seen_feat_ids = set()
        for feat in feats_and_traits or []:
            feat_id = feat.get('id')
            feat_name = str(feat.get('name') or '').strip()
            if feat_id and feat_name and feat_id not in seen_feat_ids:
                seen_feat_ids.add(feat_id)
                feat_ids.append({'id': feat_id, 'name': feat_name})

        feat_ids.sort(key=lambda x: x['name'])
        options['feat_and_trait'] = feat_ids

        inventory_ids = []
        seen_inv_ids = set()
        for item in inventory or []:
            item_id = item.get('id')
            item_name = str(item.get('name') or '').strip()
            if item_id and item_name and item_id not in seen_inv_ids:
                seen_inv_ids.add(item_id)
                inventory_ids.append({'id': item_id, 'name': item_name})

        inventory_ids.sort(key=lambda x: x['name'])
        options['inventory'] = inventory_ids
        return options

    def _get_custom_buffs(self):
        custom_buffs = ggi.go_get_all('custom_buff', {'character_id': self.character_id}) or []
        custom_buff_tables = ggi.go_get_all('custom_buff_to_stat_table', {'character_id': self.character_id}) or []
        table_to_stats = ggi.go_get_all('stat_table_to_stat', {'character_id': self.character_id}) or []

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

    _ID_BASED_TABLES = {'custom_stat', 'feat_and_trait', 'inventory'}

    def _get_valid_stat_values(self, buff_target_options, table_name):
        """Get set of valid stat values for a table. For ID-based tables, returns IDs."""
        options = buff_target_options.get(table_name, [])
        if table_name in self._ID_BASED_TABLES:
            return {opt['id'] for opt in options if isinstance(opt, dict) and opt.get('id')}
        return set(options)

    def save_custom_buff_values(self, character_id: str, request_form):
        table_name = 'custom_buff'
        name = sanitize_str(request_form.get(f'{table_name}-name'), max_len=255)
        value = clamp_int(request_form.get(f'{table_name}-value'), -999, 999, fallback=0)

        if not name:
            return

        if (ggi.go_get_all('custom_buff', {'character_id': character_id}, count=True) or 0) >= CUSTOM_BUFF_MAX:
            return

        custom_stats = ggi.go_get_all('custom_stat', {'character_id': character_id}) or []
        feats_and_traits = ggi.go_get_all('feat_and_trait', {'character_id': character_id}) or []
        inventory = ggi.go_get_all('inventory', {'character_id': character_id}) or []
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
        ggi.go_add_new('custom_buff', {
            'id': custom_buff_id,
            'name': name,
            'value': value,
            'character_id': character_id,
        })

        for pending_target in pending_table_targets:
            stat_table_id = uuid()
            ggi.go_add_new('custom_buff_to_stat_table', {
                'id': uuid(),
                'custom_buff_id': custom_buff_id,
                'stat_table_name': pending_target['table_name'],
                'stat_table_id': stat_table_id,
                'character_id': character_id,
            })
            for stat_name in pending_target['stats']:
                ggi.go_add_new('stat_table_to_stat', {
                    'id': uuid(),
                    'stat_table_id': stat_table_id,
                    'stat_name': stat_name,
                    'character_id': character_id,
                })

    def update_custom_buff_values(self, character_id: str, buff_id: str, request_form):
        if not is_valid_uuid(buff_id):
            return

        existing_buff = ggi.go_get_one('custom_buff', {'id': buff_id, 'character_id': character_id})
        if not existing_buff:
            return

        table_name = 'custom_buff'
        name = sanitize_str(request_form.get(f'{table_name}-name'), max_len=255)
        value = clamp_int(request_form.get(f'{table_name}-value'), -999, 999, fallback=0)

        if not name:
            return

        custom_stats = ggi.go_get_all('custom_stat', {'character_id': character_id}) or []
        feats_and_traits = ggi.go_get_all('feat_and_trait', {'character_id': character_id}) or []
        inventory = ggi.go_get_all('inventory', {'character_id': character_id}) or []
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
        ggi.go_update('custom_buff', {
            'id': buff_id,
            'name': name,
            'value': value,
            'character_id': character_id,
        })

        # Delete old target mappings
        old_tables = ggi.go_get_all('custom_buff_to_stat_table', {'custom_buff_id': buff_id, 'character_id': character_id}) or []
        for old_table in old_tables:
            old_stat_table_id = old_table.get('stat_table_id')
            if old_stat_table_id:
                for old_stat in ggi.go_get_all('stat_table_to_stat', {'stat_table_id': old_stat_table_id, 'character_id': character_id}) or []:
                    if old_stat.get('id'):
                        ggi.go_delete_it('stat_table_to_stat', {'id': old_stat['id']})
            if old_table.get('id'):
                ggi.go_delete_it('custom_buff_to_stat_table', {'id': old_table['id']})

        # Insert new target mappings
        for pending_target in pending_table_targets:
            stat_table_id = uuid()
            ggi.go_add_new('custom_buff_to_stat_table', {
                'id': uuid(),
                'custom_buff_id': buff_id,
                'stat_table_name': pending_target['table_name'],
                'stat_table_id': stat_table_id,
                'character_id': character_id,
            })
            for stat_name in pending_target['stats']:
                ggi.go_add_new('stat_table_to_stat', {
                    'id': uuid(),
                    'stat_table_id': stat_table_id,
                    'stat_name': stat_name,
                    'character_id': character_id,
                })

    def save_character_values(self, request_form) -> str:
        table_name = 'character'
        character_id = request_form.get(f'{table_name}-id')

        # Reject a tampered/missing character id – fall through to create a new record
        if not is_valid_uuid(character_id):
            character_id = None

        name = sanitize_optional_str(request_form.get(f'{table_name}-name'), max_len=255)
        level = 0
        race = sanitize_optional_str(request_form.get(f'{table_name}-race'), max_len=255)
        background = sanitize_optional_str(request_form.get(f'{table_name}-background'), max_len=255)
        alignment = sanitize_optional_str(request_form.get(f'{table_name}-alignment'), max_len=255)

        def _optional_int(field, fallback=None):
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
        hit_dice= sanitize_optional_str(request_form.get(f'{table_name}-hit_dice'), max_len=255)

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

        if character_id:
            ggi.go_update('character', character)
        else:
            character_id = uuid()
            character['id'] = character_id
            ggi.go_add_new('character', character)

        return character_id

    def save_class_to_character_values(self, character_id: str, request_form):
        table_name = 'class_to_character'

        class_id = request_form.get(f'{table_name}-class_id')
        level_raw = request_form.get(f'{table_name}-level')

        # Validate: class_id must be a known class; level must be 1-20
        if level_raw and class_id:
            level = clamp_int(level_raw, 1, 20, fallback=1)
            existing_class = ggi.go_get_one('class', {'id': class_id})
            if existing_class:
                class_to_character = {
                    "id": uuid(),
                    "character_id": character_id,
                    "class_id": class_id,
                    "level": level,
                }
                ggi.go_add_new('class_to_character', class_to_character)

        for field_name in request_form:
            if field_name.startswith('classes-level-'):
                class_to_character_id = field_name.replace('classes-level-', '')
                new_level_raw = request_form.get(field_name)

                if new_level_raw and is_valid_uuid(class_to_character_id):
                    # Verify this record belongs to the current character
                    existing = ggi.go_get_one('class_to_character', {
                        'id': class_to_character_id,
                        'character_id': character_id,
                    })
                    if existing:
                        ggi.go_update('class_to_character', {
                            'id': class_to_character_id,
                            'level': clamp_int(new_level_raw, 1, 20, fallback=existing.get('level', 1))
                        })

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
            existing_inventory = ggi.go_get_one('inventory', {'id': inventory_id, 'character_id': character_id})
            if not existing_inventory:
                return

            quantity_value = request_form.get(f'inventory-quantity-{inventory_id}')

            if quantity_value is None or str(quantity_value).strip() == '':
                ggi.go_delete_it('inventory', {
                    'id': inventory_id,
                    'character_id': character_id,
                })
                return

            try:
                parsed_quantity = int(quantity_value)
            except (TypeError, ValueError):
                parsed_quantity = existing_inventory.get('quantity', 1)

            if parsed_quantity <= 0:
                ggi.go_delete_it('inventory', {
                    'id': inventory_id,
                    'character_id': character_id,
                })
                return

            ggi.go_update('inventory', {
                'id': inventory_id,
                'name': existing_inventory.get('name'),
                'description': existing_inventory.get('description'),
                'quantity': parsed_quantity,
                'character_id': character_id,
            })

        def step_inventory_by_id(inventory_id: str, step: int):
            existing_inventory = ggi.go_get_one('inventory', {'id': inventory_id, 'character_id': character_id})
            if not existing_inventory:
                return

            current_quantity = existing_inventory.get('quantity')
            try:
                parsed_current_quantity = int(current_quantity)
            except (TypeError, ValueError):
                parsed_current_quantity = 1

            next_quantity = parsed_current_quantity + step
            if next_quantity <= 0:
                ggi.go_delete_it('inventory', {
                    'id': inventory_id,
                    'character_id': character_id,
                })
                return

            ggi.go_update('inventory', {
                'id': inventory_id,
                'name': existing_inventory.get('name'),
                'description': existing_inventory.get('description'),
                'quantity': next_quantity,
                'character_id': character_id,
            })

        if action == 'add' and name:
            if (ggi.go_get_all('inventory', {'character_id': character_id}, count=True) or 0) >= INVENTORY_MAX:
                return
            parsed_quantity = clamp_int(quantity, 1, 9999, fallback=1)
            inventory = {
                "id": uuid(),
                "name": name,
                "description": description,
                "quantity": parsed_quantity,
                "character_id": character_id,
            }

            ggi.go_add_new('inventory', inventory)

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
            existing_feat = ggi.go_get_one('feat_and_trait', {'id': feat_id, 'character_id': character_id})
            if not existing_feat:
                continue
            updated_name = sanitize_optional_str(request_form.get(f'{name_prefix}{feat_id}'), max_len=255)
            updated_desc = sanitize_optional_str(request_form.get(f'{desc_prefix}{feat_id}'), max_len=2000)
            if updated_name:
                ggi.go_update('feat_and_trait', {
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
            if (ggi.go_get_all('feat_and_trait', {'character_id': character_id}, count=True) or 0) >= FEAT_TRAIT_MAX:
                return
            feat_and_trait = {
                "id": feat_and_trait_id,
                "name": name,
                "description": description,
                "character_id": character_id,
            }

            ggi.go_add_new('feat_and_trait', feat_and_trait)

    def update_single_feat(self, character_id: str, feat_id: str, name: str, description: str):
        """Update a single feat/trait and return the updated record, or None."""
        if not is_valid_uuid(feat_id):
            return None
        existing = ggi.go_get_one('feat_and_trait', {'id': feat_id, 'character_id': character_id})
        if not existing:
            return None
        clean_name = sanitize_optional_str(name, max_len=255)
        clean_desc = sanitize_optional_str(description, max_len=2000)
        if not clean_name:
            return existing
        ggi.go_update('feat_and_trait', {
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
        if (ggi.go_get_all('feat_and_trait', {'character_id': character_id}, count=True) or 0) >= FEAT_TRAIT_MAX:
            return None
        clean_desc = sanitize_optional_str(description, max_len=2000)
        feat_id = uuid()
        feat = {
            'id': feat_id,
            'name': clean_name,
            'description': clean_desc,
            'character_id': character_id,
        }
        ggi.go_add_new('feat_and_trait', feat)
        return feat

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

            existing_custom_stat = ggi.go_get_one('custom_stat', {'id': custom_stat_id, 'character_id': character_id})
            if not existing_custom_stat:
                continue

            raw_name = request_form.get(f'{table_name}-name-{custom_stat_id}')
            updated_name_candidate = sanitize_optional_str(raw_name, max_len=255)
            updated_name = updated_name_candidate if updated_name_candidate else existing_custom_stat.get('name')

            updated_value = request_form.get(f'{table_name}-value-{custom_stat_id}')
            parsed_updated_value = parse_optional_int(updated_value, fallback=existing_custom_stat.get('value', 0))

            ggi.go_update('custom_stat', {
                'id': custom_stat_id,
                'name': updated_name,
                'value': parsed_updated_value,
                'character_id': character_id,
            })

        name = sanitize_optional_str(request_form.get(f'{table_name}-name'), max_len=255)
        value = request_form.get(f'{table_name}-value')

        if not name:
            return

        if (ggi.go_get_all('custom_stat', {'character_id': character_id}, count=True) or 0) >= CUSTOM_STAT_MAX:
            return

        parsed_value = parse_optional_int(value, fallback=0)

        custom_stat = {
            "id": uuid(),
            "name": name,
            "value": parsed_value,
            "character_id": character_id,
        }

        ggi.go_add_new('custom_stat', custom_stat)

    def save_ability_values(self, character_id: str, request_form):
        import math
        character = ggi.go_get_one('character', {'id': character_id})
        character_proficiency = 0
        if character:
            character_proficiency = character.get('proficiency', 0)

        for ability in self.ABILITY_TO_SKILL_MAPPING:
            raw_value = request_form.get(f'{ability}-value')
            if not raw_value or str(raw_value).strip() == '':
                continue
            # Ability scores are 1-30 in D&D 5e; clamp to that range
            value = clamp_int(raw_value, 1, 30, fallback=10)

            modifier = math.floor((value - 10) / 2)

            saving_proficient = 0
            if request_form.get(f'{ability}-proficient'):
                if request_form[f"{ability}-proficient"] == "1":
                    saving_proficient = 1

            character_ability = {
                "id": "",
                "character_id": character_id,
                "value": value,
                "modifier": modifier,
                "proficient": int(saving_proficient),
            }

            existing_ability = ggi.go_get_one(ability, {"character_id": character_id})

            if existing_ability:
                ability_id = existing_ability['id']
                character_ability['id'] = ability_id
                ggi.go_update(ability, character_ability)
            else:
                ability_id = uuid()
                character_ability['id'] = ability_id
                ggi.go_add_new(ability, character_ability)

            skills = ggi.go_get_one(f"{ability}_skills", {f"{ability}_id": ability_id})

            modifier_score = modifier
            saving_proficient_score = 0
            if saving_proficient:
                if character and character.get('proficiency'):
                    saving_proficient_score += character_proficiency

            characters_skills = {
                "id": "",
                f"{ability}_id": ability_id,
                "saving_throw": modifier_score + saving_proficient_score,
            }

            for skill in self.ABILITY_TO_SKILL_MAPPING[ability]:
                skill_proficient = 0
                skill_proficient_score = 0
                if request_form.get(f'{ability}_skills-{skill}_proficient'):
                    if request_form[f"{ability}_skills-{skill}_proficient"] == "1":
                        skill_proficient_score += character_proficiency
                        skill_proficient = 1

                characters_skills[skill] = modifier_score + skill_proficient_score
                characters_skills[f"{skill}_proficient"] = int(skill_proficient)

            if skills:
                skill_id = skills['id']
                characters_skills['id'] = skill_id
                ggi.go_update(f"{ability}_skills", characters_skills)
            else:
                skill_id = uuid()
                characters_skills['id'] = skill_id
                ggi.go_add_new(f"{ability}_skills", characters_skills)

    def process_form(self, request_form):
        character_id = self.save_character_values(request_form)
        self.save_class_to_character_values(character_id, request_form)
        self.save_inventory_values(character_id, request_form)
        self.save_feat_and_trait_values(character_id, request_form)
        self.save_custom_stat_values(character_id, request_form)
        self.save_custom_buff_values(character_id, request_form)
        self.save_ability_values(character_id, request_form)
        return character_id


