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
from auth.models import UserTheme
from auth.validators import is_valid_css_colour
from misc.config import DEBUG, secret_key, SESSION_FILE_DIR  # type: ignore
from go_get_it.tables import TABLES

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
        'https://fonts.googleapis.com',
    ],
    'font-src': [
        "'self'",
        'https://cdn.jsdelivr.net',
        'https://fonts.gstatic.com',
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


_DEATH_SAVES_TRACKER_ID = 'death-saves'


def _build_death_saves_tracker():
    return {
        'id': _DEATH_SAVES_TRACKER_ID,
        'name': 'Death Saves',
        'fixed': True,
        'entries': [
            {'id': 'death-saves-pass', 'tracker_id': _DEATH_SAVES_TRACKER_ID, 'name': 'Pass', 'value': 3},
            {'id': 'death-saves-fail', 'tracker_id': _DEATH_SAVES_TRACKER_ID, 'name': 'Fail', 'value': 3},
        ],
    }

@app.route('/', methods=['GET'])
def character_sheet():

    # ── Guest branch (auto-create on first visit) ──────────────────────────
    if not current_user.is_authenticated:
        guest.create_blank()  # no-op if guest session already exists
        character_id = guest.get_guest_character_id()
        data = guest.create_form()
        is_new_character = not data['character'].get('name')
        guest_name = str(data['character'].get('name') or '').strip()
        landing_requested = (request.args.get('landing') or '').strip() == '1'

        # Landing panel is visible for first-time guests, or when a named guest
        # explicitly returns to landing mode via the navbar title.
        show_guest_landing_panel = is_new_character or (landing_requested and bool(guest_name))
        show_guest_name_entry = is_new_character
        guest_show_sheet = not (landing_requested and bool(guest_name))

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
            guest_death_saves_tracker=_build_death_saves_tracker(),
            show_guest_landing_panel=show_guest_landing_panel,
            show_guest_name_entry=show_guest_name_entry,
            guest_show_sheet=guest_show_sheet,
            guest_character_name=guest_name,
        )

    characters = User.get_characters(db, current_user.id)
    at_character_limit = User.at_character_limit(db, current_user.id)
    user_theme = UserTheme.get_by_user_id(db, current_user.id)
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
            user_theme=user_theme,
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
            user_theme=user_theme,
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
        user_theme=user_theme,
    )


@app.route('/user/theme/save', methods=['POST'])
@login_required
def save_user_theme():
    """Persist the user's colour theme and return an OOB style block update."""
    colour_fields = [
        'background_colour', 'border_colour', 'label_colour',
        'tracker_fill_colour', 'asterisk_colour', 'field_text_colour',
        'level_colour', 'button_icon_colour', 'title_colour',
        'field_bg_colour',
    ]
    colours = {}
    for field in colour_fields:
        value = (request.form.get(field) or '').strip()
        if not is_valid_css_colour(value):
            abort(400)
        colours[field] = value

    UserTheme.save(db, current_user.id, colours)
    return render_template('components/theme_vars_oob.html', colours=colours), 200


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


@app.route('/characters/<character_id>/combat/fragment', methods=['POST'])
@guest_or_login_required
@limiter.limit('30/minute', exempt_when=lambda: current_user.is_authenticated)
def combat_fragment(character_id: str):
    if guest.is_guest() and not current_user.is_authenticated:
        guest.save_character_values(request.form)
        data = guest.create_form()
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

    _, data = _build_character_sheet_data(character_id)
    return render_template('components/combat_stats.html', character_id=character_id, character=data['character'])


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
    death_saves = _build_death_saves_tracker()
    trackers = db.go_get_all('tracker', {'character_id': character_id}) or []
    result = [death_saves]
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


def _get_single_tracker(character_id: str, tracker_id: str):
    """Return a single tracker dict (with entries) or None."""
    tracker = db.go_get_one('tracker', {'id': tracker_id, 'character_id': character_id})
    if not tracker:
        return None
    entries = db.go_get_all('tracker_entry', {'tracker_id': tracker_id}) or []
    return {'id': tracker['id'], 'name': tracker['name'], 'entries': list(entries)}


def _render_tracker_item(character_id: str, tracker_id: str):
    tracker = _get_single_tracker(character_id, tracker_id)
    if not tracker:
        abort(404)
    return render_template(
        'components/tracker_item.html',
        character_id=character_id,
        tracker=tracker,
    )


