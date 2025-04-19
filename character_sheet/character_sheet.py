from typing import Optional
from flask import Flask, render_template
from go_get_it.go_get_it import Database
from functions.functions import uuid
from go_get_it.tables import TABLES

app = Flask(__name__)
ggi = Database()

class CharacterSheet:
    # TODO: Add validation
    def __init__(self, character_id: Optional[str] = None):
        self.character_id = character_id
        self.character_field_type_mapping = {
                "id": "hidden",
                "name": "text",
                "level": "number",
                "race": "text",
                "background": "text",
                "alignment": "text",
                "armour_class": "number",
                "initiative": "number",
                "speed": "number",
                "proficiency": "number",
                "health_points": "number",
                "hit_dice": "text",
                "passive_wisdom": "number",
                "temporary_hit_points": "number",
                "xp": "number",
            }

        self.inventory_field_type_mapping = {
                "id": "hidden",
                "character_id": "hidden",
                "name": "text",
                "description": "text",
                "quantity": "number",
            }

        self.character_class_field_type_mapping = {
                "id": "hidden",
                "character_id": "hidden",
                "class_id": "select",
                "level": "number",
        }

        self.feat_and_trait_field_type_mapping = {
                "id": "hidden",
                "character_id": "hidden",
                "name": "text",
                "description": "text",
        }

        self.abilities_field_type_mapping = {
            "strength": {
                "id": "hidden",
                "character_id": "hidden",
                "value": "number",
                "modifier": "number",
                "proficient": "checkbox",
            },
            "dexterity": {
                "id": "hidden",
                "character_id": "hidden",
                "value": "number",
                "modifier": "number",
                "proficient": "checkbox",
            },
            "constitution": {
                "id": "hidden",
                "character_id": "hidden",
                "value": "number",
                "modifier": "number",
                "proficient": "checkbox",
            },
            "intelligence": {
                "id": "hidden",
                "character_id": "hidden",
                "value": "number",
                "modifier": "number",
                "proficient": "checkbox",
            },
            "wisdom": {
                "id": "hidden",
                "character_id": "hidden",
                "value": "number",
                "modifier": "number",
                "proficient": "checkbox",
            },
            "charisma": {
                "id": "hidden",
                "character_id": "hidden",
                "value": "number",
                "modifier": "number",
                "proficient": "checkbox",
            },
        }

        self.skills_field_type_mapping = {
            "strength_skills": {
                "id": "hidden",
                "strength_id": "hidden",
                "saving_throw": "number",
                "athletics": "number",
                "athletics_proficient": "checkbox",
            },
            "dexterity_skills": {
                "id": "hidden",
                "dexterity_id": "hidden",
                "saving_throw": "number",
                "acrobatics": "number",
                "acrobatics_proficient": "checkbox",
                "sleight_of_hand": "number",
                "sleight_of_hand_proficient": "checkbox",
                "stealth": "number",
                "stealth_proficient": "checkbox",
            },
            "constitution_skills": {
                "id": "hidden",
                "constitution_id": "hidden",
                "saving_throw": "number",
            },
            "intelligence_skills": {
                "id": "hidden",
                "intelligence_id": "hidden",
                "saving_throw": "number",
                "arcana": "number",
                "arcana_proficient": "checkbox",
                "history": "number",
                "history_proficient": "checkbox",
                "investigation": "number",
                "investigation_proficient": "checkbox",
                "nature": "number",
                "nature_proficient": "checkbox",
                "religion": "number",
                "religion_proficient": "checkbox",
            },
            "wisdom_skills": {
                "id": "hidden",
                "wisdom_id": "hidden",
                "saving_throw": "number",
                "animal_handling": "number",
                "animal_handling_proficient": "checkbox",
                "insight": "number",
                "insight_proficient": "checkbox",
                "medicine": "number",
                "medicine_proficient": "checkbox",
                "perception": "number",
                "perception_proficient": "checkbox",
                "survival": "number",
                "survival_proficient": "checkbox",
            },
            "charisma_skills": {
                "id": "hidden",
                "charisma_id": "hidden",
                "saving_throw": "number",
                "deception": "number",
                "deception_proficient": "checkbox",
                "intimidation": "number",
                "intimidation_proficient": "checkbox",
                "performance": "number",
                "performance_proficient": "checkbox",
                "persuasion": "number",
                "persuasion_proficient": "checkbox",
            },
        }

        self.ability_to_skill_mapping = {
            "strength": ["athletics"],
            "dexterity": ["acrobatics", "sleight_of_hand", "stealth"],
            "constitution": [],
            "intelligence": ["arcana", "history", "investigation", "nature", "religion"],
            "wisdom": ["animal_handling", "insight", "medicine", "perception", "survival"],
            "charisma": ["deception", "intimidation", "performance", "persuasion"],
        }

    def create_form(self):
        form = []
        # Character
        form.append("<h3>Character</h3>")
        character = ggi.go_get_one('character', {'id': self.character_id}) if self.character_id else None

        # Work out characters level
        if character:
            characters_class_levels = ggi.go_get_all('class_to_character', {'character_id': character['id']})
            character_level = character['level']

            for char_class in characters_class_levels or []:
                character_level += char_class['level']

            character['level'] = character_level

        character_form = self._build_form('character', self.character_field_type_mapping, character)
        form.append(character_form)

        # Class
        form.append("<h3>Classes</h3>")
        classes = ggi.go_get_all('class') or []
        class_options = [{"": "Please select a class"}]
        for c in classes:
            class_options.append({c['id']: c['name']})

        character_class_form = self._build_form('class_to_character', self.character_class_field_type_mapping, options=class_options)
        form.append(character_class_form)

        # Feats & Traits
        form.append("<h3>Feats & Traits</h3>")
        feats_form = self._build_form('feat_and_trait', self.feat_and_trait_field_type_mapping)
        form.append(feats_form)

        # Inventory
        form.append("<h3>Inventory</h3>")
        inventory_form = self._build_form('inventory', self.inventory_field_type_mapping)
        form.append(inventory_form)

        # Abilities
        form.append("<h3>Abilities</h3>")
        for ability in self.abilities_field_type_mapping:
            form.append(f"<h4>{ability}</h4>")
            existing_ability = ggi.go_get_one(ability, {"character_id": self.character_id})
            ability_form = self._build_form(ability, self.abilities_field_type_mapping[ability], existing_ability)
            form.append(ability_form)

            # Skills
            ability_skills = None
            if existing_ability:
                ability_skills = ggi.go_get_one(f"{ability}_skills", {f"{ability}_id": existing_ability['id']})

            skill_form = self._build_form(f"{ability}_skills", self.skills_field_type_mapping[f"{ability}_skills"], ability_skills)
            form.append(skill_form)


        return "".join(form)

    def _build_form(
        self,
        table_name: str,
        field_types: dict,
        data: Optional[dict] = None,
        skip_fields: list = [],
        options: Optional[list[dict[str, str]]] = []):
        # Build from character table
            table = TABLES[table_name]
            fields_list = []
            for k in table.keys():
                if k in skip_fields:
                    continue
                fields_list.append(k)

            field_type_mapping = field_types

            fields = []
            selection = ""
            for field in fields_list:
                field_value = data[field] if data else ""
                field_type = field_type_mapping.get(field, "text")

                if field_type == "select":
                    for opt in options or []:
                        for k, v in opt.items():
                            selection += f'<option value="{k}">{v}</option>'

                create_field = render_template('field.html', field=field, field_type=field_type, field_value=field_value, table=table_name, options=selection)
                fields.append(create_field)

            return "".join(fields)

    def process_form(self, request_form):
        def _save_character_values():
            table_name = 'character'
            character_id = request_form.get(f'{table_name}-id')
            name = request_form.get(f'{table_name}-name')
            level = 0 # request_form.get(f'{table_name}-level')
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

            # Build character values to save
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

        def _save_class_to_character_values(character_id: str):
            table_name = 'class_to_character'
            character_id = character_id
            class_id = request_form.get(f'{table_name}-class_id')
            level = request_form.get(f'{table_name}-level')

            if level:
                class_to_character = {
                    "id": uuid(),
                    "character_id": character_id,
                    "class_id": class_id,
                    "level": level,
                }

                ggi.go_add_new('class_to_character', class_to_character)

        def _save_inventory_values(character_id: str):
            table_name = 'inventory'
            inventory_id = uuid()
            name = request_form.get(f'{table_name}-name')
            description = request_form.get(f'{table_name}-description')
            quantity = request_form.get(f'{table_name}-quantity')

            # Only trigger save if there is a name and quantity
            if name:
                inventory = {
                    "id": inventory_id,
                    "name": name,
                    "description": description,
                    "quantity": quantity or 1,
                    "character_id": character_id,
                }

                ggi.go_add_new('inventory', inventory)

        def _save_feat_and_trait_values(character_id: str):
            table_name = 'feat_and_trait'
            feat_and_trait_id = uuid()
            name = request_form.get(f'{table_name}-name')
            description = request_form.get(f'{table_name}-description')

            # Only trigger save if there is a name
            if name:
                feat_and_trait = {
                    "id": feat_and_trait_id,
                    "name": name,
                    "description": description,
                    "character_id": character_id,
                }

                ggi.go_add_new('feat_and_trait', feat_and_trait)

        def _save_ability_values(character_id: str):
            import math
            character = ggi.go_get_one('character', {'id': character_id})
            character_proficiency = 0
            if character:
                character_proficiency = character.get('proficiency', 0)

            abilities =[
                "strength",
                "dexterity",
                "constitution",
                "intelligence",
                "wisdom",
                "charisma",
            ]
            # TODO: rename proficient field (everwhere) to be saving throw proficient
            for ability in abilities:
                value = request_form.get(f'{ability}-value')
                if value:
                    value = int(value)
                else:
                    continue
                # Calc the ability modifier
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

                # Calc the skill scores based on the ability modifiers
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

                for skill in self.ability_to_skill_mapping.get(ability, []):
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

        character_id = _save_character_values()
        _save_class_to_character_values(character_id)
        _save_inventory_values(character_id)
        _save_feat_and_trait_values(character_id)
        _save_ability_values(character_id)
        return character_id


