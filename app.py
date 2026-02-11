from flask import Flask, redirect, render_template, request, url_for
from character_sheet.character_sheet import CharacterSheet
from go_get_it.go_get_it import Database
from misc.config import DEBUG, secret_key # type: ignore

app = Flask(__name__)
app.secret_key = secret_key

db = Database()
debug = None

@app.route('/', methods=['GET', 'POST'])
def character_sheet():
    character_id = request.args.get('character_id') or "01964ee7cdcc1641bd25fe601c157a58" # debug purposes
    debug = f"{character_id}"

    character_sheet = CharacterSheet(character_id=character_id)
    character_sheet_data = character_sheet.create_form()

    class_to_chararcter = db.go_get_all('class_to_character', {'character_id': character_id}) or []

    character_classes = []
    for char_class in class_to_chararcter:
        dnd_class = db.go_get_one('class', {'id': char_class['class_id']})
        if dnd_class:
            character_classes.append({
                'id': char_class['id'],
                'name': dnd_class['name'],
                'level': char_class['level']
            })

    # inventory = db.go_get_all('inventory', {'character_id': character_id})
    # feats_and_traits = db.go_get_all('feat_and_trait', {'character_id': character_id})

    if request.method == 'POST':
        character_id = character_sheet.process_form(request.form)
        return redirect(url_for('character_sheet', character_id=character_id))

    return render_template(
        'index.html',
        character_id=character_id,
        character=character_sheet_data['character'],
        classes=character_sheet_data['classes'],
        class_options=character_sheet_data['class_options'],
        # abilities=character_sheet_data['abilities'],
        # feats_and_traits=character_sheet_data['feats_and_traits'],
        # inventory=inventory,
        debug=debug
        )

@app.route("/<character_id>/inventory/<inventory_id>/remove")
def remove_inventory_item(character_id: str, inventory_id: str):
    if not character_id or not inventory_id or not db.go_get_one('inventory', {'id': inventory_id, "character_id": character_id}):
        # How'd you get it here, turn around!
        return redirect(url_for('character_sheet'))

    db.go_delete_it('inventory', {'id': inventory_id, "character_id": character_id})
    return redirect(url_for('character_sheet', character_id=character_id))


@app.route("/<character_id>/feat-and-trait/<feat_and_trait_id>/remove")
def remove_feat_and_trait_item(character_id: str, feat_and_trait_id: str):
    if not character_id or not feat_and_trait_id or not db.go_get_one('feat_and_trait', {'id': feat_and_trait_id, "character_id": character_id}):
        # How'd you get it here, turn around!
        return redirect(url_for('character_sheet'))

    db.go_delete_it('feat_and_trait', {'id': feat_and_trait_id, "character_id": character_id})
    return redirect(url_for('character_sheet', character_id=character_id))


@app.route("/<character_id>/class/<class_id>/remove")
def remove_class(character_id: str, class_id: str):
    if not character_id or not class_id or not db.go_get_one('class_to_character', {'id': class_id, "character_id": character_id}):
        # How'd you get it here, turn around!
        return redirect(url_for('character_sheet'))

    db.go_delete_it('class_to_character', {'id': class_id, "character_id": character_id})
    return redirect(url_for('character_sheet', character_id=character_id))


if __name__ == '__main__':
    # Create the database
    db.go_create_db()
    # Seed the database
    db.go_seed_db()
    # Run the Flask app on port 8888
    app.run(host='0.0.0.0', port=8888, debug=DEBUG)