@app.route('/characters/<character_id>/tracker/<tracker_id>/update', methods=['POST'])
@login_required
def update_tracker(character_id: str, tracker_id: str):
    if not User.owns_character(db, current_user.id, character_id):
        abort(403)
    tracker = db.go_get_one('tracker', {'id': tracker_id, 'character_id': character_id})
    if not tracker:
        abort(404)
    # Update tracker name
    name = request.form.get('tracker-name', '').strip()[:60]
    if name:
        db.go_update('tracker', {'id': tracker_id, 'name': name})
    # Update entries
    entries = db.go_get_all('tracker_entry', {'tracker_id': tracker_id}) or []
    for entry in entries:
        eid = entry['id']
        entry_name = request.form.get(f'entry-name-{eid}', '').strip()[:40]
        entry_value_raw = request.form.get(f'entry-value-{eid}', '')
        updates = {}
        if entry_name:
            updates['name'] = entry_name
        if entry_value_raw:
            try:
                updates['value'] = max(1, min(20, int(entry_value_raw)))
            except (ValueError, TypeError):
                pass
        if updates:
            updates['id'] = eid
            db.go_update('tracker_entry', updates)
    return _render_tracker_item(character_id, tracker_id)


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


# ══════════════════════════════════════════════════════════════════════════════
#  Admin routes
# ══════════════════════════════════════════════════════════════════════════════

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# FK relationships: table → (fk_column, parent_table)
_CHILD_TABLES_BY_CHARACTER = [
    ('inventory', 'character_id'),
    ('feat_and_trait', 'character_id'),
    ('class_to_character', 'character_id'),
    ('custom_stat', 'character_id'),
    ('custom_buff', 'character_id'),
    ('custom_buff_to_stat_table', 'character_id'),
    ('stat_table_to_stat', 'character_id'),
    ('strength', 'character_id'),
    ('dexterity', 'character_id'),
    ('constitution', 'character_id'),
    ('intelligence', 'character_id'),
    ('wisdom', 'character_id'),
    ('charisma', 'character_id'),
    ('tracker', 'character_id'),
]

_ABILITY_TABLES = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']

_SKILL_TABLE_MAP = {
    'strength': 'strength_skills',
    'dexterity': 'dexterity_skills',
    'constitution': 'constitution_skills',
    'intelligence': 'intelligence_skills',
    'wisdom': 'wisdom_skills',
    'charisma': 'charisma_skills',
}


_FK_TO_PARENT = {
    'user_id': 'user',
    'character_id': 'character',
    'class_id': 'class',
    'tracker_id': 'tracker',
    'custom_buff_id': 'custom_buff',
    'strength_id': 'strength',
    'dexterity_id': 'dexterity',
    'constitution_id': 'constitution',
    'intelligence_id': 'intelligence',
    'wisdom_id': 'wisdom',
    'charisma_id': 'charisma',
}


def _find_orphans():
    """Find all rows with FK references to non-existent parent rows."""
    orphans = []
    for table_name, schema in TABLES.items():
        for col_name in schema:
            if col_name in _FK_TO_PARENT:
                parent_table = _FK_TO_PARENT[col_name]
                rows = db.go_get_all(table_name) or []
                for row in rows:
                    fk_val = row.get(col_name)
                    if fk_val:
                        parent = db.go_get_one(parent_table, {'id': fk_val})
                        if not parent:
                            orphans.append({
                                'table': table_name,
                                'row': row,
                                'fk_col': col_name,
                                'missing_parent': parent_table,
                                'missing_id': fk_val,
                            })
    return orphans


def _count_orphans():
    return len(_find_orphans())


def _admin_table_columns(table_name):
    if table_name not in TABLES:
        return []
    return list(TABLES[table_name].keys())


def _admin_fk_links(table_name):
    """Return dict of column → URL prefix for FK links."""
    links = {}
    schema = TABLES.get(table_name, {})
    if 'character_id' in schema:
        links['character_id'] = '/admin/character/'
    if 'user_id' in schema:
        links['user_id'] = '/admin/user/'
    return links


@app.route('/admin')
@admin_required
def admin_home():
    users = db.go_get_all('user') or []
    for user in users:
        links = db.go_get_all('user_to_character', {'user_id': user['id']}) or []
        user['character_count'] = len(links)

    # Count orphaned rows for the badge
    orphan_count = _count_orphans()

    return render_template('admin.html',
        view='users',
        users=users,
        all_tables=list(TABLES.keys()),
        orphan_count=orphan_count,
        breadcrumbs=[{'label': 'Admin', 'url': '/admin'}],
    )


