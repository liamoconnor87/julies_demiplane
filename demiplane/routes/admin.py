from functools import wraps
from urllib.parse import urlparse

from flask import abort, redirect, render_template, request
from flask_login import current_user

from demiplane.auth.models import UserTheme
from demiplane.functions.functions import uuid as generate_uuid
from demiplane.functions.validators import is_valid_uuid
from go_get_it.tables import TABLES


# FK relationships: table -> (fk_column)
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


def _rows_or_empty(result):
    if isinstance(result, list):
        return result
    return []


def _normalise_internal_redirect(candidate: str, fallback: str):
    """Allow only local relative redirects to avoid open redirect issues."""
    value = (candidate or '').strip()
    if not value:
        return fallback

    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return fallback
    if not value.startswith('/'):
        return fallback

    return value


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated


def register_admin_routes(app, db):
    def _find_orphans():
        """Find all rows with FK references to non-existent parent rows."""
        orphans = []
        for table_name, schema in TABLES.items():
            for col_name in schema:
                if col_name in _FK_TO_PARENT:
                    parent_table = _FK_TO_PARENT[col_name]
                    rows = _rows_or_empty(db.go_get_all(table_name))
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

        # stat_table_to_stat links to custom_buff_to_stat_table via stat_table_id,
        # which is not a regular id-based FK in TABLES.
        stat_rows = _rows_or_empty(db.go_get_all('stat_table_to_stat'))
        for row in stat_rows:
            stat_table_id = row.get('stat_table_id')
            if not stat_table_id:
                continue
            parent = db.go_get_one('custom_buff_to_stat_table', {'stat_table_id': stat_table_id})
            if not parent:
                orphans.append({
                    'table': 'stat_table_to_stat',
                    'row': row,
                    'fk_col': 'stat_table_id',
                    'missing_parent': 'custom_buff_to_stat_table',
                    'missing_id': stat_table_id,
                })

        return orphans

    def _count_orphans():
        return len(_find_orphans())

    def _admin_table_columns(table_name):
        if table_name not in TABLES:
            return []
        return list(TABLES[table_name].keys())

    def _admin_fk_links(table_name):
        """Return dict of column -> URL prefix for FK links."""
        links = {}
        schema = TABLES.get(table_name, {})
        if 'character_id' in schema:
            links['character_id'] = '/admin/character/'
        if 'user_id' in schema:
            links['user_id'] = '/admin/user/'
        return links

    def _render_admin(**kwargs):
        try:
            user_theme = UserTheme.get_by_user_id(db, current_user.id)
        except Exception:
            app.logger.exception('Could not load user theme for admin page')
            user_theme = None
        return render_template('admin.html', user_theme=user_theme, **kwargs)

    @app.route('/admin')
    @admin_required
    def admin_home():
        users = _rows_or_empty(db.go_get_all('user'))
        for user in users:
            links = _rows_or_empty(db.go_get_all('user_to_character', {'user_id': user['id']}))
            user['character_count'] = len(links)

        orphan_count = _count_orphans()

        return _render_admin(
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
        for orphan in orphans:
            grouped.setdefault(orphan['table'], []).append(orphan)
        return _render_admin(
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

        links = _rows_or_empty(db.go_get_all('user_to_character', {'user_id': user_id}))
        characters = []
        for link in links:
            char = db.go_get_one('character', {'id': link['character_id']})
            if char:
                characters.append(char)

        return _render_admin(
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
            rows = _rows_or_empty(db.go_get_all(table_name, {fk_col: character_id}))
            child_links.append({
                'label': table_name.replace('_', ' ').title(),
                'url': f'/admin/table/{table_name}?filter_col={fk_col}&filter_val={character_id}',
                'count': len(rows),
            })

        # Ability skills are linked via ability_id FK, not character_id.
        for ability in _ABILITY_TABLES:
            skill_table = _SKILL_TABLE_MAP[ability]
            ability_row = db.go_get_one(ability, {'character_id': character_id})
            if ability_row:
                fk_col = f'{ability}_id'
                skill_rows = _rows_or_empty(db.go_get_all(skill_table, {fk_col: ability_row['id']}))
                child_links.append({
                    'label': skill_table.replace('_', ' ').title(),
                    'url': f'/admin/table/{skill_table}?filter_col={fk_col}&filter_val={ability_row["id"]}',
                    'count': len(skill_rows),
                })

        trackers = _rows_or_empty(db.go_get_all('tracker', {'character_id': character_id}))
        for tracker in trackers:
            entries = _rows_or_empty(db.go_get_all('tracker_entry', {'tracker_id': tracker['id']}))
            child_links.append({
                'label': f'Tracker Entries ({tracker["name"] or tracker["id"][:8]})',
                'url': f'/admin/table/tracker_entry?filter_col=tracker_id&filter_val={tracker["id"]}',
                'count': len(entries),
            })

        link = db.go_get_one('user_to_character', {'character_id': character_id})
        user = db.go_get_one('user', {'id': link['user_id']}) if link else None

        breadcrumbs = [{'label': 'Admin', 'url': '/admin'}]
        if user:
            breadcrumbs.append({'label': user['username'], 'url': f'/admin/user/{user["id"]}'})
        breadcrumbs.append({'label': character.get('name') or '(unnamed)', 'url': f'/admin/character/{character_id}'})

        return _render_admin(
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
            rows = _rows_or_empty(db.go_get_all(table_name, {filter_col: filter_val}))
        else:
            rows = _rows_or_empty(db.go_get_all(table_name))
            filter_col = None
            filter_val = None

        columns = _admin_table_columns(table_name)
        fk_links = _admin_fk_links(table_name)

        # Enrich rows with display names for FK columns.
        schema = TABLES.get(table_name, {})
        for row in rows:
            display = {}
            if 'character_id' in schema and row.get('character_id'):
                char = db.go_get_one('character', {'id': row['character_id']})
                if char:
                    display['character_id'] = char.get('name') or '(unnamed)'
            if 'user_id' in schema and row.get('user_id'):
                user = db.go_get_one('user', {'id': row['user_id']})
                if user:
                    display['user_id'] = user.get('username') or '(unknown)'
            if 'class_id' in schema and row.get('class_id'):
                cls = db.go_get_one('class', {'id': row['class_id']})
                if cls:
                    display['class_id'] = cls.get('name') or '(unknown)'
            if 'tracker_id' in schema and row.get('tracker_id'):
                tracker = db.go_get_one('tracker', {'id': row['tracker_id']})
                if tracker:
                    display['tracker_id'] = tracker.get('name') or '(unknown)'
            if 'custom_buff_id' in schema and row.get('custom_buff_id'):
                buff = db.go_get_one('custom_buff', {'id': row['custom_buff_id']})
                if buff:
                    display['custom_buff_id'] = buff.get('name') or '(unknown)'

            for ability in _ABILITY_TABLES:
                fk_col_name = f'{ability}_id'
                if fk_col_name in schema and row.get(fk_col_name):
                    ability_row = db.go_get_one(ability, {'id': row[fk_col_name]})
                    if ability_row and ability_row.get('character_id'):
                        char = db.go_get_one('character', {'id': ability_row['character_id']})
                        if char:
                            display[fk_col_name] = f'{ability.title()} -> {char.get("name") or "(unnamed)"}'
            row['_display'] = display

        # Build breadcrumbs and trace back to character/user when filtered.
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
            parent_table = filter_col.replace('_id', '')
            if parent_table in _ABILITY_TABLES:
                ability_row = db.go_get_one(parent_table, {'id': filter_val})
                if ability_row and ability_row.get('character_id'):
                    character_id = ability_row['character_id']
                    char = db.go_get_one('character', {'id': character_id})
                    link = db.go_get_one('user_to_character', {'character_id': character_id})
                    user = db.go_get_one('user', {'id': link['user_id']}) if link else None
                    if user:
                        breadcrumbs.append({'label': user['username'], 'url': f'/admin/user/{user["id"]}'})
                    if char:
                        breadcrumbs.append({'label': char.get('name') or '(unnamed)', 'url': f'/admin/character/{character_id}'})
        breadcrumbs.append({'label': table_name.replace('_', ' ').title(), 'url': current_url})

        return _render_admin(
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

        redirect_url = _normalise_internal_redirect(
            request.form.get('redirect', ''),
            f'/admin/table/{table_name}',
        )
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

        redirect_url = _normalise_internal_redirect(
            request.form.get('redirect', ''),
            f'/admin/table/{table_name}',
        )
        return redirect(redirect_url)

    @app.route('/admin/table/<table_name>/<row_id>/delete', methods=['POST'])
    @admin_required
    def admin_table_delete(table_name, row_id):
        if table_name not in TABLES:
            abort(404)
        if not is_valid_uuid(row_id):
            abort(400)

        # Cascade delete for user: remove all their characters and links.
        if table_name == 'user':
            links = _rows_or_empty(db.go_get_all('user_to_character', {'user_id': row_id}))
            for link in links:
                character_id = link['character_id']
                for child_table, fk_col in _CHILD_TABLES_BY_CHARACTER:
                    child_rows = _rows_or_empty(db.go_get_all(child_table, {fk_col: character_id}))
                    for child_row in child_rows:
                        if child_table in _ABILITY_TABLES:
                            skill_table = _SKILL_TABLE_MAP[child_table]
                            fk = f'{child_table}_id'
                            skill_rows = _rows_or_empty(db.go_get_all(skill_table, {fk: child_row['id']}))
                            for skill_row in skill_rows:
                                db.go_delete_it(skill_table, {'id': skill_row['id']})
                        if child_table == 'tracker':
                            entries = _rows_or_empty(db.go_get_all('tracker_entry', {'tracker_id': child_row['id']}))
                            for entry in entries:
                                db.go_delete_it('tracker_entry', {'id': entry['id']})
                        db.go_delete_it(child_table, {'id': child_row['id']})
                db.go_delete_it('character', {'id': character_id})
            db.go_delete_by('user_to_character', {'user_id': row_id})

        # Cascade delete for character: remove all child data.
        if table_name == 'character':
            for child_table, fk_col in _CHILD_TABLES_BY_CHARACTER:
                child_rows = _rows_or_empty(db.go_get_all(child_table, {fk_col: row_id}))
                for child_row in child_rows:
                    if child_table in _ABILITY_TABLES:
                        skill_table = _SKILL_TABLE_MAP[child_table]
                        fk = f'{child_table}_id'
                        skill_rows = _rows_or_empty(db.go_get_all(skill_table, {fk: child_row['id']}))
                        for skill_row in skill_rows:
                            db.go_delete_it(skill_table, {'id': skill_row['id']})
                    if child_table == 'tracker':
                        entries = _rows_or_empty(db.go_get_all('tracker_entry', {'tracker_id': child_row['id']}))
                        for entry in entries:
                            db.go_delete_it('tracker_entry', {'id': entry['id']})
                    db.go_delete_it(child_table, {'id': child_row['id']})
            db.go_delete_by('user_to_character', {'character_id': row_id})

        # Cascade delete for tracker: remove tracker entries.
        if table_name == 'tracker':
            entries = _rows_or_empty(db.go_get_all('tracker_entry', {'tracker_id': row_id}))
            for entry in entries:
                db.go_delete_it('tracker_entry', {'id': entry['id']})

        # Cascade delete for custom_buff: remove buff-to-stat-table links.
        if table_name == 'custom_buff':
            links = _rows_or_empty(db.go_get_all('custom_buff_to_stat_table', {'custom_buff_id': row_id}))
            for link in links:
                stat_table_id = link.get('stat_table_id')
                if stat_table_id:
                    stat_rows = _rows_or_empty(db.go_get_all('stat_table_to_stat', {'stat_table_id': stat_table_id}))
                    for stat_row in stat_rows:
                        db.go_delete_it('stat_table_to_stat', {'id': stat_row['id']})
                db.go_delete_it('custom_buff_to_stat_table', {'id': link['id']})

        # Cascade delete for custom_buff_to_stat_table: remove linked stat rows.
        if table_name == 'custom_buff_to_stat_table':
            link = db.go_get_one('custom_buff_to_stat_table', {'id': row_id})
            if link and link.get('stat_table_id'):
                stat_rows = _rows_or_empty(db.go_get_all('stat_table_to_stat', {'stat_table_id': link['stat_table_id']}))
                for stat_row in stat_rows:
                    db.go_delete_it('stat_table_to_stat', {'id': stat_row['id']})

        # Cascade delete for ability tables: remove skill rows.
        if table_name in _ABILITY_TABLES:
            skill_table = _SKILL_TABLE_MAP[table_name]
            fk = f'{table_name}_id'
            skill_rows = _rows_or_empty(db.go_get_all(skill_table, {fk: row_id}))
            for skill_row in skill_rows:
                db.go_delete_it(skill_table, {'id': skill_row['id']})

        db.go_delete_it(table_name, {'id': row_id})
        redirect_url = _normalise_internal_redirect(
            request.form.get('redirect', ''),
            f'/admin/table/{table_name}',
        )
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
