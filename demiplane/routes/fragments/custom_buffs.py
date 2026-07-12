from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet
from demiplane.functions.validators import is_valid_uuid
from demiplane.routes.helpers import build_character_sheet_data

from ._shared import _rows_or_empty


def register_custom_buffs_fragment_routes(app, db, limiter):
    @app.route('/characters/<character_id>/custom-buffs/fragment', methods=['POST'])
    @login_required
    def custom_buffs_fragment(character_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        sheet.save_custom_buff_values(character_id, request.form)

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/buffs/buff_change_response.html',
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            character_id=character_id,
            character=data['character'],
            abilities=data['abilities'],
            custom_stats=data['custom_stats'],
            custom_stats_at_capacity=data['custom_stats_at_capacity'],
            classes=data['classes'],
        )

    @app.route('/characters/<character_id>/custom-buff/<custom_buff_id>/update', methods=['POST'])
    @login_required
    def update_custom_buff_item(character_id: str, custom_buff_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        if not is_valid_uuid(custom_buff_id):
            return redirect(url_for('character_sheet'))
        sheet = CharacterSheet(character_id=character_id)
        sheet.update_custom_buff_values(character_id, custom_buff_id, request.form)

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/buffs/buff_change_response.html',
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            character_id=character_id,
            character=data['character'],
            abilities=data['abilities'],
            custom_stats=data['custom_stats'],
            custom_stats_at_capacity=data['custom_stats_at_capacity'],
            classes=data['classes'],
        )

    @app.route('/characters/<character_id>/custom-buff/<custom_buff_id>/remove', methods=['POST'])
    @login_required
    def remove_custom_buff_item(character_id: str, custom_buff_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        if not character_id or not custom_buff_id or not db.go_get_one('custom_buff', {'id': custom_buff_id, 'character_id': character_id}):
            return redirect(url_for('character_sheet'))

        custom_buff_tables = _rows_or_empty(db.go_get_all('custom_buff_to_stat_table', {'custom_buff_id': custom_buff_id, 'character_id': character_id}))
        for custom_buff_table in custom_buff_tables:
            stat_table_id = custom_buff_table.get('stat_table_id')
            table_link_id = custom_buff_table.get('id')
            if stat_table_id:
                table_stats = _rows_or_empty(db.go_get_all('stat_table_to_stat', {'stat_table_id': stat_table_id, 'character_id': character_id}))
                for table_stat in table_stats:
                    if table_stat.get('id'):
                        db.go_delete_it('stat_table_to_stat', {'id': table_stat['id']})
            if table_link_id:
                db.go_delete_it('custom_buff_to_stat_table', {'id': table_link_id})

        db.go_delete_it('custom_buff', {'id': custom_buff_id, 'character_id': character_id})

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/buffs/buff_change_response.html',
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            character_id=character_id,
            character=data['character'],
            abilities=data['abilities'],
            custom_stats=data['custom_stats'],
            custom_stats_at_capacity=data['custom_stats_at_capacity'],
            classes=data['classes'],
        )
