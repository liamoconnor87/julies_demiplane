from .trackers import get_trackers_for_character, register_tracker_fragment_routes
from .character_info import register_character_info_fragment_routes
from .classes import register_classes_fragment_routes
from .abilities import register_abilities_fragment_routes
from .feats import register_feats_fragment_routes
from .inventory import register_inventory_fragment_routes
from .custom_stats import register_custom_stats_fragment_routes
from .custom_buffs import register_custom_buffs_fragment_routes


def register_fragment_routes(app, db, limiter):
    register_character_info_fragment_routes(app, db, limiter)
    register_classes_fragment_routes(app, db, limiter)
    register_abilities_fragment_routes(app, db, limiter)
    register_feats_fragment_routes(app, db, limiter)
    register_inventory_fragment_routes(app, db, limiter)
    register_custom_stats_fragment_routes(app, db, limiter)
    register_custom_buffs_fragment_routes(app, db, limiter)
    register_tracker_fragment_routes(app, db, limiter)
