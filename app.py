from flask import Flask, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFProtect
from character_sheet.character_sheet import CharacterSheet
from character_sheet.custom_buff import BuffProcessor
from go_get_it.go_get_it import GoGetDB
from misc.config import DEBUG, secret_key # type: ignore

app = Flask(__name__)
app.secret_key = secret_key
CSRFProtect(app)

db = GoGetDB()

def _build_character_sheet_data(character_id: str):
    sheet = CharacterSheet(character_id=character_id)
    data = sheet.create_form()
    BuffProcessor(character_id).transform_out(data)
    return sheet, data

@app.route('/', methods=['GET'])
def character_sheet():
    character_id = request.args.get('character_id') or "01964ee7cdcc1641bd25fe601c157a58" # debug purposes
    debug = character_id

    _, character_sheet_data = _build_character_sheet_data(character_id)

    return render_template(
        'index.html',
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
        debug=debug
    )

@app.route('/characters/<character_id>/character-info/fragment', methods=['POST'])
def character_info_fragment(character_id: str):
    sheet = CharacterSheet(character_id=character_id)
    request_form = BuffProcessor(character_id).transform_in(request.form)
    sheet.save_character_values(request_form)

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/character_info_change_response.html',
        character_id=character_id,
        character=data['character'],
        abilities=data['abilities'],
    )

@app.route('/characters/<character_id>/classes/fragment', methods=['POST'])
def classes_fragment(character_id: str):
    sheet = CharacterSheet(character_id=character_id)
    sheet.save_class_to_character_values(character_id, request.form)

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/classes_fragment_response.html',
        character_id=character_id,
        classes=data['classes'],
        class_options=data['class_options'],
        character=data['character']
    )

@app.route('/characters/<character_id>/feats-traits/fragment', methods=['POST'])
def feats_traits_fragment(character_id: str):
    sheet = CharacterSheet(character_id=character_id)
    sheet.save_feat_and_trait_values(character_id, request.form)

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/feats_traits_section.html',
        character_id=character_id,
        feats_and_traits=data['feats_and_traits'],
        feats_and_traits_at_capacity=data['feats_and_traits_at_capacity']
    )

@app.route('/characters/<character_id>/abilities-skills/fragment', methods=['POST'])
def abilities_skills_fragment(character_id: str):
    sheet = CharacterSheet(character_id=character_id)
    transformed_form = BuffProcessor(character_id).transform_in(request.form)
    sheet.save_ability_values(character_id, transformed_form)

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/abilities_section.html',
        abilities=data['abilities'],
        character_id=character_id
    )

@app.route('/characters/<character_id>/inventory/fragment', methods=['POST'])
def inventory_fragment(character_id: str):
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
def custom_stats_fragment(character_id: str):
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
        character_id=character_id
    )


@app.route('/characters/<character_id>/custom-buffs/fragment', methods=['POST'])
def custom_buffs_fragment(character_id: str):
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
    )

@app.route('/characters/<character_id>/inventory/<inventory_id>/remove', methods=['POST'])
def remove_inventory_item(character_id: str, inventory_id: str):
    if not character_id or not inventory_id or not db.go_get_one('inventory', {'id': inventory_id, 'character_id': character_id}):
        return redirect(url_for('character_sheet'))

    db.go_delete_it('inventory', {'id': inventory_id, 'character_id': character_id})

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/inventory_section.html',
        inventory=data['inventory'],
        inventory_at_capacity=data['inventory_at_capacity'],
        character_id=character_id
    )


@app.route('/characters/<character_id>/feat-and-trait/<feat_and_trait_id>/remove', methods=['POST'])
def remove_feat_and_trait_item(character_id: str, feat_and_trait_id: str):
    if not character_id or not feat_and_trait_id or not db.go_get_one('feat_and_trait', {'id': feat_and_trait_id, 'character_id': character_id}):
        return redirect(url_for('character_sheet'))

    db.go_delete_it('feat_and_trait', {'id': feat_and_trait_id, 'character_id': character_id})

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/feats_traits_section.html',
        character_id=character_id,
        feats_and_traits=data['feats_and_traits'],
        feats_and_traits_at_capacity=data['feats_and_traits_at_capacity']
    )


@app.route('/characters/<character_id>/custom-stat/<custom_stat_id>/remove', methods=['POST'])
def remove_custom_stat_item(character_id: str, custom_stat_id: str):
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
    )


@app.route('/characters/<character_id>/custom-buff/<custom_buff_id>/remove', methods=['POST'])
def remove_custom_buff_item(character_id: str, custom_buff_id: str):
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
    )


@app.route('/characters/<character_id>/class/<class_id>/remove', methods=['POST'])
def remove_class(character_id: str, class_id: str):
    if not character_id or not class_id or not db.go_get_one('class_to_character', {'id': class_id, 'character_id': character_id}):
        return redirect(url_for('character_sheet'))

    db.go_delete_it('class_to_character', {'id': class_id, 'character_id': character_id})

    _, data = _build_character_sheet_data(character_id)
    return render_template(
        'components/classes_fragment_response.html',
        character_id=character_id,
        classes=data['classes'],
        class_options=data['class_options'],
        character=data['character']
    )


if __name__ == '__main__':
    # Create the database
    db.go_create_db()
    # Seed the database
    db.go_seed_db()
    # Run the Flask app on port 8888
    app.run(host='0.0.0.0', port=8888, debug=DEBUG)
