from datetime import datetime
from xml.sax.saxutils import escape

from flask import abort, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet
from demiplane.services import guest_character as guest
from demiplane.functions.functions import uuid as generate_uuid
from db.config import CANONICAL_URL


def register_dnd_character_sheet_routes(app, db, limiter):
    @app.route('/guest/start', methods=['POST'])
    @limiter.limit('5/hour')
    def guest_start():
        """Create a blank guest character in the session and redirect to /."""
        if current_user.is_authenticated:
            return redirect(url_for('character_sheet'))
        guest.create_blank()
        resp = make_response('', 200)
        resp.headers['HX-Redirect'] = '/'
        return resp

    @app.route('/robots.txt', methods=['GET'])
    def robots_txt():
        content = [
            'User-agent: *',
            'Allow: /',
            'Disallow: /admin',
            'Disallow: /characters/',
            f'Sitemap: {CANONICAL_URL}/sitemap.xml',
        ]
        return app.response_class('\n'.join(content) + '\n', mimetype='text/plain')

    @app.route('/sitemap.xml', methods=['GET'])
    def sitemap_xml():
        homepage = f'{CANONICAL_URL}/'
        lastmod = datetime.utcnow().date().isoformat()
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <url>\n'
            f'    <loc>{escape(homepage)}</loc>\n'
            f'    <lastmod>{lastmod}</lastmod>\n'
            '    <changefreq>weekly</changefreq>\n'
            '    <priority>1.0</priority>\n'
            '  </url>\n'
            '</urlset>\n'
        )
        return app.response_class(xml, mimetype='application/xml')

    @app.route('/characters/new', methods=['POST'])
    @login_required
    def create_character():
        if User.at_character_limit(db, current_user.id):
            abort(403)

        # Redirect to an unsaved blank form — nothing is persisted yet.
        resp = make_response('', 200)
        resp.headers['HX-Redirect'] = '/?new=true'
        return resp

    @app.route('/characters/first-save', methods=['POST'])
    @login_required
    def first_save_character():
        """Persist a brand-new character for the first time."""
        if User.at_character_limit(db, current_user.id):
            abort(403)

        # First-save must always create a new character; reject tampered IDs.
        if (request.form.get('character-id') or '').strip():
            abort(400)

        sheet = CharacterSheet(character_id=None)
        create_payload = request.form.to_dict(flat=True)
        create_payload['character-id'] = ''
        character_id = sheet.save_character_values(create_payload)

        db.go_add_new('user_to_character', {
            'id': generate_uuid(),
            'user_id': current_user.id,
            'character_id': character_id,
        })

        resp = make_response('', 200)
        resp.headers['HX-Redirect'] = f'/?character_id={character_id}'
        return resp

    @app.route('/characters/<character_id>/delete', methods=['DELETE'])
    @login_required
    def delete_character(character_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        confirmation = request.form.get('confirmation', '')
        if confirmation != 'DELETE':
            char = db.go_get_one('character', {'id': character_id})
            return render_template(
                'components/auth/delete_character_dropdown.html',
                character_id=character_id,
                character=char,
                error='You must type DELETE to confirm.',
            ), 200

        User.delete_character(db, current_user.id, character_id)

        resp = make_response('', 200)
        resp.headers['HX-Redirect'] = '/'
        return resp
