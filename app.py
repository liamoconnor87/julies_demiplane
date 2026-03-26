from datetime import timedelta
from functools import wraps

from flask import Flask, abort, make_response, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFProtect
from flask_login import current_user, login_required
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

from character_sheet.character_sheet import CharacterSheet
from character_sheet.custom_buff import BuffProcessor
from character_sheet import guest_character as guest
from go_get_it.go_get_it import GoGetDB
from functions.functions import uuid as generate_uuid
from functions.validators import is_valid_uuid
from auth import setup_auth
from auth.models import User
from misc.config import DEBUG, secret_key, SESSION_FILE_DIR  # type: ignore

# ── App creation ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = secret_key

# ── Request size limit (16 KB) ────────────────────────────────────────────────
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024

# ── Server-side sessions (filesystem) ─────────────────────────────────────────
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = SESSION_FILE_DIR
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
app.config['SESSION_FILE_THRESHOLD'] = 500
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# ── CSRF ──────────────────────────────────────────────────────────────────────
CSRFProtect(app)

# ── Rate limiting ─────────────────────────────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=['60/minute'],
    storage_uri='memory://',
)

# ── Security headers (Talisman) ──────────────────────────────────────────────
csp = {
    'default-src': "'self'",
    'script-src': [
        "'self'",
        'https://cdn.jsdelivr.net',
        'https://unpkg.com',
    ],
    'style-src': [
        "'self'",
        "'unsafe-inline'",
        'https://cdn.jsdelivr.net',
    ],
    'font-src': [
        "'self'",
        'https://cdn.jsdelivr.net',
    ],
    'img-src': "'self' data:",
}
Talisman(
    app,
    force_https=not DEBUG,
    content_security_policy=csp,
    session_cookie_secure=not DEBUG,
)

# ── Database & auth ───────────────────────────────────────────────────────────
db = GoGetDB()
db.go_create_db()  # ensure tables exist regardless of how the app is started
setup_auth(app, db, limiter)


# ── Guest helpers ─────────────────────────────────────────────────────────────

