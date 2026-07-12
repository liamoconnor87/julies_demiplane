from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet, FEAT_TRAIT_MAX, CUSTOM_BUFF_MAX
from demiplane.services import guest_character as guest
from demiplane.routes.helpers import guest_or_login_required, build_guest_character_sheet_data


def register_feats_fragment_routes(app, db, limiter):
    @app.route('/characters/<character_id>/feats-traits/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def feats_traits_fragment(character_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.save_feat_and_trait_values(character_id, request.form)
            data = sheet.create_form()
            return render_template(
                'components/feats/feats_traits_section.html',
                character_id=character_id,
                feats_and_traits=data['feats_and_traits'],
                feats_and_traits_at_capacity=data['feats_and_traits_at_capacity'],
                is_guest=True,
            )
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        sheet.save_feat_and_trait_values(character_id, request.form)

        feats_and_traits = sheet.fetch_feats_data()
        custom_buffs = sheet.fetch_custom_buffs_data()
        buff_target_options = sheet.fetch_buff_target_options_data(feats_and_traits=feats_and_traits)
        return render_template(
            'components/feats/feats_traits_change_response.html',
            character_id=character_id,
            feats_and_traits=feats_and_traits,
            feats_and_traits_at_capacity=len(feats_and_traits) >= FEAT_TRAIT_MAX,
            custom_buffs=custom_buffs,
            custom_buffs_at_capacity=len(custom_buffs) >= CUSTOM_BUFF_MAX,
            buff_target_options=buff_target_options,
            is_guest=False,
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
                'components/feats/feats_traits_section.html',
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

        feats_and_traits = sheet.fetch_feats_data()
        custom_buffs = sheet.fetch_custom_buffs_data()
        buff_target_options = sheet.fetch_buff_target_options_data(feats_and_traits=feats_and_traits)
        return render_template(
            'components/feats/feats_traits_change_response.html',
            character_id=character_id,
            feats_and_traits=feats_and_traits,
            feats_and_traits_at_capacity=len(feats_and_traits) >= FEAT_TRAIT_MAX,
            custom_buffs=custom_buffs,
            custom_buffs_at_capacity=len(custom_buffs) >= CUSTOM_BUFF_MAX,
            buff_target_options=buff_target_options,
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
            return render_template('components/feats/feat_row.html', feat=feat, character_id=character_id)
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        feat = sheet.update_single_feat(character_id, feat_and_trait_id, name, description)
        if not feat:
            abort(400)

        custom_buffs = sheet.fetch_custom_buffs_data()
        buff_target_options = sheet.fetch_buff_target_options_data()
        return render_template(
            'components/feats/feat_row_change_response.html',
            feat=feat,
            character_id=character_id,
            custom_buffs=custom_buffs,
            custom_buffs_at_capacity=len(custom_buffs) >= CUSTOM_BUFF_MAX,
            buff_target_options=buff_target_options,
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
            return render_template('components/feats/feat_row_guest_add_response.html', feat=feat, character_id=character_id)
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        feat = sheet.add_single_feat(character_id, name, description)
        if not feat:
            abort(400)

        custom_buffs = sheet.fetch_custom_buffs_data()
        buff_target_options = sheet.fetch_buff_target_options_data()
        return render_template(
            'components/feats/feat_row_change_response.html',
            feat=feat,
            character_id=character_id,
            custom_buffs=custom_buffs,
            custom_buffs_at_capacity=len(custom_buffs) >= CUSTOM_BUFF_MAX,
            buff_target_options=buff_target_options,
        )
