"""
{
    table_name: {
        value: field,
        value: field
    }
}
"""
from misc.admin import ADMIN_SEED


SEED = {
    "class": {
        "artificer": "name",
        "barbarian": "name",
        "bard": "name",
        "cleric": "name",
        "druid": "name",
        "fighter": "name",
        "monk": "name",
        "paladin": "name",
        "ranger": "name",
        "rogue": "name",
        "sorcerer": "name",
        "warlock": "name",
        "wizard": "name"
    },
}

# Full-row seeds (tables where each entry needs multiple fields)
SEED_ROWS = ADMIN_SEED
