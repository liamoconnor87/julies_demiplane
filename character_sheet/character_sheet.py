from typing import Optional
from go_get_it.go_get_it import Database
from functions.functions import uuid
ggi = Database()

class CharacterSheet:
    ABILITY_TO_SKILL_MAPPING = {
        "strength": ["athletics"],
        "dexterity": ["acrobatics", "sleight_of_hand", "stealth"],
        "constitution": [],
        "intelligence": ["arcana", "history", "investigation", "nature", "religion"],
        "wisdom": ["animal_handling", "insight", "medicine", "perception", "survival"],
        "charisma": ["deception", "intimidation", "performance", "persuasion"],
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
        # inventory = ggi.go_get_all('inventory', {'character_id': self.character_id}) or []

        return {
            'character': character,
            'classes': classes,
            'class_options': class_options,
            'abilities': abilities_data,
            'feats_and_traits': feats_and_traits,
            # 'inventory': inventory
        }

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
        inventory_id = uuid()
        name = request_form.get(f'{table_name}-name')
        description = request_form.get(f'{table_name}-description')
        quantity = request_form.get(f'{table_name}-quantity')

        if name:
            inventory = {
                "id": inventory_id,
                "name": name,
                "description": description,
                "quantity": quantity or 1,
                "character_id": character_id,
            }

            ggi.go_add_new('inventory', inventory)

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
        self.save_ability_values(character_id, request_form)
        return character_id


