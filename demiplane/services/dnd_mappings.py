ABILITY_TO_SKILL_MAPPING = {
    'strength': ['athletics'],
    'dexterity': ['acrobatics', 'sleight_of_hand', 'stealth'],
    'constitution': [],
    'intelligence': ['arcana', 'history', 'investigation', 'nature', 'religion'],
    'wisdom': ['animal_handling', 'insight', 'medicine', 'perception', 'survival'],
    'charisma': ['deception', 'intimidation', 'performance', 'persuasion'],
}

CLASS_HIT_DIE_MAPPING = {
    'artificer': 8, 'barbarian': 12, 'bard': 8, 'cleric': 8, 'druid': 8,
    'fighter': 10, 'monk': 8, 'paladin': 10, 'ranger': 10, 'rogue': 8,
    'sorcerer': 6, 'warlock': 8, 'wizard': 6,
}

SPELL_LEVEL_LABELS = {
    0: 'Cantrips', 1: '1st Level', 2: '2nd Level', 3: '3rd Level',
    4: '4th Level', 5: '5th Level', 6: '6th Level', 7: '7th Level',
    8: '8th Level', 9: '9th Level',
}

# The only classes that name any spell in the 5etools data. Barbarian, fighter,
# monk and rogue are selectable (CLASS_HIT_DIE_MAPPING) but appear on zero
# spells, so they're deliberately absent here -- see spell_filter_class_names.
SPELLCASTING_CLASSES = {
    'artificer', 'bard', 'cleric', 'druid', 'paladin',
    'ranger', 'sorcerer', 'warlock', 'wizard',
}


def spell_filter_class_names(classes: list[dict]) -> list[str]:
    """Class names to render as spell filter pills for a character.

    Non-casting classes are dropped. The pills render active, and a pill that
    matches no spell filters the whole list down to nothing, so a pure fighter
    would open the Spells tab to an empty page. Dropping them leaves no class
    pill at all, which applySpellFilters reads as "don't filter by class".

    Class rows are seeded lowercase (db/seed.py) but spell.classes stores
    proper-cased names from the 5etools data, so capitalize to make them match.

    Args:
        classes: class rows as returned by CharacterSheet.fetch_classes_data.

    Returns:
        Sorted, de-duplicated, proper-cased names of the character's casting classes.
    """
    return sorted({
        c['class_name'].capitalize()
        for c in classes
        if c.get('class_name', '').lower() in SPELLCASTING_CLASSES
    })
