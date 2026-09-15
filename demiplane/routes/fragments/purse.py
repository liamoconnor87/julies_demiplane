from flask import abort, render_template, request
from flask_login import current_user, login_required

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet


def register_purse_fragment_routes(app, db, limiter):
    @app.route('/characters/<character_id>/purse/update', methods=['POST'])
    @login_required
    @limiter.limit('30/minute')
    def update_purse(character_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        sheet = CharacterSheet(character_id=character_id)
        purse = sheet.save_purse_values(character_id, request.form)

        return render_template(
            'components/inventory/purse_section.html',
            purse=purse,
            character_id=character_id,
        )
