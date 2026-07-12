from .constants import (
    INVENTORY_MAX,
    CUSTOM_STAT_MAX,
    CUSTOM_BUFF_MAX,
    FEAT_TRAIT_MAX,
    TRACKER_MAX,
    TRACKER_ENTRY_MAX,
)
from .base import CharacterSheetBase
from .character_info import CharacterInfoMixin
from .abilities import AbilitiesMixin
from .classes import ClassesMixin
from .feats import FeatsMixin
from .inventory import InventoryMixin
from .custom_stats import CustomStatsMixin
from .custom_buffs import CustomBuffsMixin


class CharacterSheet(
    CharacterInfoMixin, AbilitiesMixin, ClassesMixin, FeatsMixin,
    InventoryMixin, CustomStatsMixin, CustomBuffsMixin, CharacterSheetBase,
):
    pass


__all__ = [
    "CharacterSheet",
    "INVENTORY_MAX",
    "CUSTOM_STAT_MAX",
    "CUSTOM_BUFF_MAX",
    "FEAT_TRAIT_MAX",
    "TRACKER_MAX",
    "TRACKER_ENTRY_MAX",
]
