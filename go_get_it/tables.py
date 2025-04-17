# Data types
from typing import Optional

_id = "TEXT(32) PRIMARY KEY"

def _text(limit: Optional[int] = None):
    if limit is None:
        limit = 255
    return f"TEXT({limit})"

_integer = "INTEGER"
_mediumtext = "MEDIUMTEXT"
_boolean = "INTEGER NOT NULL DEFAULT 0 CHECK (value IN (0, 1))"
_fk = "TEXT"

"""
TABLES = {
    "table_name": {
        "column_name": "data_type",
        "column_name": "data_type",
    }
}
"""

TABLES = {
    "character": {
        "id": _id,
        "name": _text(),
        "level": _integer,
        "race": _text(),
        "background": _text(),
        "alignment": _text(),
        "armour_class": _integer,
        "initiative": _integer,
        "speed": _integer,
        "proficiency": _integer,
        "health_points": _integer,
        "hit_dice": _text(),
        "passive_wisdom": _integer,
        "temporary_hit_points": _integer,
        "xp": _integer,
    },
    "inventory": {
        "id": _id,
        "character_id": _fk,
        "name": _text(),
        "description": _mediumtext,
        "quantity": _integer,
    },
    "class": {
        "id": _id,
        "name": _text(),
    },
    "class_to_character": {
        "id": _id,
        "character_id": _fk,
        "class_id": _integer,
        "level": _integer,
    },
    "feat_and_trait": {
        "id": _id,
        "character_id": _fk,
        "name": _text(),
        "description": _mediumtext,
    },
    "strength": {
        "id": _id,
        "character_id": _fk,
        "value": _integer,
        "modifier": _integer,
        "proficient": _boolean,
    },
    "dexterity": {
        "id": _id,
        "character_id": _fk,
        "value": _integer,
        "modifier": _integer,
        "proficient": _boolean,
    },
    "constitution": {
        "id": _id,
        "character_id": _fk,
        "value": _integer,
        "modifier": _integer,
        "proficient": _boolean,
    },
    "intelligence": {
        "id": _id,
        "character_id": _fk,
        "value": _integer,
        "modifier": _integer,
        "proficient": _boolean,
    },
    "wisdom": {
        "id": _id,
        "character_id": _fk,
        "value": _integer,
        "modifier": _integer,
        "proficient": _boolean,
    },
    "charisma": {
        "id": _id,
        "character_id": _fk,
        "value": _integer,
        "modifier": _integer,
        "proficient": _boolean,
    },
    "strength_skills": {
        "id": _id,
        "strength_id": _fk,
        "saving_throw": _integer,
        "athletics": _integer,
    },
    "dexterity_skills": {
        "id": _id,
        "dexterity_id": _fk,
        "saving_throw": _integer,
        "acrobatics": _integer,
        "sleight_of_hand": _integer,
        "stealth": _integer,
    },
    "constitution_skills": {
        "id": _id,
        "constitution_id": _fk,
        "saving_throw": _integer,
    },
    "intelligence_skills": {
        "id": _id,
        "intelligence_id": _fk,
        "saving_throw": _integer,
        "arcana": _integer,
        "history": _integer,
        "investigation": _integer,
        "nature": _integer,
        "religion": _integer,
    },
    "wisdom_skills": {
        "id": _id,
        "wisdom_id": _fk,
        "saving_throw": _integer,
        "animal_handling": _integer,
        "insight": _integer,
        "medicine": _integer,
        "perception": _integer,
        "survival": _integer,
    },
    "charisma_skills": {
        "id": _id,
        "charisma_id": _fk,
        "saving_throw": _integer,
        "deception": _integer,
        "intimidation": _integer,
        "performance": _integer,
        "persuasion": _integer,
    },
}