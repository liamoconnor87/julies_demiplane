from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.exceptions import HTTPException

from auth.models import User
from character_sheet.character_sheet import CharacterSheet, TRACKER_MAX, TRACKER_ENTRY_MAX
from character_sheet.custom_buff import BuffProcessor
from character_sheet import guest_character as guest
from functions.functions import uuid as generate_uuid
from functions.validators import is_valid_uuid


def _rows_or_empty(result):
    if isinstance(result, list):
        return result
    return []


def _count_or_zero(result):
    if isinstance(result, int):
        return result
    if isinstance(result, list):
        return len(result)
    return 0


def get_trackers_for_character(db, character_id: str):
    """Return custom DB trackers (with entries) for a character."""
    trackers = _rows_or_empty(db.go_get_all('tracker', {'character_id': character_id}))
    result = []
    for tracker in trackers:
        entries = _rows_or_empty(db.go_get_all('tracker_entry', {'tracker_id': tracker['id']}))
        result.append({
            'id': tracker['id'],
            'name': tracker['name'],
            'entries': entries,
            'entries_at_capacity': len(entries) >= TRACKER_ENTRY_MAX,
        })
    return result


def register_fragment_routes(
    app,
    db,
    limiter,
    guest_or_login_required,
    build_character_sheet_data,
    build_guest_character_sheet_data,
):
    @app.route('/characters/<character_id>/character-info/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def character_info_fragment(character_id: str):
        feedback_message = ''
        feedback_kind = 'success'

        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            try:
                sheet.save_character_values(request.form)
                data = sheet.create_form()
            except HTTPException:
                raise
            except Exception:
                app.logger.exception('Character info save failed for guest character_id=%s', character_id)
                feedback_message = 'Something went wrong. Please try again.'
                feedback_kind = 'error'
                data = sheet.create_form()

            is_new_character = not data['character'].get('name')
            guest_name = str(data['character'].get('name') or '').strip()
            return render_template(
                'components/character_info_change_response.html',
                character_id=character_id,
                character=data['character'],
                abilities=data['abilities'],
                is_guest=True,
                show_guest_landing_panel=is_new_character,
                show_guest_name_entry=is_new_character,
                guest_character_name=guest_name,
                character_info_feedback_message=feedback_message,
                character_info_feedback_kind=feedback_kind,
            )

        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        sheet = CharacterSheet(character_id=character_id)
        request_form = BuffProcessor(character_id).transform_in(request.form)
        try:
            sheet.save_character_values(request_form)
        except HTTPException:
            raise
        except Exception:
            app.logger.exception('Character info save failed for user_id=%s character_id=%s', current_user.id, character_id)
            feedback_message = 'Something went wrong. Please try again.'
            feedback_kind = 'error'

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/character_info_change_response.html',
            character_id=character_id,
            character=data['character'],
            abilities=data['abilities'],
            is_guest=False,
            character_info_feedback_message=feedback_message,
            character_info_feedback_kind=feedback_kind,
        )

    @app.route('/characters/<character_id>/combat/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def combat_fragment(character_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.save_combat_values(character_id, request.form)
            data = sheet.create_form()
            return render_template(
                'components/guest_combat_stats.html',
                character_id=character_id,
                character=data['character'],
                is_guest=True,
            )

        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        sheet.save_combat_values(character_id, request.form)

        _, data = build_character_sheet_data(character_id)
        return render_template('components/combat_stats.html', character_id=character_id, character=data['character'])

    @app.route('/characters/<character_id>/classes/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def classes_fragment(character_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.save_class_to_character_values(character_id, request.form)
            data = sheet.create_form()
            return render_template(
                'components/classes_fragment_response.html',
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

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/classes_fragment_response.html',
            character_id=character_id,
            classes=data['classes'],
            class_options=data['class_options'],
            character=data['character'],
            custom_stats=data['custom_stats'],
            custom_stats_at_capacity=data['custom_stats_at_capacity'],
            is_guest=False,
        )

    @app.route('/characters/<character_id>/feats-traits/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def feats_traits_fragment(character_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.save_feat_and_trait_values(character_id, request.form)
            data = sheet.create_form()
            return render_template(
                'components/feats_traits_section.html',
                character_id=character_id,
                feats_and_traits=data['feats_and_traits'],
                feats_and_traits_at_capacity=data['feats_and_traits_at_capacity'],
                is_guest=True,
            )
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        sheet.save_feat_and_trait_values(character_id, request.form)

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/feats_traits_change_response.html',
            character_id=character_id,
            feats_and_traits=data['feats_and_traits'],
            feats_and_traits_at_capacity=data['feats_and_traits_at_capacity'],
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            is_guest=False,
        )

    @app.route('/characters/<character_id>/abilities-skills/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def abilities_skills_fragment(character_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.save_ability_values(character_id, request.form)
            data = sheet.create_form()
            return render_template(
                'components/abilities_section.html',
                abilities=data['abilities'],
                character_id=character_id,
                is_guest=True,
            )
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        transformed_form = BuffProcessor(character_id).transform_in(request.form)
        sheet.save_ability_values(character_id, transformed_form)

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/abilities_section.html',
            abilities=data['abilities'],
            character_id=character_id,
            is_guest=False,
        )

    @app.route('/characters/<character_id>/abilities-skills/<ability_name>/update', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def update_ability_row(character_id: str, ability_name: str):
        normalized_ability_name = str(ability_name or '').strip().lower()
        if normalized_ability_name not in CharacterSheet.ABILITY_TO_SKILL_MAPPING:
            abort(404)

        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.save_ability_values(character_id, request.form)
            data = sheet.create_form()
            ability_data = next((row for row in data['abilities'] if row.get('ability_name') == normalized_ability_name), None)
            if not ability_data:
                abort(404)
            return render_template(
                'components/ability_row.html',
                ability_name=ability_data['ability_name'],
                ability=ability_data['ability'],
                skills=ability_data['skills'],
                skill_list=ability_data['skill_list'],
                character_id=character_id,
                is_guest=True,
            )

        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        sheet = CharacterSheet(character_id=character_id)
        transformed_form = BuffProcessor(character_id).transform_in(request.form)
        sheet.save_ability_values(character_id, transformed_form)

        _, data = build_character_sheet_data(character_id)
        ability_data = next((row for row in data['abilities'] if row.get('ability_name') == normalized_ability_name), None)
        if not ability_data:
            abort(404)

        return render_template(
            'components/ability_row.html',
            ability_name=ability_data['ability_name'],
            ability=ability_data['ability'],
            skills=ability_data['skills'],
            skill_list=ability_data['skill_list'],
            character_id=character_id,
            is_guest=False,
        )

    @app.route('/characters/<character_id>/inventory/fragment', methods=['POST'])
    @login_required
    def inventory_fragment(character_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        sheet.save_inventory_values(character_id, request.form)

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/inventory_change_response.html',
            inventory=data['inventory'],
            inventory_at_capacity=data['inventory_at_capacity'],
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            character_id=character_id,
        )

    @app.route('/characters/<character_id>/custom-stats/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def custom_stats_fragment(character_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.save_custom_stat_values(character_id, request.form)
            data = sheet.create_form()
            return render_template(
                'components/custom_stats_change_response.html',
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
            'components/custom_stats_change_response.html',
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
            return render_template('components/custom_stat_row.html', stat=updated_stat, character_id=character_id)

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

        return render_template('components/custom_stat_row.html', stat=rendered_stat, character_id=character_id)

    @app.route('/characters/<character_id>/custom-buffs/fragment', methods=['POST'])
    @login_required
    def custom_buffs_fragment(character_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        sheet.save_custom_buff_values(character_id, request.form)

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/buff_change_response.html',
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
            'components/buff_change_response.html',
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

    @app.route('/characters/<character_id>/inventory/<inventory_id>/remove', methods=['POST'])
    @login_required
    def remove_inventory_item(character_id: str, inventory_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        if not character_id or not inventory_id or not db.go_get_one('inventory', {'id': inventory_id, 'character_id': character_id}):
            return redirect(url_for('character_sheet'))

        db.go_delete_it('inventory', {'id': inventory_id, 'character_id': character_id})

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/inventory_change_response.html',
            inventory=data['inventory'],
            inventory_at_capacity=data['inventory_at_capacity'],
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            character_id=character_id,
        )

    @app.route('/characters/<character_id>/inventory/<inventory_id>/update', methods=['POST'])
    @login_required
    def update_inventory_item(character_id: str, inventory_id: str):
        name = request.form.get(f'inventory-name-{inventory_id}', '')
        description = request.form.get(f'inventory-description-{inventory_id}', '')
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        item = sheet.update_single_inventory_item(character_id, inventory_id, name, description)
        if not item:
            abort(400)

        _, data = build_character_sheet_data(character_id)
        rendered_item = next((entry for entry in data['inventory'] if entry.get('id') == inventory_id), item)
        return render_template(
            'components/inventory_row_change_response.html',
            item=rendered_item,
            character_id=character_id,
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
        )

    @app.route('/characters/<character_id>/inventory/<inventory_id>/step', methods=['POST'])
    @login_required
    def step_inventory_item(character_id: str, inventory_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        try:
            step = int(request.form.get('inventory-step', '0'))
        except (TypeError, ValueError):
            step = 0

        # Clamp step size defensively.
        step = max(-100, min(100, step))
        if step == 0:
            abort(400)

        sheet = CharacterSheet(character_id=character_id)
        item = sheet.step_single_inventory_item(character_id, inventory_id, step)

        _, data = build_character_sheet_data(character_id)
        rendered_item = None
        if item is not None:
            rendered_item = next((entry for entry in data['inventory'] if entry.get('id') == inventory_id), item)

        return render_template(
            'components/inventory_row_change_response.html',
            item=rendered_item,
            character_id=character_id,
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
        )

    @app.route('/characters/<character_id>/inventory/add', methods=['POST'])
    @login_required
    def add_inventory_item(character_id: str):
        name = request.form.get('inventory-name', '')
        description = request.form.get('inventory-description', '')
        quantity = request.form.get('inventory-quantity', '1')
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        item = sheet.add_single_inventory_item(character_id, name, description, quantity)
        if not item:
            abort(400)

        _, data = build_character_sheet_data(character_id)
        rendered_item = next((entry for entry in data['inventory'] if entry.get('id') == item.get('id')), item)
        return render_template(
            'components/inventory_row_change_response.html',
            item=rendered_item,
            character_id=character_id,
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
        )

    @app.route('/characters/<character_id>/feat-and-trait/<feat_and_trait_id>/remove', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def remove_feat_and_trait_item(character_id: str, feat_and_trait_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.remove_feat_and_trait(character_id, feat_and_trait_id)
            data = sheet.create_form()
            return render_template(
                'components/feats_traits_section.html',
                character_id=character_id,
                feats_and_traits=data['feats_and_traits'],
                feats_and_traits_at_capacity=data['feats_and_traits_at_capacity'],
                is_guest=True,
            )
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        if not character_id or not feat_and_trait_id or not db.go_get_one('feat_and_trait', {'id': feat_and_trait_id, 'character_id': character_id}):
            return redirect(url_for('character_sheet'))

        sheet = CharacterSheet(character_id=character_id)
        sheet.remove_feat_and_trait(character_id, feat_and_trait_id)

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/feats_traits_change_response.html',
            character_id=character_id,
            feats_and_traits=data['feats_and_traits'],
            feats_and_traits_at_capacity=data['feats_and_traits_at_capacity'],
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            is_guest=False,
        )

    @app.route('/characters/<character_id>/feat-and-trait/<feat_and_trait_id>/update', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def update_feat_and_trait_item(character_id: str, feat_and_trait_id: str):
        name = request.form.get(f'feat_and_trait-name-{feat_and_trait_id}', '')
        description = request.form.get(f'feat_and_trait-description-{feat_and_trait_id}', '')
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, _ = build_guest_character_sheet_data(character_id)
            feat = sheet.update_single_feat(character_id, feat_and_trait_id, name, description)
            if not feat:
                abort(400)
            return render_template('components/feat_row.html', feat=feat, character_id=character_id)
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        feat = sheet.update_single_feat(character_id, feat_and_trait_id, name, description)
        if not feat:
            abort(400)

        _, data = build_character_sheet_data(character_id)
        rendered_feat = next((entry for entry in data['feats_and_traits'] if entry.get('id') == feat_and_trait_id), feat)
        return render_template(
            'components/feat_row_change_response.html',
            feat=rendered_feat,
            character_id=character_id,
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
        )

    @app.route('/characters/<character_id>/feat-and-trait/add', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def add_feat_and_trait_item(character_id: str):
        name = request.form.get('feat_and_trait-name', '')
        description = request.form.get('feat_and_trait-description', '')
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, _ = build_guest_character_sheet_data(character_id)
            feat = sheet.add_single_feat(character_id, name, description)
            if not feat:
                abort(400)
            return render_template('components/feat_row.html', feat=feat, character_id=character_id)
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        feat = sheet.add_single_feat(character_id, name, description)
        if not feat:
            abort(400)

        _, data = build_character_sheet_data(character_id)
        rendered_feat = next((entry for entry in data['feats_and_traits'] if entry.get('id') == feat.get('id')), feat)
        return render_template(
            'components/feat_row_change_response.html',
            feat=rendered_feat,
            character_id=character_id,
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
        )

    @app.route('/characters/<character_id>/custom-stat/<custom_stat_id>/remove', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def remove_custom_stat_item(character_id: str, custom_stat_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.remove_custom_stat(character_id, custom_stat_id)
            data = sheet.create_form()
            return render_template(
                'components/custom_stats_change_response.html',
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
            'components/custom_stats_change_response.html',
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
            'components/buff_change_response.html',
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

    @app.route('/characters/<character_id>/class/<class_id>/remove', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def remove_class(character_id: str, class_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.remove_class(character_id, class_id)
            data = sheet.create_form()
            return render_template(
                'components/classes_fragment_response.html',
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

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/classes_fragment_response.html',
            character_id=character_id,
            classes=data['classes'],
            class_options=data['class_options'],
            character=data['character'],
            custom_stats=data['custom_stats'],
            custom_stats_at_capacity=data['custom_stats_at_capacity'],
            is_guest=False,
        )

    def _get_single_tracker(character_id: str, tracker_id: str):
        tracker = db.go_get_one('tracker', {'id': tracker_id, 'character_id': character_id})
        if not tracker:
            return None
        entries = _rows_or_empty(db.go_get_all('tracker_entry', {'tracker_id': tracker_id}))
        return {
            'id': tracker['id'],
            'name': tracker['name'],
            'entries': entries,
            'entries_at_capacity': len(entries) >= TRACKER_ENTRY_MAX,
        }

    def _render_tracker_page(character_id: str):
        trackers = get_trackers_for_character(db, character_id)
        return render_template(
            'components/tracker_page.html',
            character_id=character_id,
            trackers=trackers,
            trackers_at_capacity=len(trackers) >= TRACKER_MAX,
            tracker_max=TRACKER_MAX,
            tracker_entry_max=TRACKER_ENTRY_MAX,
        )

    def _render_tracker_item(character_id: str, tracker_id: str):
        tracker = _get_single_tracker(character_id, tracker_id)
        if not tracker:
            abort(404)
        return render_template(
            'components/tracker_item.html',
            character_id=character_id,
            tracker=tracker,
            tracker_entry_max=TRACKER_ENTRY_MAX,
        )

    @app.route('/characters/<character_id>/tracker/<tracker_id>/update', methods=['POST'])
    @login_required
    @limiter.limit('120/minute')
    def update_tracker(character_id: str, tracker_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        tracker = db.go_get_one('tracker', {'id': tracker_id, 'character_id': character_id})
        if not tracker:
            abort(404)

        name = request.form.get('tracker-name', '').strip()[:60]
        if name:
            db.go_update('tracker', {'id': tracker_id, 'name': name})

        entries = _rows_or_empty(db.go_get_all('tracker_entry', {'tracker_id': tracker_id}))
        for entry in entries:
            entry_id = entry['id']
            entry_name = request.form.get(f'entry-name-{entry_id}', '').strip()[:40]
            entry_value_raw = request.form.get(f'entry-value-{entry_id}', '')
            updates = {}
            if entry_name:
                updates['name'] = entry_name
            if entry_value_raw:
                try:
                    updates['value'] = max(1, min(20, int(entry_value_raw)))
                except (ValueError, TypeError):
                    pass
            if updates:
                updates['id'] = entry_id
                db.go_update('tracker_entry', updates)

        return _render_tracker_item(character_id, tracker_id)

    @app.route('/characters/<character_id>/tracker/add', methods=['POST'])
    @login_required
    @limiter.limit('120/minute')
    def add_tracker(character_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        tracker_count = _count_or_zero(db.go_get_all('tracker', {'character_id': character_id}, count=True))
        if tracker_count >= TRACKER_MAX:
            return _render_tracker_page(character_id)

        name = request.form.get('add-tracker-name-input', '').strip()[:60]
        if name:
            db.go_add_new('tracker', {
                'id': generate_uuid(),
                'character_id': character_id,
                'name': name,
            })

        return _render_tracker_page(character_id)

    @app.route('/characters/<character_id>/tracker/<tracker_id>/remove', methods=['POST'])
    @login_required
    @limiter.limit('120/minute')
    def remove_tracker(character_id: str, tracker_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        tracker = db.go_get_one('tracker', {'id': tracker_id, 'character_id': character_id})
        if tracker:
            entries = _rows_or_empty(db.go_get_all('tracker_entry', {'tracker_id': tracker_id}))
            for entry in entries:
                db.go_delete_it('tracker_entry', {'id': entry['id']})
            db.go_delete_it('tracker', {'id': tracker_id, 'character_id': character_id})

        return _render_tracker_page(character_id)

    @app.route('/characters/<character_id>/tracker/<tracker_id>/entry/add', methods=['POST'])
    @login_required
    @limiter.limit('120/minute')
    def add_tracker_entry(character_id: str, tracker_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        if not db.go_get_one('tracker', {'id': tracker_id, 'character_id': character_id}):
            abort(403)

        entry_count = _count_or_zero(db.go_get_all('tracker_entry', {'tracker_id': tracker_id}, count=True))
        if entry_count >= TRACKER_ENTRY_MAX:
            return _render_tracker_page(character_id)

        name = request.form.get(f'entry-name-{tracker_id}', '').strip()[:40]
        try:
            value = max(1, min(20, int(request.form.get(f'entry-value-{tracker_id}', 3))))
        except (ValueError, TypeError):
            value = 3

        if name:
            db.go_add_new('tracker_entry', {
                'id': generate_uuid(),
                'tracker_id': tracker_id,
                'name': name,
                'value': value,
            })

        return _render_tracker_page(character_id)

    @app.route('/characters/<character_id>/tracker/<tracker_id>/entry/<entry_id>/remove', methods=['POST'])
    @login_required
    @limiter.limit('120/minute')
    def remove_tracker_entry(character_id: str, tracker_id: str, entry_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        entry = db.go_get_one('tracker_entry', {'id': entry_id, 'tracker_id': tracker_id})
        if entry:
            tracker = db.go_get_one('tracker', {'id': tracker_id, 'character_id': character_id})
            if tracker:
                db.go_delete_it('tracker_entry', {'id': entry_id, 'tracker_id': tracker_id})

        return _render_tracker_page(character_id)