@app.route('/admin/orphans')
@admin_required
def admin_orphans():
    orphans = _find_orphans()
    grouped = {}
    for o in orphans:
        grouped.setdefault(o['table'], []).append(o)
    return render_template('admin.html',
        view='orphans',
        orphan_groups=grouped,
        orphan_count=len(orphans),
        breadcrumbs=[
            {'label': 'Admin', 'url': '/admin'},
            {'label': 'Orphaned Data', 'url': '/admin/orphans'},
        ],
    )


@app.route('/admin/user/<user_id>')
@admin_required
def admin_user_detail(user_id):
    user = db.go_get_one('user', {'id': user_id})
    if not user:
        abort(404)
    links = db.go_get_all('user_to_character', {'user_id': user_id}) or []
    characters = []
    for link in links:
        char = db.go_get_one('character', {'id': link['character_id']})
        if char:
            characters.append(char)
    return render_template('admin.html',
        view='user_detail',
        user=user,
        characters=characters,
        breadcrumbs=[
            {'label': 'Admin', 'url': '/admin'},
            {'label': user['username'], 'url': f'/admin/user/{user_id}'},
        ],
    )


@app.route('/admin/character/<character_id>')
@admin_required
def admin_character_detail(character_id):
    character = db.go_get_one('character', {'id': character_id})
    if not character:
        abort(404)

    child_links = []
    for table_name, fk_col in _CHILD_TABLES_BY_CHARACTER:
        rows = db.go_get_all(table_name, {fk_col: character_id}) or []
        child_links.append({
            'label': table_name.replace('_', ' ').title(),
            'url': f'/admin/table/{table_name}?filter_col={fk_col}&filter_val={character_id}',
            'count': len(rows),
        })

    # Ability skills (linked via ability_id FK, not character_id)
    for ability in _ABILITY_TABLES:
        skill_table = _SKILL_TABLE_MAP[ability]
        ability_row = db.go_get_one(ability, {'character_id': character_id})
        if ability_row:
            fk_col = f'{ability}_id'
            skill_rows = db.go_get_all(skill_table, {fk_col: ability_row['id']}) or []
            child_links.append({
                'label': skill_table.replace('_', ' ').title(),
                'url': f'/admin/table/{skill_table}?filter_col={fk_col}&filter_val={ability_row["id"]}',
                'count': len(skill_rows),
            })

    # Tracker entries (linked via tracker_id)
    trackers = db.go_get_all('tracker', {'character_id': character_id}) or []
    for tracker in trackers:
        entries = db.go_get_all('tracker_entry', {'tracker_id': tracker['id']}) or []
        child_links.append({
            'label': f'Tracker Entries ({tracker["name"] or tracker["id"][:8]})',
            'url': f'/admin/table/tracker_entry?filter_col=tracker_id&filter_val={tracker["id"]}',
            'count': len(entries),
        })

    # Find owning user for breadcrumb
    link = db.go_get_one('user_to_character', {'character_id': character_id})
    user = db.go_get_one('user', {'id': link['user_id']}) if link else None

    breadcrumbs = [{'label': 'Admin', 'url': '/admin'}]
    if user:
        breadcrumbs.append({'label': user['username'], 'url': f'/admin/user/{user["id"]}'})
    breadcrumbs.append({'label': character.get('name') or '(unnamed)', 'url': f'/admin/character/{character_id}'})

    return render_template('admin.html',
        view='character_detail',
        character=character,
        child_links=child_links,
        breadcrumbs=breadcrumbs,
    )


