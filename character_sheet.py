from typing import Optional
from flask import Flask, render_template
from go_get_it import Database
from functions import uuid
from tables import TABLES

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
                "class_id": "hidden",
                "level": "number",
        }

    def create_form(self):
        form = []
        # Character
        form.append("<h3>Character</h3>")
        character = ggi.go_get_one('character', {'id': self.character_id}) if self.character_id else None
        character_form = self._build_form('character', self.character_field_type_mapping, character)
        form.append(character_form)

        #Class
        form.append("<h3>Classes</h3>")
        character_class_form = self._build_form('class_to_character', self.character_class_field_type_mapping)
        form.append(character_class_form)

        # Inventory
        form.append("<h3>Inventory</h3>")
        inventory_form = self._build_form('inventory', self.inventory_field_type_mapping)
        form.append(inventory_form)

        return "".join(form)

    def _build_form(self, table_name: str, field_types: dict, data: Optional[dict] = None, skip_fields: list = []):
        # Build from character table
            table = TABLES[table_name]
            fields_list = []
            for k in table.keys():
                if k in skip_fields:
                    continue
                fields_list.append(k)

            field_type_mapping = field_types

            fields = []
            for field in fields_list:
                field_value = data[field] if data else ""
                field_type = field_type_mapping.get(field, "text")

                create_field = render_template('field.html', field=field, field_type=field_type, field_value=field_value, table=table_name)
                fields.append(create_field)

            return "".join(fields)

    def process_form(self, request_form):
        def _save_character_values():
            table_name = 'character'
            character_id = request_form.get(f'{table_name}-id')
            name = request_form.get(f'{table_name}-name')
            level = request_form.get(f'{table_name}-level')
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

            return inventory_id

        character_id = _save_character_values()
        _save_inventory_values(character_id)
        return character_id


