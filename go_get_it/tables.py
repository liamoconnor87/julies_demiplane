# Data types
from typing import Optional

_id = "TEXT(32) PRIMARY KEY"

def _text(limit: Optional[int] = None):
    if limit is None:
        limit = 255
    return f"TEXT({limit})"

_integer = "INTEGER"
_mediumtext = "MEDIUMTEXT"
_boolean = "INTEGER NOT NULL DEFAULT 0"
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
        "passive_wisdom": _integer,
        "xp": _integer,
        "health_points": _integer,
        "hit_dice": _text(),
        "temporary_hit_points": _integer,
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
        "class_id": _fk,
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
        "proficient": _boolean,
        "modifier": _integer,
    },
    "constitution": {
        "id": _id,
        "character_id": _fk,
        "value": _integer,
        "proficient": _boolean,
        "modifier": _integer,
    },
    "intelligence": {
        "id": _id,
        "character_id": _fk,
        "value": _integer,
        "proficient": _boolean,
        "modifier": _integer,
    },
    "wisdom": {
        "id": _id,
        "character_id": _fk,
        "value": _integer,
        "proficient": _boolean,
        "modifier": _integer,
    },
    "charisma": {
        "id": _id,
        "character_id": _fk,
        "value": _integer,
        "proficient": _boolean,
        "modifier": _integer,
    },
    "strength_skills": {
        "id": _id,
        "saving_throw": _integer,
        "athletics": _integer,
        "athletics_proficient": _boolean,
        "strength_id": _fk,
    },
    "dexterity_skills": {
        "id": _id,
        "saving_throw": _integer,
        "acrobatics": _integer,
        "acrobatics_proficient": _boolean,
        "sleight_of_hand": _integer,
        "sleight_of_hand_proficient": _boolean,
        "stealth": _integer,
        "stealth_proficient": _boolean,
        "dexterity_id": _fk,
    },
    "constitution_skills": {
        "id": _id,
        "saving_throw": _integer,
        "constitution_id": _fk,
    },
    "intelligence_skills": {
        "id": _id,
        "saving_throw": _integer,
        "arcana": _integer,
        "arcana_proficient": _boolean,
        "history": _integer,
        "history_proficient": _boolean,
        "investigation": _integer,
        "investigation_proficient": _boolean,
        "nature": _integer,
        "nature_proficient": _boolean,
        "religion": _integer,
        "religion_proficient": _boolean,
        "intelligence_id": _fk,
    },
    "wisdom_skills": {
        "id": _id,
        "saving_throw": _integer,
        "animal_handling": _integer,
        "animal_handling_proficient": _boolean,
        "insight": _integer,
        "insight_proficient": _boolean,
        "medicine": _integer,
        "medicine_proficient": _boolean,
        "perception": _integer,
        "perception_proficient": _boolean,
        "survival": _integer,
        "survival_proficient": _boolean,
        "wisdom_id": _fk,
    },
    "charisma_skills": {
        "id": _id,
        "saving_throw": _integer,
        "deception": _integer,
        "deception_proficient": _boolean,
        "intimidation": _integer,
        "intimidation_proficient": _boolean,
        "performance": _integer,
        "performance_proficient": _boolean,
        "persuasion": _integer,
        "persuasion_proficient": _boolean,
        "charisma_id": _fk,
    },
}