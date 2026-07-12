from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet, CUSTOM_STAT_MAX
from demiplane.services.custom_buff import BuffProcessor
from demiplane.services import guest_character as guest
from demiplane.routes.helpers import guest_or_login_required, build_guest_character_sheet_data


def register_classes_fragment_routes(app, db, limiter):
    @app.route('/characters/<character_id>/classes/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def classes_fragment(character_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.save_class_to_character_values(character_id, request.form)
            data = sheet.create_form()
            return render_template(
                'components/classes/classes_fragment_response.html',
                character_id=character_id,
                classes=data['classes'],
                class_options=data['class_options'],
                character=data['character'],
                custom_stats=data['custom_stats'],
                custom_stats_at_capacity=data['custom_stats_at_capacity'],
                is_guest=True,
            )
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        sheet.save_class_to_character_values(character_id, request.form)

        class_levels = sheet.fetch_class_levels()
        classes, class_options = sheet.fetch_classes_data(class_levels=class_levels)
        character = sheet.fetch_character_info_data(class_levels=class_levels)
        custom_stats = sheet.fetch_custom_stats_data()
        custom_buffs = sheet.fetch_custom_buffs_data()
        BuffProcessor(character_id).transform_out({'custom_stats': custom_stats, 'custom_buffs': custom_buffs})

        return render_template(
            'components/classes/classes_fragment_response.html',
            character_id=character_id,
            classes=classes,
            class_options=class_options,
            character=character,
            custom_stats=custom_stats,
            custom_stats_at_capacity=len(custom_stats) >= CUSTOM_STAT_MAX,
            is_guest=False,
        )

    @app.route('/characters/<character_id>/class/<class_id>/remove', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def remove_class(character_id: str, class_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.remove_class(character_id, class_id)
            data = sheet.create_form()
            return render_template(
                'components/classes/classes_fragment_response.html',
                character_id=character_id,
                classes=data['classes'],
                class_options=data['class_options'],
                character=data['character'],
                custom_stats=data['custom_stats'],
                custom_stats_at_capacity=data['custom_stats_at_capacity'],
                is_guest=True,
            )
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        if not character_id or not class_id or not db.go_get_one('class_to_character', {'id': class_id, 'character_id': character_id}):
            return redirect(url_for('character_sheet'))

        sheet = CharacterSheet(character_id=character_id)
        sheet.remove_class(character_id, class_id)

        class_levels = sheet.fetch_class_levels()
        classes, class_options = sheet.fetch_classes_data(class_levels=class_levels)
        character = sheet.fetch_character_info_data(class_levels=class_levels)
        custom_stats = sheet.fetch_custom_stats_data()
        custom_buffs = sheet.fetch_custom_buffs_data()
        BuffProcessor(character_id).transform_out({'custom_stats': custom_stats, 'custom_buffs': custom_buffs})

        return render_template(
            'components/classes/classes_fragment_response.html',
            character_id=character_id,
            classes=classes,
            class_options=class_options,
            character=character,
            custom_stats=custom_stats,
            custom_stats_at_capacity=len(custom_stats) >= CUSTOM_STAT_MAX,
            is_guest=False,
        )
