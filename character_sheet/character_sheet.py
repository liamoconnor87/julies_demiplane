from typing import Optional
from go_get_it.go_get_it import GoGetDB
from functions.functions import uuid
ggi = GoGetDB()

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
            "xp",
            "health_points",
            "temporary_hit_points",
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

        buff_target_options = self._get_buff_target_options(custom_stats)
        custom_buffs = self._get_custom_buffs()
        self._apply_custom_buffs(character, abilities_data, custom_stats, custom_buffs)

        return {
            'character': character,
            'classes': classes,
            'class_options': class_options,
            'abilities': abilities_data,
            'feats_and_traits': feats_and_traits,
            'inventory': inventory,
            'custom_stats': custom_stats,
            'custom_buffs': custom_buffs,
            'buff_target_options': buff_target_options,
        }

    def _parse_int(self, value, fallback=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _get_buff_target_options(self, custom_stats):
        options = {
            table_name: columns[:]
            for table_name, columns in self.BUFF_TARGET_TABLE_COLUMNS.items()
        }

        custom_stat_names = []
        for custom_stat in custom_stats or []:
            stat_name = str(custom_stat.get('name') or '').strip()
            if not stat_name:
                continue
            if stat_name not in custom_stat_names:
                custom_stat_names.append(stat_name)

        custom_stat_names.sort()
        options['custom_stat'] = custom_stat_names
        return options

    def _get_custom_buffs(self):
        custom_buffs = ggi.go_get_all('custom_buff', {'character_id': self.character_id}) or []
        custom_buff_tables = ggi.go_get_all('custom_buff_to_stat_table', {'character_id': self.character_id}) or []
        table_to_stats = ggi.go_get_all('stat_table_to_stat', {'character_id': self.character_id}) or []

        stats_by_table_id = {}
        for stat_record in table_to_stats:
            table_id = stat_record.get('stat_table_id')
            if not table_id:
                continue

            stat_name = str(stat_record.get('stat_name') or '').strip()
            if not stat_name:
                continue

            if table_id not in stats_by_table_id:
                stats_by_table_id[table_id] = []

            stats_by_table_id[table_id].append(stat_name)

        table_targets_by_buff_id = {}
        for table_mapping in custom_buff_tables:
            custom_buff_id = table_mapping.get('custom_buff_id')
            table_name = table_mapping.get('stat_table_name')
            table_id = table_mapping.get('stat_table_id')

            if not custom_buff_id or not table_name or not table_id:
                continue

            if custom_buff_id not in table_targets_by_buff_id:
                table_targets_by_buff_id[custom_buff_id] = []

            table_targets_by_buff_id[custom_buff_id].append({
                'stat_table_name': table_name,
                'stat_table_id': table_id,
                'stat_names': stats_by_table_id.get(table_id, []),
            })

        for custom_buff in custom_buffs:
            custom_buff['targets'] = table_targets_by_buff_id.get(custom_buff.get('id'), [])

        return custom_buffs

    def _apply_custom_buffs(self, character, abilities_data, custom_stats, custom_buffs):
        if not custom_buffs:
            return

        abilities_by_name = {
            ability_data.get('ability_name'): ability_data.get('ability')
            for ability_data in abilities_data
        }
        skills_by_table = {
            f"{ability_data.get('ability_name')}_skills": ability_data.get('skills')
            for ability_data in abilities_data
        }
        custom_stats_by_name = {
            str(custom_stat.get('name') or '').strip(): custom_stat
            for custom_stat in custom_stats
        }

        for custom_buff in custom_buffs:
            adjustment_value = self._parse_int(custom_buff.get('value'), 0)
            if adjustment_value == 0:
                continue

            for target_group in custom_buff.get('targets', []):
                stat_table_name = target_group.get('stat_table_name')
                stat_names = target_group.get('stat_names') or []

                if stat_table_name == 'character' and character:
                    for stat_name in stat_names:
                        if stat_name not in character:
                            continue
                        current_value = self._parse_int(character.get(stat_name), 0)
                        character[stat_name] = current_value + adjustment_value
                    continue

                if stat_table_name in abilities_by_name:
                    ability_data = abilities_by_name.get(stat_table_name) or {}
                    for stat_name in stat_names:
                        if stat_name not in ability_data:
                            continue
                        current_value = self._parse_int(ability_data.get(stat_name), 0)
                        ability_data[stat_name] = current_value + adjustment_value
                    continue

                if stat_table_name in skills_by_table:
                    skills_data = skills_by_table.get(stat_table_name) or {}
                    for stat_name in stat_names:
                        if stat_name not in skills_data:
                            continue
                        current_value = self._parse_int(skills_data.get(stat_name), 0)
                        skills_data[stat_name] = current_value + adjustment_value
                    continue

                if stat_table_name == 'custom_stat':
                    for stat_name in stat_names:
                        custom_stat = custom_stats_by_name.get(str(stat_name or '').strip())
                        if not custom_stat:
                            continue
                        current_value = self._parse_int(custom_stat.get('value'), 0)
                        custom_stat['value'] = current_value + adjustment_value

        if character:
            character['current_health_points'] = self._parse_int(character.get('health_points'), 0) + self._parse_int(character.get('temporary_hit_points'), 0)

    def save_custom_buff_values(self, character_id: str, request_form):
        table_name = 'custom_buff'
        name = str(request_form.get(f'{table_name}-name') or '').strip()
        value = self._parse_int(request_form.get(f'{table_name}-value'), 0)

        if not name:
            return

        custom_stats = ggi.go_get_all('custom_stat', {'character_id': character_id}) or []
        buff_target_options = self._get_buff_target_options(custom_stats)

        selected_tables = []
        table_field_prefix = f'{table_name}-table-'
        for field_name in request_form:
            if not field_name.startswith(table_field_prefix):
                continue

            table_name_value = field_name.replace(table_field_prefix, '')
            if table_name_value in buff_target_options:
                selected_tables.append(table_name_value)

        if not selected_tables:
            return

        pending_table_targets = []

        for selected_table in selected_tables:
            selected_stats = []
            stat_field_prefix = f'{table_name}-stat-{selected_table}-'
            for field_name in request_form:
                if not field_name.startswith(stat_field_prefix):
                    continue

                stat_value = str(request_form.get(field_name) or '').strip()
                if not stat_value:
                    continue

                if stat_value not in buff_target_options.get(selected_table, []):
                    continue

                if stat_value not in selected_stats:
                    selected_stats.append(stat_value)

            if not selected_stats:
                continue

            pending_table_targets.append({
                'table_name': selected_table,
                'stats': selected_stats,
            })

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

    def save_character_values(self, request_form):
        table_name = 'character'
        character_id = request_form.get(f'{table_name}-id')
        name = request_form.get(f'{table_name}-name')
        level = 0
        race = request_form.get(f'{table_name}-race')
        background = request_form.get(f'{table_name}-background')
        alignment = request_form.get(f'{table_name}-alignment')
        armour_class = request_form.get(f'{table_name}-armour_class')
        initiative = request_form.get(f'{table_name}-initiative')
        speed = request_form.get(f'{table_name}-speed')
        proficiency = request_form.get(f'{table_name}-proficiency')
        health_points = request_form.get(f'{table_name}-health_points')
        hit_dice = request_form.get(f'{table_name}-hit_dice')
        passive_wisdom = request_form.get(f'{table_name}-passive_wisdom')
        temporary_hit_points = request_form.get(f'{table_name}-temporary_hit_points')
        xp = request_form.get(f'{table_name}-xp')

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
        level = request_form.get(f'{table_name}-level')

        if level and class_id:
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
                new_level = request_form.get(field_name)

                if new_level:
                    ggi.go_update('class_to_character', {
                        'id': class_to_character_id,
                        'level': new_level
                    })

    def save_inventory_values(self, character_id: str, request_form):
        table_name = 'inventory'
        name = request_form.get(f'{table_name}-name')
        description = request_form.get(f'{table_name}-description')
        quantity = request_form.get(f'{table_name}-quantity')
        action = request_form.get('inventory-action')
        update_id = request_form.get('inventory-update-id')
        step_value = request_form.get('inventory-step')

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
            inventory = {
                "id": uuid(),
                "name": name,
                "description": description,
                "quantity": quantity or 1,
                "character_id": character_id,
            }

            ggi.go_add_new('inventory', inventory)

        if action == 'update' and update_id:
            update_inventory_by_id(update_id)
            return

        if action == 'step' and update_id:
            try:
                parsed_step = int(step_value) if step_value is not None else 0
            except (TypeError, ValueError):
                parsed_step = 0

            if parsed_step != 0:
                step_inventory_by_id(update_id, parsed_step)
            return

        if action:
            return

        for field_name in request_form:
            if not field_name.startswith('inventory-quantity-'):
                continue

            inventory_id = field_name.replace('inventory-quantity-', '')
            update_inventory_by_id(inventory_id)

    def save_feat_and_trait_values(self, character_id: str, request_form):
        table_name = 'feat_and_trait'
        feat_and_trait_id = uuid()
        name = request_form.get(f'{table_name}-name')
        description = request_form.get(f'{table_name}-description')

        if name:
            feat_and_trait = {
                "id": feat_and_trait_id,
                "name": name,
                "description": description,
                "character_id": character_id,
            }

            ggi.go_add_new('feat_and_trait', feat_and_trait)

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
            existing_custom_stat = ggi.go_get_one('custom_stat', {'id': custom_stat_id, 'character_id': character_id})
            if not existing_custom_stat:
                continue

            updated_name = request_form.get(f'{table_name}-name-{custom_stat_id}')
            if updated_name is None or str(updated_name).strip() == '':
                updated_name = existing_custom_stat.get('name')

            updated_value = request_form.get(f'{table_name}-value-{custom_stat_id}')
            try:
                parsed_updated_value = int(updated_value) if updated_value is not None and str(updated_value).strip() != '' else 0
            except (TypeError, ValueError):
                parsed_updated_value = existing_custom_stat.get('value', 0)

            ggi.go_update('custom_stat', {
                'id': custom_stat_id,
                'name': updated_name,
                'value': parsed_updated_value,
                'character_id': character_id,
            })

        name = request_form.get(f'{table_name}-name')
        value = request_form.get(f'{table_name}-value')

        if not name:
            return

        try:
            parsed_value = int(value) if value is not None and str(value).strip() != '' else 0
        except (TypeError, ValueError):
            parsed_value = 0

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
            value = request_form.get(f'{ability}-value')
            if value:
                value = int(value)
            else:
                continue

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


