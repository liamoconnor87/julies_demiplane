from flask import abort, render_template, request
from flask_login import current_user, login_required

from demiplane.auth.models import User
from demiplane.services.character_sheet import TRACKER_MAX, TRACKER_ENTRY_MAX
from demiplane.functions.functions import uuid as generate_uuid

from ._shared import _rows_or_empty, _count_or_zero


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


def register_tracker_fragment_routes(app, db, limiter):
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
            'components/tracker/tracker_page.html',
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
            'components/tracker/tracker_item.html',
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
