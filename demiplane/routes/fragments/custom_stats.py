from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet
from demiplane.services.custom_buff import BuffProcessor
from demiplane.services import guest_character as guest
from demiplane.routes.helpers import guest_or_login_required, build_character_sheet_data, build_guest_character_sheet_data


def register_custom_stats_fragment_routes(app, db, limiter):
    @app.route('/characters/<character_id>/custom-stats/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def custom_stats_fragment(character_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.save_custom_stat_values(character_id, request.form)
            data = sheet.create_form()
            return render_template(
                'components/stats/custom_stats_change_response.html',
                custom_stats=data['custom_stats'],
                custom_stats_at_capacity=data['custom_stats_at_capacity'],
                custom_buffs=data['custom_buffs'],
                custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
                buff_target_options=data['buff_target_options'],
                class_options=data['class_options'],
                classes=data['classes'],
                character_id=character_id,
                is_guest=True,
            )
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        sheet.save_custom_stat_values(character_id, request.form)

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/stats/custom_stats_change_response.html',
            custom_stats=data['custom_stats'],
            custom_stats_at_capacity=data['custom_stats_at_capacity'],
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            class_options=data['class_options'],
            classes=data['classes'],
            character_id=character_id,
            is_guest=False,
        )

    @app.route('/characters/<character_id>/custom-stat/<custom_stat_id>/update', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def update_custom_stat_item(character_id: str, custom_stat_id: str):
        value_field = f'custom_stat-value-{custom_stat_id}'
        name_field = f'custom_stat-name-{custom_stat_id}'

        if guest.is_guest() and not current_user.is_authenticated:
            sheet, _ = build_guest_character_sheet_data(character_id)
            updated_stat = sheet.update_single_custom_stat(
                character_id,
                custom_stat_id,
                request.form.get(name_field, ''),
                request.form.get(value_field),
            )
            if not updated_stat:
                abort(400)
            return render_template('components/stats/custom_stat_row.html', stat=updated_stat, character_id=character_id)

        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        transformed_form = BuffProcessor(character_id).transform_in(request.form)
        sheet = CharacterSheet(character_id=character_id)
        updated_stat = sheet.update_single_custom_stat(
            character_id,
            custom_stat_id,
            transformed_form.get(name_field, request.form.get(name_field, '')),
            transformed_form.get(value_field, request.form.get(value_field)),
        )
        if not updated_stat:
            abort(400)

        _, data = build_character_sheet_data(character_id)
        rendered_stat = next((s for s in data['custom_stats'] if s.get('id') == custom_stat_id), None)
        if not rendered_stat:
            abort(404)

        return render_template('components/stats/custom_stat_row.html', stat=rendered_stat, character_id=character_id)

    @app.route('/characters/<character_id>/custom-stat/<custom_stat_id>/remove', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def remove_custom_stat_item(character_id: str, custom_stat_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.remove_custom_stat(character_id, custom_stat_id)
            data = sheet.create_form()
            return render_template(
                'components/stats/custom_stats_change_response.html',
                character_id=character_id,
                custom_stats=data['custom_stats'],
                custom_stats_at_capacity=data['custom_stats_at_capacity'],
                custom_buffs=data['custom_buffs'],
                custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
                buff_target_options=data['buff_target_options'],
                class_options=data['class_options'],
                classes=data['classes'],
                is_guest=True,
            )
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        if not character_id or not custom_stat_id or not db.go_get_one('custom_stat', {'id': custom_stat_id, 'character_id': character_id}):
            return redirect(url_for('character_sheet'))

        sheet = CharacterSheet(character_id=character_id)
        sheet.remove_custom_stat(character_id, custom_stat_id)

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/stats/custom_stats_change_response.html',
            character_id=character_id,
            custom_stats=data['custom_stats'],
            custom_stats_at_capacity=data['custom_stats_at_capacity'],
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            class_options=data['class_options'],
            classes=data['classes'],
            is_guest=False,
        )
