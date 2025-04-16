from flask import Flask, redirect, render_template, request, url_for
import datetime
from character_sheet.character_sheet import CharacterSheet
from go_get_it.go_get_it import Database
from misc.config import DEBUG, secret_key # type: ignore

app = Flask(__name__)
app.secret_key = secret_key

db = Database()
debug = None

@app.route('/', methods=['GET', 'POST'])
def character_sheet():
    character_id = request.args.get('character_id') or "01963ec9fbe3169914dc3927442c28bc" # debug purposes
    debug = f"{character_id} - {db.go_get_all('character', count=True)} - {datetime.datetime.now()}"

    character_sheet = CharacterSheet(character_id=character_id)
    character_sheet_form = character_sheet.create_form()

    inventory = db.go_get_all('inventory', {'character_id': character_id})

    if request.method == 'POST':
        character_id = character_sheet.process_form(request.form)
        return redirect(url_for('character_sheet', character_id=character_id))

    return render_template(
        'index.html',
        character_id=character_id,
        character_sheet_form=character_sheet_form,
        debug=debug,
        inventory=inventory,
        )

@app.route("/<character_id>/<inventory_id>/remove")
def remove_inventory_item(character_id: str, inventory_id: str):
    if not character_id or not inventory_id or not db.go_get_one('inventory', {'id': inventory_id, "character_id": character_id}):
        # How'd you get it here, turn around!
        return redirect(url_for('character_sheet'))

    db.go_delete_it('inventory', {'id': inventory_id, "character_id": character_id})
    return redirect(url_for('character_sheet', character_id=character_id))


if __name__ == '__main__':
    db.create_db()
    # Seed the database
    db.go_seed_db()
    # Run the Flask app on port 8888
    app.run(host='0.0.0.0', port=8888, debug=DEBUG)
