from flask import abort, render_template, request
from flask_login import current_user

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet
from demiplane.services.custom_buff import BuffProcessor
from demiplane.services import guest_character as guest
from demiplane.routes.helpers import guest_or_login_required, build_guest_character_sheet_data


def register_abilities_fragment_routes(app, db, limiter):
    @app.route('/characters/<character_id>/abilities-skills/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def abilities_skills_fragment(character_id: str):
        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            sheet.save_ability_values(character_id, request.form)
            data = sheet.create_form()
            return render_template(
                'components/abilities/abilities_section.html',
                abilities=data['abilities'],
                character_id=character_id,
                is_guest=True,
            )
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        transformed_form = BuffProcessor(character_id).transform_in(request.form)
        sheet.save_ability_values(character_id, transformed_form)

        abilities = sheet.fetch_abilities_data()
        character = sheet.fetch_character_row()
        custom_buffs = sheet.fetch_custom_buffs_data()
        BuffProcessor(character_id).transform_out({'character': character, 'abilities': abilities, 'custom_buffs': custom_buffs})

        return render_template(
            'components/abilities/abilities_section.html',
            abilities=abilities,
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
                'components/abilities/ability_row.html',
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

        ability_data = sheet.fetch_single_ability_data(normalized_ability_name)
        if not ability_data:
            abort(404)

        character = sheet.fetch_character_row()
        custom_buffs = sheet.fetch_custom_buffs_data()
        BuffProcessor(character_id).transform_out({'character': character, 'abilities': [ability_data], 'custom_buffs': custom_buffs})

        return render_template(
            'components/abilities/ability_row.html',
            ability_name=ability_data['ability_name'],
            ability=ability_data['ability'],
            skills=ability_data['skills'],
            skill_list=ability_data['skill_list'],
            character_id=character_id,
            is_guest=False,
        )
