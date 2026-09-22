from flask import abort
from flask_login import current_user, login_required

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet


def register_spells_fragment_routes(app, db, limiter):
    @app.route('/characters/<character_id>/spell/<spell_id>/toggle-known', methods=['POST'])
    @login_required
    def toggle_spell_known_item(character_id: str, spell_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        if not db.go_get_one('spell', {'id': spell_id}):
            abort(404)
        sheet = CharacterSheet(character_id=character_id)
        sheet.toggle_spell_known(spell_id)
        # htmx excludes 204 from its "should settle" check, so afterSettle never
        # fires and the global loading spinner is left stuck -- 200 with an
        # empty body is the same "nothing to swap" signal without that gotcha.
        return '', 200

    @app.route('/characters/<character_id>/spell/<spell_id>/toggle-prepared', methods=['POST'])
    @login_required
    def toggle_spell_prepared_item(character_id: str, spell_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        if not db.go_get_one('spell', {'id': spell_id}):
            abort(404)
        sheet = CharacterSheet(character_id=character_id)
        sheet.toggle_spell_prepared(spell_id)
        return '', 200