@app.route('/admin/table/<table_name>')
@admin_required
def admin_table_view(table_name):
    if table_name not in TABLES:
        abort(404)

    filter_col = request.args.get('filter_col')
    filter_val = request.args.get('filter_val')
    current_url = request.url

    if filter_col and filter_val and filter_col in TABLES[table_name]:
        rows = db.go_get_all(table_name, {filter_col: filter_val}) or []
    else:
        rows = db.go_get_all(table_name) or []
        filter_col = None
        filter_val = None

    columns = _admin_table_columns(table_name)
    fk_links = _admin_fk_links(table_name)

    # Enrich rows with display names for FK columns
    schema = TABLES.get(table_name, {})
    for row in rows:
        display = {}
        if 'character_id' in schema and row.get('character_id'):
            char = db.go_get_one('character', {'id': row['character_id']})
            if char:
                display['character_id'] = char.get('name') or '(unnamed)'
        if 'user_id' in schema and row.get('user_id'):
            u = db.go_get_one('user', {'id': row['user_id']})
            if u:
                display['user_id'] = u.get('username') or '(unknown)'
        if 'class_id' in schema and row.get('class_id'):
            cls = db.go_get_one('class', {'id': row['class_id']})
            if cls:
                display['class_id'] = cls.get('name') or '(unknown)'
        if 'tracker_id' in schema and row.get('tracker_id'):
            t = db.go_get_one('tracker', {'id': row['tracker_id']})
            if t:
                display['tracker_id'] = t.get('name') or '(unknown)'
        if 'custom_buff_id' in schema and row.get('custom_buff_id'):
            b = db.go_get_one('custom_buff', {'id': row['custom_buff_id']})
            if b:
                display['custom_buff_id'] = b.get('name') or '(unknown)'
        # Ability skill FK columns (strength_id, dexterity_id, etc.)
        for ability in _ABILITY_TABLES:
            fk_col_name = f'{ability}_id'
            if fk_col_name in schema and row.get(fk_col_name):
                ability_row = db.go_get_one(ability, {'id': row[fk_col_name]})
                if ability_row and ability_row.get('character_id'):
                    char = db.go_get_one('character', {'id': ability_row['character_id']})
                    if char:
                        display[fk_col_name] = f'{ability.title()} → {char.get("name") or "(unnamed)"}'
        row['_display'] = display

    # Build breadcrumbs — try to trace back to character → user
    breadcrumbs = [{'label': 'Admin', 'url': '/admin'}]
    if filter_col == 'character_id' and filter_val:
        char = db.go_get_one('character', {'id': filter_val})
        link = db.go_get_one('user_to_character', {'character_id': filter_val})
        user = db.go_get_one('user', {'id': link['user_id']}) if link else None
        if user:
            breadcrumbs.append({'label': user['username'], 'url': f'/admin/user/{user["id"]}'})
        if char:
            breadcrumbs.append({'label': char.get('name') or '(unnamed)', 'url': f'/admin/character/{filter_val}'})
    elif filter_col and filter_val and filter_col.endswith('_id'):
        # Try to find parent ability → character for skill tables
        parent_table = filter_col.replace('_id', '')
        if parent_table in _ABILITY_TABLES:
            ability_row = db.go_get_one(parent_table, {'id': filter_val})
            if ability_row and ability_row.get('character_id'):
                cid = ability_row['character_id']
                char = db.go_get_one('character', {'id': cid})
                link = db.go_get_one('user_to_character', {'character_id': cid})
                user = db.go_get_one('user', {'id': link['user_id']}) if link else None
                if user:
                    breadcrumbs.append({'label': user['username'], 'url': f'/admin/user/{user["id"]}'})
                if char:
                    breadcrumbs.append({'label': char.get('name') or '(unnamed)', 'url': f'/admin/character/{cid}'})
    breadcrumbs.append({'label': table_name.replace('_', ' ').title(), 'url': current_url})

    return render_template('admin.html',
        view='table',
        table_name=table_name,
        rows=rows,
        columns=columns,
        fk_links=fk_links,
        filter_col=filter_col,
        filter_val=filter_val,
        current_url=current_url,
        breadcrumbs=breadcrumbs,
    )


@app.route('/admin/table/<table_name>/create', methods=['POST'])
@admin_required
def admin_table_create(table_name):
    if table_name not in TABLES:
        abort(404)
    columns = _admin_table_columns(table_name)
    row = {}
    for col in columns:
        val = request.form.get(f'new-{col}', '').strip()
        if col == 'id' and not val:
            val = generate_uuid()
        row[col] = val if val != '' else None
    db.go_add_new(table_name, row)
    redirect_url = request.form.get('redirect', f'/admin/table/{table_name}')
    return redirect(redirect_url)


@app.route('/admin/table/<table_name>/<row_id>/update', methods=['POST'])
@admin_required
def admin_table_update(table_name, row_id):
    if table_name not in TABLES:
        abort(404)
    if not is_valid_uuid(row_id):
        abort(400)
    columns = _admin_table_columns(table_name)
    row = {'id': row_id}
    for col in columns:
        if col == 'id':
            continue
        val = request.form.get(f'field-{col}', '').strip()
        row[col] = val if val != '' else None
    db.go_update(table_name, row)
    redirect_url = request.form.get('redirect', f'/admin/table/{table_name}')
    return redirect(redirect_url)