def guest_or_login_required(f):
    """Allow authenticated users OR active guest sessions; 403 otherwise."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        if guest.is_guest():
            # Validate that the character_id in the URL belongs to this guest
            character_id = kwargs.get('character_id')
            if character_id and character_id != guest.get_guest_character_id():
                abort(403)
            return f(*args, **kwargs)
        abort(403)
    return decorated

def _build_character_sheet_data(character_id: str):
    sheet = CharacterSheet(character_id=character_id)
    data = sheet.create_form()
    BuffProcessor(character_id).transform_out(data)
    return sheet, data

@app.route('/', methods=['GET'])
def character_sheet():

    # ── Guest branch (auto-create on first visit) ──────────────────────────
    if not current_user.is_authenticated:
        guest.create_blank()  # no-op if guest session already exists
        character_id = guest.get_guest_character_id()
        data = guest.create_form()
        is_new_character = not data['character'].get('name')

        return render_template(
            'index.html',
            characters=[],
            active_character_id=character_id,
            at_character_limit=True,
            is_new_character=is_new_character,
            is_guest=True,
            character_id=character_id,
            character=data['character'],
            classes=data['classes'],
            class_options=data['class_options'],
            abilities=data['abilities'],
            feats_and_traits=data['feats_and_traits'],
            feats_and_traits_at_capacity=data['feats_and_traits_at_capacity'],
            inventory=data['inventory'],
            inventory_at_capacity=data['inventory_at_capacity'],
            custom_stats=data['custom_stats'],
            custom_stats_at_capacity=data['custom_stats_at_capacity'],
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            trackers=[],
        )

    characters = User.get_characters(db, current_user.id)
    at_character_limit = User.at_character_limit(db, current_user.id)
    character_id = request.args.get('character_id')

    # If no character_id specified, default to first owned character
    if not character_id and characters:
        character_id = characters[0]['id']

    # Verify ownership
    if character_id and not User.owns_character(db, current_user.id, character_id):
        abort(403)

    active_character_id = character_id

    # ── Unsaved new character (no DB row yet) ──────────────────────────────
    if request.args.get('new') == 'true':
        blank_character = {
            'id': None, 'name': None, 'level': 0,
            'race': None, 'background': None, 'alignment': None,
            'armour_class': None, 'initiative': None, 'speed': None,
            'proficiency': None, 'passive_wisdom': None, 'xp': None,
            'health_points': None, 'hit_dice': None,
            'temporary_hit_points': None,
        }
        return render_template(
            'index.html',
            characters=characters,
            active_character_id=None,
            at_character_limit=at_character_limit,
            is_new_character=True,
            is_unsaved=True,
            is_guest=False,
            character_id=None,
            character=blank_character,
            classes=[],
            class_options=[],
            abilities=[],
            feats_and_traits=[],
            feats_and_traits_at_capacity=False,
            inventory=[],
            inventory_at_capacity=False,
            custom_stats=[],
            custom_stats_at_capacity=False,
            custom_buffs=[],
            custom_buffs_at_capacity=False,
            buff_target_options={},
            trackers=[],
        )

    if not character_id:
        return render_template(
            'index.html',
            characters=characters,
            active_character_id=active_character_id,
            at_character_limit=at_character_limit,
            is_guest=False,
            character=None,
            trackers=[],
        )

    _, character_sheet_data = _build_character_sheet_data(character_id)

    # Detect if this is a brand-new character (no name set yet)
    is_new_character = not character_sheet_data['character'].get('name')

    return render_template(
        'index.html',
        characters=characters,
        active_character_id=active_character_id,
        at_character_limit=at_character_limit,
        is_new_character=is_new_character,
        is_guest=False,
        character_id=character_id,
        character=character_sheet_data['character'],
        classes=character_sheet_data['classes'],
        class_options=character_sheet_data['class_options'],
        abilities=character_sheet_data['abilities'],
        feats_and_traits=character_sheet_data['feats_and_traits'],
        feats_and_traits_at_capacity=character_sheet_data['feats_and_traits_at_capacity'],
        inventory=character_sheet_data['inventory'],
        inventory_at_capacity=character_sheet_data['inventory_at_capacity'],
        custom_stats=character_sheet_data['custom_stats'],
        custom_stats_at_capacity=character_sheet_data['custom_stats_at_capacity'],
        custom_buffs=character_sheet_data['custom_buffs'],
        custom_buffs_at_capacity=character_sheet_data['custom_buffs_at_capacity'],
        buff_target_options=character_sheet_data['buff_target_options'],
        trackers=_get_trackers(character_id),
    )


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

    sheet = CharacterSheet(character_id=None)
    character_id = sheet.save_character_values(request.form)

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
            'components/delete_character_dropdown.html',
            character_id=character_id,
            character=char,
            error='You must type DELETE to confirm.',
        ), 200

    User.delete_character(db, current_user.id, character_id)

    resp = make_response('', 200)
    resp.headers['HX-Redirect'] = '/'
    return resp

@app.route('/characters/<character_id>/character-info/fragment', methods=['POST'])
@guest_or_login_required
@limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
def character_info_fragment(character_id: str):
    if guest.is_guest() and not current_user.is_authenticated:
        guest.save_character_values(request.form)
        data = guest.create_form()
        return render_template(
            'components/character_info_change_response.html',
            character_id=character_id,
            character=data['character'],
            abilities=data['abilities'],
            is_guest=True,
        )
    if not User.owns_character(db, current_user.id, character_id):
        abort(403)
    sheet = CharacterSheet(character_id=character_id)
    request_form = BuffProcessor(character_id).transform_in(request.form)
    sheet.save_character_values(request_form)

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/character_info_change_response.html',
        character_id=character_id,
        character=data['character'],
        abilities=data['abilities'],
        is_guest=False,
    )

@app.route('/characters/<character_id>/classes/fragment', methods=['POST'])
@guest_or_login_required
@limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
def classes_fragment(character_id: str):
    if guest.is_guest() and not current_user.is_authenticated:
        guest.save_class_to_character_values(request.form)
        data = guest.create_form()
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

    _, data = _build_character_sheet_data(character_id)
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
        guest.save_feat_and_trait_values(request.form)
        data = guest.create_form()
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

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/feats_traits_section.html',
        character_id=character_id,
        feats_and_traits=data['feats_and_traits'],
        feats_and_traits_at_capacity=data['feats_and_traits_at_capacity'],
        is_guest=False,
    )

@app.route('/characters/<character_id>/abilities-skills/fragment', methods=['POST'])
@guest_or_login_required
@limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
def abilities_skills_fragment(character_id: str):
    if guest.is_guest() and not current_user.is_authenticated:
        guest.save_ability_values(request.form)
        data = guest.create_form()
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

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/abilities_section.html',
        abilities=data['abilities'],
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

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/inventory_section.html',
        inventory=data['inventory'],
        inventory_at_capacity=data['inventory_at_capacity'],
        character_id=character_id
    )

@app.route('/characters/<character_id>/custom-stats/fragment', methods=['POST'])
@guest_or_login_required
@limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
def custom_stats_fragment(character_id: str):
    if guest.is_guest() and not current_user.is_authenticated:
        guest.save_custom_stat_values(request.form)
        data = guest.create_form()
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

    _, data = _build_character_sheet_data(character_id)
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


@app.route('/characters/<character_id>/custom-buffs/fragment', methods=['POST'])
@login_required
def custom_buffs_fragment(character_id: str):
    if not User.owns_character(db, current_user.id, character_id):
        abort(403)
    sheet = CharacterSheet(character_id=character_id)
    sheet.save_custom_buff_values(character_id, request.form)

    _, data = _build_character_sheet_data(character_id)
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

    _, data = _build_character_sheet_data(character_id)
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
    return '', 200


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
    return render_template('components/inventory_row.html', item=item, character_id=character_id)


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
    return render_template('components/inventory_row.html', item=item, character_id=character_id)


@app.route('/characters/<character_id>/feat-and-trait/<feat_and_trait_id>/remove', methods=['POST'])
@guest_or_login_required
@limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
def remove_feat_and_trait_item(character_id: str, feat_and_trait_id: str):
    if guest.is_guest() and not current_user.is_authenticated:
        guest.remove_feat_and_trait(feat_and_trait_id)
        return '', 200
    if not User.owns_character(db, current_user.id, character_id):
        abort(403)
    if not character_id or not feat_and_trait_id or not db.go_get_one('feat_and_trait', {'id': feat_and_trait_id, 'character_id': character_id}):
        return redirect(url_for('character_sheet'))

    db.go_delete_it('feat_and_trait', {'id': feat_and_trait_id, 'character_id': character_id})
    return '', 200


@app.route('/characters/<character_id>/feat-and-trait/<feat_and_trait_id>/update', methods=['POST'])
@guest_or_login_required
@limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
def update_feat_and_trait_item(character_id: str, feat_and_trait_id: str):
    name = request.form.get(f'feat_and_trait-name-{feat_and_trait_id}', '')
    description = request.form.get(f'feat_and_trait-description-{feat_and_trait_id}', '')
    if guest.is_guest() and not current_user.is_authenticated:
        feat = guest.update_single_feat(feat_and_trait_id, name, description)
        if not feat:
            abort(400)
        return render_template('components/feat_row.html', feat=feat, character_id=character_id)
    if not User.owns_character(db, current_user.id, character_id):
        abort(403)
    sheet = CharacterSheet(character_id=character_id)
    feat = sheet.update_single_feat(character_id, feat_and_trait_id, name, description)
    if not feat:
        abort(400)
    return render_template('components/feat_row.html', feat=feat, character_id=character_id)


@app.route('/characters/<character_id>/feat-and-trait/add', methods=['POST'])
@guest_or_login_required
@limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
def add_feat_and_trait_item(character_id: str):
    name = request.form.get('feat_and_trait-name', '')
    description = request.form.get('feat_and_trait-description', '')
    if guest.is_guest() and not current_user.is_authenticated:
        feat = guest.add_single_feat(name, description)
        if not feat:
            abort(400)
        return render_template('components/feat_row.html', feat=feat, character_id=character_id)
    if not User.owns_character(db, current_user.id, character_id):
        abort(403)
    sheet = CharacterSheet(character_id=character_id)
    feat = sheet.add_single_feat(character_id, name, description)
    if not feat:
        abort(400)
    return render_template('components/feat_row.html', feat=feat, character_id=character_id)


@app.route('/characters/<character_id>/custom-stat/<custom_stat_id>/remove', methods=['POST'])
@guest_or_login_required
@limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
def remove_custom_stat_item(character_id: str, custom_stat_id: str):
    if guest.is_guest() and not current_user.is_authenticated:
        guest.remove_custom_stat(custom_stat_id)
        data = guest.create_form()
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

    db.go_delete_it('custom_stat', {'id': custom_stat_id, 'character_id': character_id})

    _, data = _build_character_sheet_data(character_id)
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

    custom_buff_tables = db.go_get_all('custom_buff_to_stat_table', {'custom_buff_id': custom_buff_id, 'character_id': character_id}) or []
    for custom_buff_table in custom_buff_tables:
        stat_table_id = custom_buff_table.get('stat_table_id')
        table_link_id = custom_buff_table.get('id')
        if stat_table_id:
            for table_stat in db.go_get_all('stat_table_to_stat', {'stat_table_id': stat_table_id, 'character_id': character_id}) or []:
                if table_stat.get('id'):
                    db.go_delete_it('stat_table_to_stat', {'id': table_stat['id']})
        if table_link_id:
            db.go_delete_it('custom_buff_to_stat_table', {'id': table_link_id})

    db.go_delete_it('custom_buff', {'id': custom_buff_id, 'character_id': character_id})

    _, data = _build_character_sheet_data(character_id)
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
        guest.remove_class(class_id)
        data = guest.create_form()
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

    db.go_delete_it('class_to_character', {'id': class_id, 'character_id': character_id})

    _, data = _build_character_sheet_data(character_id)
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


def _get_trackers(character_id: str):
    """Return all trackers (with entries) for a character, ordered by id."""
    trackers = db.go_get_all('tracker', {'character_id': character_id}) or []
    result = []
    for t in trackers:
        entries = db.go_get_all('tracker_entry', {'tracker_id': t['id']}) or []
        result.append({'id': t['id'], 'name': t['name'], 'entries': list(entries)})
    return result


def _render_tracker_page(character_id: str):
    return render_template(
        'components/tracker_page.html',
        character_id=character_id,
        trackers=_get_trackers(character_id),
    )


@app.route('/characters/<character_id>/tracker/add', methods=['POST'])
@login_required
def add_tracker(character_id: str):
    if not User.owns_character(db, current_user.id, character_id):
        abort(403)
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
def remove_tracker(character_id: str, tracker_id: str):
    if not User.owns_character(db, current_user.id, character_id):
        abort(403)
    tracker = db.go_get_one('tracker', {'id': tracker_id, 'character_id': character_id})
    if tracker:
        for entry in db.go_get_all('tracker_entry', {'tracker_id': tracker_id}) or []:
            db.go_delete_it('tracker_entry', {'id': entry['id']})
        db.go_delete_it('tracker', {'id': tracker_id, 'character_id': character_id})
    return _render_tracker_page(character_id)


@app.route('/characters/<character_id>/tracker/<tracker_id>/entry/add', methods=['POST'])
@login_required
def add_tracker_entry(character_id: str, tracker_id: str):
    if not User.owns_character(db, current_user.id, character_id):
        abort(403)
    if not db.go_get_one('tracker', {'id': tracker_id, 'character_id': character_id}):
        abort(403)
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
def remove_tracker_entry(character_id: str, tracker_id: str, entry_id: str):
    if not User.owns_character(db, current_user.id, character_id):
        abort(403)
    entry = db.go_get_one('tracker_entry', {'id': entry_id, 'tracker_id': tracker_id})
    if entry:
        tracker = db.go_get_one('tracker', {'id': tracker_id, 'character_id': character_id})
        if tracker:
            db.go_delete_it('tracker_entry', {'id': entry_id, 'tracker_id': tracker_id})
    return _render_tracker_page(character_id)


if __name__ == '__main__':
    # Create the database
    db.go_create_db()
    # Sync the database schema
    db.go_sync_schema()
    # Seed the database
    db.go_seed_db()
    # Run the Flask app on port 8888
    app.run(host='0.0.0.0', port=8888, debug=DEBUG)
