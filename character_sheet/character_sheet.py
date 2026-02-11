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
                "passive_wisdom": "number",
                "xp": "number",
                "health_points": "number",
                "hit_dice": "text",
                "temporary_hit_points": "number",
                # Non table fields
                "current_health_points": "number",
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

        """
        {
            table_name: {
                field_name: {
                    field_container_styles: str,
                    input_styles: str,
                    label_styles: str,
                },
                field_name: {
                    field_container_styles: str,
                    input_styles: str,
                    label_styles: str,
                }
            }
        }
        """
        self.field_styles = {
            "character": {
                "name": {
                    "field_container_styles": "char-field field-margins",
                    "input_styles": "char-field-input",
                    "label_styles": "char-field-label",
                },
                "level": {
                    "field_container_styles": "char-field-square field-margins",
                    "input_styles": "char-field-input-square",
                    "label_styles": "char-field-label-square",
                    "disabled": "disabled",
                },
                "race": {
                    "field_container_styles": "char-field field-margins",
                    "input_styles": "char-field-input",
                    "label_styles": "char-field-label",
                },
                "background": {
                    "field_container_styles": "char-field field-margins",
                    "input_styles": "char-field-input",
                    "label_styles": "char-field-label",
                },
                "alignment": {
                    "field_container_styles": "char-field field-margins",
                    "input_styles": "char-field-input",
                    "label_styles": "char-field-label",
                },
                "armour_class": {
                    "field_container_styles": "char-field-square field-margins",
                    "input_styles": "char-field-input-square",
                    "label_styles": "char-field-label-square",
                },
                "initiative": {
                    "field_container_styles": "char-field-square field-margins",
                    "input_styles": "char-field-input-square",
                    "label_styles": "char-field-label-square",
                },
                "speed": {
                    "field_container_styles": "char-field-square field-margins",
                    "input_styles": "char-field-input-square",
                    "label_styles": "char-field-label-square",
                },
                "xp": {
                    "field_name": "XP",
                    "field_container_styles": "char-field-m field-margins",
                    "input_styles": "char-field-input-xp",
                    "label_styles": "char-field-label-xp",
                },
                "proficiency": {
                    "field_container_styles": "char-field-square field-margins",
                    "input_styles": "char-field-input-square",
                    "label_styles": "char-field-label-square",
                },
                "passive_wisdom": {
                    "field_container_styles": "char-field-sm field-margins",
                    "input_styles": "char-field-input-square",
                    "label_styles": "char-field-label-square text-center",
                },
                "health_points": {
                    "field_container_styles": "char-field-square-lg field-margins",
                    "input_styles": "char-field-input-square-lg",
                    "label_styles": "char-field-label-square",
                },
                "hit_dice": {
                    "field_container_styles": "char-field-sm-col field-margins",
                    "input_styles": "char-field-input-square hd-tweaks",
                    "label_styles": "char-field-label-square text-center",
                },
                "temporary_hit_points": {
                    "field_name": "Temp HP",
                    "field_container_styles": "char-field-sm-col field-margins",
                    "input_styles": "char-field-input-square hd-tweaks",
                    "label_styles": "char-field-label-square text-center",
                },
                "current_health_points": {
                    "field_container_styles": "char-field-square-lg field-margins",
                    "input_styles": "char-field-input-square-lg",
                    "label_styles": "char-field-label-square",
                    "disabled": "disabled",
                }
            },
            "strength": {
                "value": {
                    "field_name": "Strength",
                    "field_container_styles": "char-field-square-lg field-margins",
                    "input_styles": "char-field-input-square-lg",
                    "label_styles": "char-field-label-square",
                },
                "modifier": {
                    "field_container_styles": "char-field-sm-col field-margins",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "proficient": {
                    "input_styles": "display-none",
                }
            },
            "dexterity": {
                "value": {
                    "field_name": "Dexterity",
                    "field_container_styles": "char-field-square-lg field-margins",
                    "input_styles": "char-field-input-square-lg",
                    "label_styles": "char-field-label-square",
                },
                "modifier": {
                    "field_container_styles": "char-field-sm-col field-margins",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "proficient": {
                    "input_styles": "display-none",
                }
            },
            "constitution": {
                "value": {
                    "field_name": "Constitution",
                    "field_container_styles": "char-field-square-lg field-margins",
                    "input_styles": "char-field-input-square-lg",
                    "label_styles": "char-field-label-square",
                },
                "modifier": {
                    "field_container_styles": "char-field-sm-col field-margins",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "proficient": {
                    "input_styles": "display-none",
                }
            },
            "intelligence": {
                "value": {
                    "field_name": "Intelligence",
                    "field_container_styles": "char-field-square-lg field-margins",
                    "input_styles": "char-field-input-square-lg",
                    "label_styles": "char-field-label-square",
                },
                "modifier": {
                    "field_container_styles": "char-field-sm-col field-margins",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "proficient": {
                    "input_styles": "display-none",
                }
            },
            "wisdom": {
                "value": {
                    "field_name": "Wisdom",
                    "field_container_styles": "char-field-square-lg field-margins",
                    "input_styles": "char-field-input-square-lg",
                    "label_styles": "char-field-label-square",
                },
                "modifier": {
                    "field_container_styles": "char-field-sm-col field-margins",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "proficient": {
                    "input_styles": "display-none",
                }
            },
            "charisma": {
                "value": {
                    "field_name": "Charisma",
                    "field_container_styles": "char-field-square-lg field-margins",
                    "input_styles": "char-field-input-square-lg",
                    "label_styles": "char-field-label-square",
                },
                "modifier": {
                    "field_container_styles": "char-field-sm-col field-margins",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "proficient": {
                    "input_styles": "display-none",
                }
            },
            "strength_skills": {
                "saving_throw": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "athletics": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "athletics_proficient": {
                    "input_styles": "display-none",
                }
            },

            "dexterity_skills": {
                "saving_throw": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "acrobatics": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "acrobatics_proficient": {
                    "input_styles": "display-none",
                },
                "sleight_of_hand": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "sleight_of_hand_proficient": {
                    "input_styles": "display-none",
                },
                "stealth": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "stealth_proficient": {
                    "input_styles": "display-none",
                },
            },

            "constitution_skills": {
                "saving_throw": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
            },

            "intelligence_skills": {
                "saving_throw": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "arcana": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "arcana_proficient": {
                    "input_styles": "display-none",
                },
                "history": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "history_proficient": {
                    "input_styles": "display-none",
                },
                "investigation": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "investigation_proficient": {
                    "input_styles": "display-none",
                },
                "nature": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "nature_proficient": {
                    "input_styles": "display-none",
                },
                "religion": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "religion_proficient": {
                    "input_styles": "display-none",
                },
            },

            "wisdom_skills": {
                "saving_throw": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "animal_handling": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "animal_handling_proficient": {
                    "input_styles": "display-none",
                },
                "insight": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "insight_proficient": {
                    "input_styles": "display-none",
                },
                "medicine": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "medicine_proficient": {
                    "input_styles": "display-none",
                },
                "perception": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "perception_proficient": {
                    "input_styles": "display-none",
                },
                "survival": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "survival_proficient": {
                    "input_styles": "display-none",
                },
            },
            "charisma_skills": {
                "saving_throw": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "deception": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "deception_proficient": {
                    "input_styles": "display-none",
                },
                "intimidation": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "intimidation_proficient": {
                    "input_styles": "display-none",
                },
                "performance": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "performance_proficient": {
                    "input_styles": "display-none",
                },
                "persuasion": {
                    "field_container_styles": "char-field-sm-col field-margins pointer proficient-hover skill-margin-left",
                    "input_styles": "char-field-input-square no-caret",
                    "label_styles": "char-field-label-square text-center",
                },
                "persuasion_proficient": {
                    "input_styles": "display-none",
                },
            }
        }

    def create_form(self):
        """
        Returns structured data for the character sheet instead of HTML strings.
        This data will be passed to Jinja2 templates for rendering.
        """
        # Get character data
        character = ggi.go_get_one('character', {'id': self.character_id}) if self.character_id else {}

        # Calculate total character level from base + class levels
        if character:
            characters_class_levels = ggi.go_get_all('class_to_character', {'character_id': character.get('id')})
            character_level = character.get('level', 0)

            for char_class in characters_class_levels or []:
                character_level += char_class.get('level', 0)

            character['level'] = character_level

        # Get abilities and skills data
        abilities_data = []
        for ability_name in self.abilities_field_type_mapping:
            ability = ggi.go_get_one(ability_name, {"character_id": self.character_id}) or {}

            # Get skills for this ability
            skills = {}
            if ability.get('id'):
                skills = ggi.go_get_one(f"{ability_name}_skills", {f"{ability_name}_id": ability['id']}) or {}

            # Get skill list for this ability
            skill_list = self.ability_to_skill_mapping.get(ability_name, [])

            abilities_data.append({
                'ability_name': ability_name,
                'ability': ability,
                'skills': skills,
                'skill_list': skill_list
            })

        # Classes
        all_classes = ggi.go_get_all('class') or []
        classes = ggi.go_get_all('class_to_character', {'character_id': self.character_id}) or []

        # Get IDs of classes already assigned to this character
        assigned_class_ids = [char_class['class_id'] for char_class in classes]

        # Filter out classes that are already assigned
        class_options = [c for c in all_classes if c['id'] not in assigned_class_ids]

        # Match class IDs to class names
        for char_class in classes:
            matching_class = next((c for c in all_classes if c['id'] == char_class['class_id']), None)
            if matching_class:
                char_class['class_name'] = matching_class['name']

        # Feats & Traits
        # feats_and_traits = ggi.go_get_all('feat_and_trait', {'character_id': self.character_id}) or []

        # Inventory
        # inventory = ggi.go_get_all('inventory', {'character_id': self.character_id}) or []

        return {
            'character': character,
            'classes': classes,
            'class_options': class_options,
            # 'abilities': abilities_data,
            # 'feats_and_traits': feats_and_traits,
            # 'inventory': inventory
        }

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

            # Handle adding new class
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

            # Handle updating existing class levels
            for field_name in request_form:
                if field_name.startswith('classes-level-'):
                    # Extract the class_to_character ID from field name
                    class_to_character_id = field_name.replace('classes-level-', '')
                    new_level = request_form.get(field_name)

                    if new_level:
                        # Update the existing class level
                        ggi.go_update('class_to_character', {
                            'id': class_to_character_id,
                            'level': new_level
                        })

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


