from flask import abort, render_template, request
from flask_login import current_user

from auth.models import User, UserTheme
from character_sheet.character_sheet import TRACKER_MAX, TRACKER_ENTRY_MAX
from character_sheet import guest_character as guest
from routes.fragments import get_trackers_for_character
from routes.helpers import build_character_sheet_data, build_guest_character_sheet_data


def register_main_routes(app, db):
    @app.route('/', methods=['GET'])
    def character_sheet():

        # ── Guest branch (auto-create on first visit) ──────────────────────────
        if not current_user.is_authenticated:
            guest.create_blank()  # no-op if guest session already exists
            character_id = guest.get_guest_character_id()
            if not character_id:
                guest.create_blank()
                character_id = guest.get_guest_character_id()
            sheet, data = build_guest_character_sheet_data(character_id)
            character_id = sheet.character_id
            is_new_character = not data['character'].get('name')
            guest_name = str(data['character'].get('name') or '').strip()
            landing_requested = (request.args.get('landing') or '').strip() == '1'

            # Landing panel is visible for first-time guests, or when a named guest
            # explicitly returns to landing mode via the navbar title.
            show_guest_landing_panel = is_new_character or (landing_requested and bool(guest_name))
            show_guest_name_entry = is_new_character
            guest_show_sheet = not (landing_requested and bool(guest_name))

            return render_template(
                'index.html',
                characters=[],
                active_character_id=character_id,
                at_character_limit=True,
                is_new_character=is_new_character,
                is_guest=True,
                character_id=character_id,
                character=data['character'],
                classes=data['classes'],
                class_options=data['class_options'],
                abilities=data['abilities'],
                feats_and_traits=data['feats_and_traits'],
                feats_and_traits_at_capacity=data['feats_and_traits_at_capacity'],
                inventory=data['inventory'],
                inventory_at_capacity=data['inventory_at_capacity'],
                custom_stats=data['custom_stats'],
                custom_stats_at_capacity=data['custom_stats_at_capacity'],
                custom_buffs=data['custom_buffs'],
                custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
                buff_target_options=data['buff_target_options'],
                trackers=[],
                show_guest_landing_panel=show_guest_landing_panel,
                show_guest_name_entry=show_guest_name_entry,
                guest_show_sheet=guest_show_sheet,
                guest_character_name=guest_name,
            )

        characters = User.get_characters(db, current_user.id)
        at_character_limit = User.at_character_limit(db, current_user.id)
        user_theme = UserTheme.get_by_user_id(db, current_user.id)
        character_id = request.args.get('character_id')

        # If no character_id specified, default to first owned character
        if not character_id and characters:
            character_id = characters[0]['id']

        # Verify ownership
        if character_id and not User.owns_character(db, current_user.id, character_id):
            abort(403)

        active_character_id = character_id

        # ── Unsaved new character (no DB row yet) ──────────────────────────────
        if request.args.get('new') == 'true':
            blank_character = {
                'id': None, 'name': None, 'level': 0,
                'race': None, 'background': None, 'alignment': None,
                'armour_class': None, 'initiative': None, 'speed': None,
                'proficiency': None, 'passive_wisdom': None, 'xp': None,
                'health_points': None, 'hit_dice': None,
                'temporary_hit_points': None,
            }
            return render_template(
                'index.html',
                characters=characters,
                active_character_id=None,
                at_character_limit=at_character_limit,
                is_new_character=True,
                is_unsaved=True,
                is_guest=False,
                character_id=None,
                character=blank_character,
                classes=[],
                class_options=[],
                abilities=[],
                feats_and_traits=[],
                feats_and_traits_at_capacity=False,
                inventory=[],
                inventory_at_capacity=False,
                custom_stats=[],
                custom_stats_at_capacity=False,
                custom_buffs=[],
                custom_buffs_at_capacity=False,
                buff_target_options={},
                trackers=[],
                user_theme=user_theme,
            )

        if not character_id:
            return render_template(
                'index.html',
                characters=characters,
                active_character_id=active_character_id,
                at_character_limit=at_character_limit,
                is_guest=False,
                character=None,
                trackers=[],
                user_theme=user_theme,
            )

        _, character_sheet_data = build_character_sheet_data(character_id)
        trackers = get_trackers_for_character(db, character_id)

        # Detect if this is a brand-new character (no name set yet)
        is_new_character = not character_sheet_data['character'].get('name')

        return render_template(
            'index.html',
            characters=characters,
            active_character_id=active_character_id,
            at_character_limit=at_character_limit,
            is_new_character=is_new_character,
            is_guest=False,
            character_id=character_id,
            character=character_sheet_data['character'],
            classes=character_sheet_data['classes'],
            class_options=character_sheet_data['class_options'],
            abilities=character_sheet_data['abilities'],
            feats_and_traits=character_sheet_data['feats_and_traits'],
            feats_and_traits_at_capacity=character_sheet_data['feats_and_traits_at_capacity'],
            inventory=character_sheet_data['inventory'],
            inventory_at_capacity=character_sheet_data['inventory_at_capacity'],
            custom_stats=character_sheet_data['custom_stats'],
            custom_stats_at_capacity=character_sheet_data['custom_stats_at_capacity'],
            custom_buffs=character_sheet_data['custom_buffs'],
            custom_buffs_at_capacity=character_sheet_data['custom_buffs_at_capacity'],
            buff_target_options=character_sheet_data['buff_target_options'],
            trackers=trackers,
            trackers_at_capacity=len(trackers) >= TRACKER_MAX,
            tracker_max=TRACKER_MAX,
            tracker_entry_max=TRACKER_ENTRY_MAX,
            user_theme=user_theme,
        )