@app.route('/admin/table/<table_name>/<row_id>/delete', methods=['POST'])
@admin_required
def admin_table_delete(table_name, row_id):
    if table_name not in TABLES:
        abort(404)
    if not is_valid_uuid(row_id):
        abort(400)

    # Cascade delete for user: remove all their characters and links
    if table_name == 'user':
        links = db.go_get_all('user_to_character', {'user_id': row_id}) or []
        for link in links:
            # Cascade delete each character
            cid = link['character_id']
            for child_table, fk_col in _CHILD_TABLES_BY_CHARACTER:
                child_rows = db.go_get_all(child_table, {fk_col: cid}) or []
                for child_row in child_rows:
                    if child_table in _ABILITY_TABLES:
                        skill_table = _SKILL_TABLE_MAP[child_table]
                        fk = f'{child_table}_id'
                        skill_rows = db.go_get_all(skill_table, {fk: child_row['id']}) or []
                        for sr in skill_rows:
                            db.go_delete_it(skill_table, {'id': sr['id']})
                    if child_table == 'tracker':
                        entries = db.go_get_all('tracker_entry', {'tracker_id': child_row['id']}) or []
                        for entry in entries:
                            db.go_delete_it('tracker_entry', {'id': entry['id']})
                    db.go_delete_it(child_table, {'id': child_row['id']})
            db.go_delete_it('character', {'id': cid})
        db.go_delete_by('user_to_character', {'user_id': row_id})

    # Cascade delete for character: remove all child data
    if table_name == 'character':
        for child_table, fk_col in _CHILD_TABLES_BY_CHARACTER:
            child_rows = db.go_get_all(child_table, {fk_col: row_id}) or []
            for child_row in child_rows:
                # Also cascade skill tables for abilities
                if child_table in _ABILITY_TABLES:
                    skill_table = _SKILL_TABLE_MAP[child_table]
                    fk = f'{child_table}_id'
                    skill_rows = db.go_get_all(skill_table, {fk: child_row['id']}) or []
                    for sr in skill_rows:
                        db.go_delete_it(skill_table, {'id': sr['id']})
                # Cascade tracker entries
                if child_table == 'tracker':
                    entries = db.go_get_all('tracker_entry', {'tracker_id': child_row['id']}) or []
                    for entry in entries:
                        db.go_delete_it('tracker_entry', {'id': entry['id']})
                db.go_delete_it(child_table, {'id': child_row['id']})
        # Remove user_to_character link
        db.go_delete_by('user_to_character', {'character_id': row_id})

    # Cascade delete for tracker: remove tracker entries
    if table_name == 'tracker':
        entries = db.go_get_all('tracker_entry', {'tracker_id': row_id}) or []
        for entry in entries:
            db.go_delete_it('tracker_entry', {'id': entry['id']})

    # Cascade delete for custom_buff: remove buff-to-stat-table links
    if table_name == 'custom_buff':
        links = db.go_get_all('custom_buff_to_stat_table', {'custom_buff_id': row_id}) or []
        for link in links:
            db.go_delete_it('custom_buff_to_stat_table', {'id': link['id']})

    # Cascade delete for ability tables: remove skill rows
    if table_name in _ABILITY_TABLES:
        skill_table = _SKILL_TABLE_MAP[table_name]
        fk = f'{table_name}_id'
        skill_rows = db.go_get_all(skill_table, {fk: row_id}) or []
        for sr in skill_rows:
            db.go_delete_it(skill_table, {'id': sr['id']})

    db.go_delete_it(table_name, {'id': row_id})
    redirect_url = request.form.get('redirect', f'/admin/table/{table_name}')
    return redirect(redirect_url)


@app.route('/admin/table/user/<user_id>/toggle-admin', methods=['POST'])
@admin_required
def admin_toggle_admin(user_id):
    user = db.go_get_one('user', {'id': user_id})
    if not user:
        abort(404)
    user['admin'] = 0 if user.get('admin') else 1
    db.go_update('user', user)
    return redirect('/admin')


if __name__ == '__main__':
    # Create the database
    db.go_create_db()
    # Sync the database schema
    db.go_sync_schema()
    # Seed the database
    db.go_seed_db()
    # Run the Flask app on port 8888
    app.run(host='0.0.0.0', port=8888, debug=DEBUG)
