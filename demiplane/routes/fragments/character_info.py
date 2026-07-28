from flask import abort, render_template, request
from flask_login import current_user
from werkzeug.exceptions import HTTPException

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet
from demiplane.services.custom_buff import BuffProcessor
from demiplane.services import guest_character as guest
from demiplane.functions.feedback import default_feedback, error_feedback, feedback_template_context
from demiplane.routes.helpers import guest_or_login_required, build_character_sheet_data, build_guest_character_sheet_data


def register_character_info_fragment_routes(app, db, limiter):
    @app.route('/characters/<character_id>/character-info/fragment', methods=['POST'])
    @guest_or_login_required
    @limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
    def character_info_fragment(character_id: str):
        feedback = default_feedback()

        if guest.is_guest() and not current_user.is_authenticated:
            sheet, data = build_guest_character_sheet_data(character_id)
            try:
                sheet.save_character_values(request.form)
                data = sheet.create_form()
            except HTTPException:
                raise
            except Exception:
                app.logger.exception('Character info save failed for guest character_id=%s', character_id)
                feedback = error_feedback()
                data = sheet.create_form()

            is_new_character = not data['character'].get('name')
            guest_name = str(data['character'].get('name') or '').strip()
            return render_template(
                'components/character/character_info_change_response.html',
                character_id=character_id,
                character=data['character'],
                abilities=data['abilities'],
                is_guest=True,
                show_guest_landing_panel=is_new_character,
                show_guest_name_entry=is_new_character,
                guest_character_name=guest_name,
                **feedback_template_context('character_info', feedback),
            )

        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        existing_before = db.go_get_one('character', {'id': character_id}) or {}

        sheet = CharacterSheet(character_id=character_id)
        request_form = BuffProcessor(character_id).transform_in(request.form)
        try:
            sheet.save_character_values(request_form)
        except HTTPException:
            raise
        except Exception:
            app.logger.exception('Character info save failed for user_id=%s character_id=%s', current_user.id, character_id)
            feedback = error_feedback()

        # Abilities only need refreshing when proficiency changed — that's the only
        # field on this form that cascades into ability/skill recalculation.
        character = sheet.fetch_character_info_data()
        proficiency_changed = character.get('proficiency') != existing_before.get('proficiency')

        if proficiency_changed:
            _, data = build_character_sheet_data(character_id)
            character = data['character']
            abilities = data['abilities']
            skip_abilities_oob = False
        else:
            custom_buffs = sheet.fetch_custom_buffs_data()
            BuffProcessor(character_id).transform_out({'character': character, 'custom_buffs': custom_buffs})
            abilities = []
            skip_abilities_oob = True

        return render_template(
            'components/character/character_info_change_response.html',
            character_id=character_id,
            character=character,
            abilities=abilities,
            is_guest=False,
            skip_abilities_oob=skip_abilities_oob,
            **feedback_template_context('character_info', feedback),
        )
