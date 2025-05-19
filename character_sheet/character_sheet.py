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
        form = []
        # Character
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

        # # Class
        # form.append("<h3>Classes</h3>")
        # classes = ggi.go_get_all('class') or []
        # class_options = [{"": "Please select a class"}]
        # for c in classes:
        #     class_options.append({c['id']: c['name']})

        # character_class_form = self._build_form('class_to_character', self.character_class_field_type_mapping, options=class_options)
        # form.append(character_class_form)

        # Abilities
        form.append("<h3>Abilities & Skills</h3>")
        for ability in self.abilities_field_type_mapping:
            existing_ability = ggi.go_get_one(ability, {"character_id": self.character_id})
            ability_form = self._build_form(ability, self.abilities_field_type_mapping[ability], existing_ability)
            form.append(ability_form)

            # Skills
            ability_skills = None
            if existing_ability:
                ability_skills = ggi.go_get_one(f"{ability}_skills", {f"{ability}_id": existing_ability['id']})

            skill_form = self._build_form(f"{ability}_skills", self.skills_field_type_mapping[f"{ability}_skills"], ability_skills)
            form.append(skill_form)

        # # Feats & Traits
        # form.append("<h3>Feats & Traits</h3>")
        # feats_form = self._build_form('feat_and_trait', self.feat_and_trait_field_type_mapping)
        # form.append(feats_form)

        # # Inventory
        # form.append("<h3>Inventory</h3>")
        # inventory_form = self._build_form('inventory', self.inventory_field_type_mapping)
        # form.append(inventory_form)

        return "".join(form)

    def _build_form(
        self,
        table_name: str,
        field_types: dict,
        data: Optional[dict] = None,
        skip_fields: list = [],
        options: Optional[list[dict[str, str]]] = []):
        # Get the fields from the table
        table = TABLES[table_name]
        fields_list = []
        for k in table.keys():
            if k in skip_fields:
                continue
            fields_list.append(k)

        # Add some custom fields
        if table_name == "character":
            fields_list.append("current_health_points")

        field_type_mapping = field_types

        fields = []

        selection = ""
        for field in fields_list:
            field_template = "field.html"
            field_name = field.replace("_", " ").title()
            field_container_styles = ""
            input_styles = ""
            label_styles = ""
            disabled = ""

            field_value = data.get(field, "") if data else ""
            field_type = field_type_mapping.get(field, "text")

            # NOTE: THIS IS WRONG - DOES NOT SPECIFY WHAT FIELD
            if field_type == "select":
                for opt in options or []:
                    for k, v in opt.items():
                        selection += f'<option value="{k}">{v}</option>'

            if table_name == "character":
                if field in ("id", "armour_class", "health_points"):
                    if field == "id":
                        fields.append("<h4>Character</h4>")
                    if field == "armour_class":
                        fields.append("<h4>Combat</h4>")

                    fields.append("<div class='row'>")

                if field in ("hit_dice"):
                    fields.append("<div class='col grp-char-fields'>")

            if table_name == "strength" or table_name == "dexterity" or table_name == "constitution" or table_name == "intelligence" or table_name == "wisdom" or table_name == "charisma":
                if field == "id":
                    fields.append("<div class='row'>")

                if field == "modifier":
                    fields.append("<div class='col grp-char-fields'>")

            if table_name == "strength_skills":
                if field == "athletics":
                    fields.append("<div class='col grp-char-fields'>")

            if table_name == "dexterity_skills":
                if field == "acrobatics":
                    fields.append("<div class='col grp-char-fields'>")
                if field == "stealth":
                    fields.append("<div class='col grp-char-fields'>")

            if table_name == "intelligence_skills":
                if field == "arcana":
                    fields.append("<div class='col grp-char-fields'>")
                if field == "investigation":
                    fields.append("<div class='col grp-char-fields'>")
                if field == "religion":
                    fields.append("<div class='col grp-char-fields'>")

            if table_name == "wisdom_skills":
                if field == "animal_handling":
                    fields.append("<div class='col grp-char-fields'>")

                if field == "medicine":
                    fields.append("<div class='col grp-char-fields'>")

                if field == "survival":
                    fields.append("<div class='col grp-char-fields'>")

            if table_name == "charisma_skills":
                if field == "deception":
                    fields.append("<div class='col grp-char-fields'>")

                if field == "performance":
                    fields.append("<div class='col grp-char-fields'>")



            # Get any styles for the field
            field_styles = self.field_styles.get(table_name, {}).get(field, {})
            if field_styles:
                field_name = field_styles.get("field_name", field_name)
                field_container_styles = field_styles.get("field_container_styles", "")
                input_styles = field_styles.get("input_styles", "")
                label_styles = field_styles.get("label_styles", "")
                disabled = field_styles.get("disabled", "")

            create_field = render_template(
                field_template,
                field=field,
                field_name=field_name,
                field_type=field_type,
                field_value=field_value,
                table_name=table_name,
                options=selection,
                disabled=disabled,
                field_container_styles=field_container_styles,
                input_styles=input_styles,
                label_styles=label_styles,
                )

            fields.append(create_field)

            # Close elements
            if table_name == "character":
                if field in ("alignment", "xp", "temporary_hit_points", "current_health_points"):
                    fields.append("</div>")

                    if field in ("alignment", "current_health_points"):
                        fields.append("<br>")

            if table_name == "strength_skills":
                if field == "saving_throw":
                    fields.append("</div>")

                if field == "athletics":
                    fields.append("</div>")
                # Close the row on the last field
                if field == "strength_id":
                    fields.append("</div><br>")

            if table_name == "dexterity_skills":
                if field == "saving_throw":
                    fields.append("</div>")

                if field == "sleight_of_hand":
                    fields.append("</div>")

                if field == "stealth":
                    fields.append("</div>")
                # Close the row on the last field
                if field == "dexterity_id":
                    fields.append("</div><br>")

            if table_name == "constitution_skills":
                if field == "saving_throw":
                    fields.append("</div>")
                # Close the row on the last field
                if field == "constitution_id":
                    fields.append("</div><br>")

            if table_name == "intelligence_skills":
                if field == "saving_throw":
                    fields.append("</div>")

                if field == "history":
                    fields.append("</div>")

                if field == "nature":
                    fields.append("</div>")

                if field == "religion":
                    fields.append("</div>")
                # Close the row on the last field
                if field == "intelligence_id":
                    fields.append("</div><br>")

            if table_name == "wisdom_skills":
                if field == "saving_throw":
                    fields.append("</div>")

                if field == "insight":
                    fields.append("</div>")

                if field == "perception":
                    fields.append("</div>")

                if field == "survival":
                    fields.append("</div>")
                # Close the row on the last field
                if field == "wisdom_id":
                    fields.append("</div><br>")

            if table_name == "charisma_skills":
                if field == "saving_throw":
                    fields.append("</div>")

                if field == "intimidation":
                    fields.append("</div>")

                if field == "persuasion":
                    fields.append("</div>")
                # Close the row on the last field
                if field == "charisma_id":
                    fields.append("</div><br>")
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


