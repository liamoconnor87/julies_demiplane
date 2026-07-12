from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet
from demiplane.routes.helpers import build_character_sheet_data


def register_inventory_fragment_routes(app, db, limiter):
    @app.route('/characters/<character_id>/inventory/fragment', methods=['POST'])
    @login_required
    def inventory_fragment(character_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        sheet.save_inventory_values(character_id, request.form)

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/inventory/inventory_change_response.html',
            inventory=data['inventory'],
            inventory_at_capacity=data['inventory_at_capacity'],
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            character_id=character_id,
        )

    @app.route('/characters/<character_id>/inventory/<inventory_id>/remove', methods=['POST'])
    @login_required
    def remove_inventory_item(character_id: str, inventory_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        if not character_id or not inventory_id or not db.go_get_one('inventory', {'id': inventory_id, 'character_id': character_id}):
            return redirect(url_for('character_sheet'))

        db.go_delete_it('inventory', {'id': inventory_id, 'character_id': character_id})

        _, data = build_character_sheet_data(character_id)
        return render_template(
            'components/inventory/inventory_change_response.html',
            inventory=data['inventory'],
            inventory_at_capacity=data['inventory_at_capacity'],
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
            character_id=character_id,
        )

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

        _, data = build_character_sheet_data(character_id)
        rendered_item = next((entry for entry in data['inventory'] if entry.get('id') == inventory_id), item)
        return render_template(
            'components/inventory/inventory_row_change_response.html',
            item=rendered_item,
            character_id=character_id,
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
        )

    @app.route('/characters/<character_id>/inventory/<inventory_id>/step', methods=['POST'])
    @login_required
    def step_inventory_item(character_id: str, inventory_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)

        try:
            step = int(request.form.get('inventory-step', '0'))
        except (TypeError, ValueError):
            step = 0

        # Clamp step size defensively.
        step = max(-100, min(100, step))
        if step == 0:
            abort(400)

        sheet = CharacterSheet(character_id=character_id)
        item = sheet.step_single_inventory_item(character_id, inventory_id, step)

        if item is None:
            return ('', 200, {
                'HX-Retarget': f'#inventory-row-{inventory_id}',
                'HX-Reswap': 'outerHTML',
            })

        _, data = build_character_sheet_data(character_id)
        rendered_item = next((entry for entry in data['inventory'] if entry.get('id') == inventory_id), item)

        return render_template(
            'components/inventory/inventory_quantity_response.html',
            item=rendered_item,
            character_id=character_id,
        )

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

        _, data = build_character_sheet_data(character_id)
        rendered_item = next((entry for entry in data['inventory'] if entry.get('id') == item.get('id')), item)
        return render_template(
            'components/inventory/inventory_row_change_response.html',
            item=rendered_item,
            character_id=character_id,
            custom_buffs=data['custom_buffs'],
            custom_buffs_at_capacity=data['custom_buffs_at_capacity'],
            buff_target_options=data['buff_target_options'],
        )
