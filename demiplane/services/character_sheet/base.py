from typing import Optional

from go_get_it.go_get_it import GoGetDB
from demiplane.services import guest_character as guest_session
from demiplane.services.dnd_mappings import ABILITY_TO_SKILL_MAPPING, CLASS_HIT_DIE_MAPPING

from .constants import FEAT_TRAIT_MAX, INVENTORY_MAX, CUSTOM_STAT_MAX, CUSTOM_BUFF_MAX

ggi = GoGetDB()


class CharacterSheetBase:
    ABILITY_TO_SKILL_MAPPING = ABILITY_TO_SKILL_MAPPING
    CLASS_HIT_DIE_MAPPING = CLASS_HIT_DIE_MAPPING

    BUFF_TARGET_TABLE_COLUMNS = {
        "character": [
            "armour_class",
            "initiative",
            "speed",
            "proficiency",
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
    def __init__(self, character_id: Optional[str] = None, guest_character: bool = False):
        self.character_id = character_id
        self.guest_character = guest_character
        if self.guest_character:
            self.store = guest_session.GuestSessionStore(character_id=self.character_id)
            self.character_id = guest_session.get_guest_character_id() or self.store.character_id
        else:
            self.store = ggi

    def _rows(self, table_name: str, params: Optional[dict] = None) -> list:
        rows = self.store.go_get_all(table_name, params)
        if isinstance(rows, list):
            return rows
        return []

    def _count(self, table_name: str, params: Optional[dict] = None) -> int:
        count_value = self.store.go_get_all(table_name, params, count=True)
        if isinstance(count_value, int):
            return count_value
        return 0

    def fetch_character_row(self):
        """Fetch the bare character row, or {} if there's no character_id."""
        return self.store.go_get_one('character', {'id': self.character_id}) if self.character_id else {}

    def fetch_class_levels(self):
        """Fetch this character's class_to_character rows (raw, unsorted, no class names attached)."""
        return self._rows('class_to_character', {'character_id': self.character_id})

    def fetch_all_classes(self):
        """Fetch every class in the reference 'class' table."""
        return self._rows('class')

    def fetch_buff_target_options_data(self, custom_stats=None, feats_and_traits=None, inventory=None):
        """Thin wrapper around _get_buff_target_options that fetches any missing piece itself."""
        if custom_stats is None:
            custom_stats = self.fetch_custom_stats_data()
        if feats_and_traits is None:
            feats_and_traits = self.fetch_feats_data()
        if inventory is None:
            inventory = self.fetch_inventory_data()
        return self._get_buff_target_options(custom_stats, feats_and_traits, inventory)

    def create_form(self):
        """
        Returns structured data for the character sheet instead of HTML strings.
        This data will be passed to Jinja2 templates for rendering.
        """
        # class_levels is shared between the character-level calc and the classes list
        # so it's only ever queried once per call — do not let a future edit deep-copy
        # this away "for safety"; fetch_classes_data already defends its own mutation.
        class_levels = self.fetch_class_levels() if self.character_id else []

        character = self.fetch_character_info_data(class_levels=class_levels)
        abilities_data = self.fetch_abilities_data()
        classes, class_options = self.fetch_classes_data(class_levels=class_levels)
        feats_and_traits = self.fetch_feats_data()
        inventory = self.fetch_inventory_data()
        custom_stats = self.fetch_custom_stats_data()
        buff_target_options = self.fetch_buff_target_options_data(custom_stats, feats_and_traits, inventory)
        custom_buffs = self.fetch_custom_buffs_data()

        return {
            'character': character,
            'classes': classes,
            'class_options': class_options,
            'abilities': abilities_data,
            'feats_and_traits': feats_and_traits,
            'feats_and_traits_at_capacity': len(feats_and_traits) >= FEAT_TRAIT_MAX,
            'inventory': inventory,
            'inventory_at_capacity': len(inventory) >= INVENTORY_MAX,
            'custom_stats': custom_stats,
            'custom_stats_at_capacity': len(custom_stats) >= CUSTOM_STAT_MAX,
            'custom_buffs': custom_buffs,
            'custom_buffs_at_capacity': len(custom_buffs) >= CUSTOM_BUFF_MAX,
            'buff_target_options': buff_target_options,
        }

    def _get_buff_target_options(self, custom_stats, feats_and_traits=None, inventory=None):
        options = {
            table_name: columns[:]
            for table_name, columns in self.BUFF_TARGET_TABLE_COLUMNS.items()
        }

        custom_stat_ids = []
        seen_cs_ids = set()
        for custom_stat in custom_stats or []:
            cs_id = custom_stat.get('id')
            stat_name = str(custom_stat.get('name') or '').strip()
            if not cs_id or not stat_name:
                continue
            if cs_id not in seen_cs_ids:
                seen_cs_ids.add(cs_id)
                custom_stat_ids.append({'id': cs_id, 'name': stat_name})

        custom_stat_ids.sort(key=lambda x: x['name'])
        options['custom_stat'] = custom_stat_ids

        feat_ids = []
        seen_feat_ids = set()
        for feat in feats_and_traits or []:
            feat_id = feat.get('id')
            feat_name = str(feat.get('name') or '').strip()
            if feat_id and feat_name and feat_id not in seen_feat_ids:
                seen_feat_ids.add(feat_id)
                feat_ids.append({'id': feat_id, 'name': feat_name})

        feat_ids.sort(key=lambda x: x['name'])
        options['feat_and_trait'] = feat_ids

        inventory_ids = []
        seen_inv_ids = set()
        for item in inventory or []:
            item_id = item.get('id')
            item_name = str(item.get('name') or '').strip()
            if item_id and item_name and item_id not in seen_inv_ids:
                seen_inv_ids.add(item_id)
                inventory_ids.append({'id': item_id, 'name': item_name})

        inventory_ids.sort(key=lambda x: x['name'])
        options['inventory'] = inventory_ids
        return options

    _ID_BASED_TABLES = {'custom_stat', 'feat_and_trait', 'inventory'}

    def _get_valid_stat_values(self, buff_target_options, table_name):
        """Get set of valid stat values for a table. For ID-based tables, returns IDs."""
        options = buff_target_options.get(table_name, [])
        if table_name in self._ID_BASED_TABLES:
            return {opt['id'] for opt in options if isinstance(opt, dict) and opt.get('id')}
        return set(options)
