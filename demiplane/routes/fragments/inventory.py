from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from demiplane.auth.models import User
from demiplane.services.character_sheet import CharacterSheet, INVENTORY_MAX, CUSTOM_BUFF_MAX


def register_inventory_fragment_routes(app, db, limiter):
    @app.route('/characters/<character_id>/inventory/fragment', methods=['POST'])
    @login_required
    def inventory_fragment(character_id: str):
        if not User.owns_character(db, current_user.id, character_id):
            abort(403)
        sheet = CharacterSheet(character_id=character_id)
        sheet.save_inventory_values(character_id, request.form)

        inventory = sheet.fetch_inventory_data()
        custom_buffs = sheet.fetch_custom_buffs_data()
        buff_target_options = sheet.fetch_buff_target_options_data(inventory=inventory)
        return render_template(
            'components/inventory/inventory_change_response.html',
            inventory=inventory,
            inventory_at_capacity=len(inventory) >= INVENTORY_MAX,
            custom_buffs=custom_buffs,
            custom_buffs_at_capacity=len(custom_buffs) >= CUSTOM_BUFF_MAX,
            buff_target_options=buff_target_options,
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

        sheet = CharacterSheet(character_id=character_id)
        inventory = sheet.fetch_inventory_data()
        custom_buffs = sheet.fetch_custom_buffs_data()
        buff_target_options = sheet.fetch_buff_target_options_data(inventory=inventory)
        return render_template(
            'components/inventory/inventory_change_response.html',
            inventory=inventory,
            inventory_at_capacity=len(inventory) >= INVENTORY_MAX,
            custom_buffs=custom_buffs,
            custom_buffs_at_capacity=len(custom_buffs) >= CUSTOM_BUFF_MAX,
            buff_target_options=buff_target_options,
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

        custom_buffs = sheet.fetch_custom_buffs_data()
        buff_target_options = sheet.fetch_buff_target_options_data()
        return render_template(
            'components/inventory/inventory_row_change_response.html',
            item=item,
            character_id=character_id,
            custom_buffs=custom_buffs,
            custom_buffs_at_capacity=len(custom_buffs) >= CUSTOM_BUFF_MAX,
            buff_target_options=buff_target_options,
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

        return render_template(
            'components/inventory/inventory_quantity_response.html',
            item=item,
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

        custom_buffs = sheet.fetch_custom_buffs_data()
        buff_target_options = sheet.fetch_buff_target_options_data()
        return render_template(
            'components/inventory/inventory_row_change_response.html',
            item=item,
            character_id=character_id,
            custom_buffs=custom_buffs,
            custom_buffs_at_capacity=len(custom_buffs) >= CUSTOM_BUFF_MAX,
            buff_target_options=buff_target_options,
        )
