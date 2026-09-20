# Spells Tab — Design Spec

**Goal:** add a fifth character sheet tab, Spells, where a player searches a seeded
spell list, adds spells to a free "Spells Known" list, marks a subset "Spells
Prepared", and sees an auto-managed Spell Slots tracker (and, for Warlocks, a
Pact Magic tracker) below both lists — all without the app enforcing any D&D
rules about what a character is *allowed* to know or prepare.

**Non-goals:** validating known/prepared limits against class rules, ritual
casting mechanics, spell attack/save DC calculation, subclass-granted casting
(Eldritch Knight, Arcane Trickster — the `class` table has no subclass field,
so there's nothing to key off). Guest (no-account) characters are out of
scope for this pass; only authenticated, DB-backed characters get the tab.

---

## 1. Spell data: source, license, scope

Source: [5etools-mirror-3/5etools-src](https://github.com/5etools-mirror-3/5etools-src),
`data/spells/spells-xphb.json` (the 2024 Player's Handbook spell list, the
edition this group plays). One JSON object per spell: `name`, `level`
(0 = cantrip), `school`, `time` (casting time), `range`, `components`,
`duration`, `entries` (description, as an array of strings with `{@tag ...}`
inline markup — see §3).

**Licensing note, because the site is public:** the repo's MIT license badge
covers 5etools' own code, not the spell text, which is Wizards of the
Coast's. The repo lives under a "mirror" account because the original got a
DMCA takedown in 2023. Seeding straight from `spells-xphb.json` carries that
same risk on a public site. The safer alternative is WotC's own SRD 5.2
(Creative Commons) or [vorpalhex/srd_spells](https://github.com/vorpalhex/srd_spells)
(MIT, SRD-only). **Decision needed before the seed script runs against
production data — flagged here, not resolved by this spec.** Everything
below is written against the 5etools JSON shape; swapping the source later
only changes the seed script's input file and field mapping, not the schema.

Only the core XPHB list is seeded now. Other official sourcebooks (Xanathar's,
Tasha's, Explorer's Guide to Wildemount, etc. — see the `source` column
below) are a follow-on: point the same seed script at another file.

---

## 2. Data model

Two new tables in `db/tables.py`, following the existing `class` /
`class_to_character` shared-reference-plus-join-table pattern:

```python
"spell": {
    "id": _id,
    "name": _text(),
    "level": _integer,        # 0 = cantrip, 1-9 = spell level
    "school": _text(50),
    "casting_time": _text(),
    "range": _text(),
    "components": _text(),
    "duration": _text(),
    "description": _mediumtext,
    "source": _text(10),      # "XPHB" today; other sourcebook codes later
},
"spell_to_character": {
    "id": _id,
    "character_id": _fk,
    "spell_id": _fk,
    "prepared": _boolean,     # Spells Known = every row; Spells Prepared = prepared=1
},
```

One row per known spell; "prepared" is a flag on that row, not a second
table. Un-preparing flips the flag. Removing from Known deletes the row,
which drops it from Prepared too — there's no way for the two lists to
disagree.

A third change, to the existing `tracker` table, supports §5:

```python
"tracker": {
    "id": _id,
    "character_id": _fk,
    "name": _text(),
    "auto_generated": _boolean,   # NEW — marks trackers this feature owns
},
```

`auto_generated` is new: nothing in the codebase sets it today (the
`tracker.fixed` flag already read by `templates/components/tracker/tracker_item.html`
to lock the name/delete/add-entry controls is currently dead — no service
ever sets it). This feature is the first to populate it, and the template's
existing `{% if not tracker.fixed %}` guards are reused by passing
`tracker.fixed = tracker.auto_generated` when rendering: an auto-generated
tracker can't be renamed or deleted by hand, but its pips still toggle
normally, exactly like every other tracker.

---

## 3. Seed script

`admin/seed_spells.py`, matching the shape of the existing `admin/postgres_to_sqlite.py`:

1. Reads a vendored copy of the source JSON (`admin/data/spells-xphb.json` —
   downloaded once and checked in, not fetched at runtime).
2. Maps each spell's fields to the `spell` table columns.
3. Strips 5etools' `{@tag text|display|extra}` markup out of `entries` down
   to plain text for v1 (render `display` if present, else `text`; drop
   everything else). No parsing into links/formatting — that's a later
   upgrade if the plain-text version reads badly. Multiple `entries` strings
   join with blank lines into one `description`.
4. Inserts with `db.go_add_new("spell", {...})`, skipping any row whose
   `name` already exists (idempotent re-runs).
5. Run once locally against SQLite, then once against prod with
   `DATABASE_URL=... python admin/seed_spells.py`, same two-environment
   pattern the existing backup scripts use.

---

## 4. Backend: known/prepared lists

New service, `demiplane/services/character_sheet/spells.py`, alongside the
existing `feats.py`/`inventory.py` in that package:

- `search_spells(query: str) -> list[dict]` — `LIKE`-search the shared
  `spell` table by name, for the left-hand search panel.
- `fetch_spells_data(character_id: str) -> dict` — returns `known` (every
  `spell_to_character` row for this character, joined to `spell`) and
  `prepared` (the subset where `prepared=1`).
- `add_spell_to_character(character_id, spell_id) -> dict` — inserts a
  `spell_to_character` row (`prepared=0`), no-ops if it already exists.
- `set_spell_prepared(character_id, spell_to_character_id, prepared: bool) -> dict`
- `remove_spell_from_character(character_id, spell_to_character_id) -> None`

New routes, `demiplane/routes/fragments/spells.py`, registered in
`demiplane/routes/fragments/__init__.py` next to the other fragment
registrations:

- `POST /characters/<character_id>/spells/search` — HTMX live-search
  (keyup, debounced client-side same as any other HTMX search), returns a
  fragment of matching spell cards for the left panel.
- `POST /characters/<character_id>/spell/add` — adds to Known, returns the
  updated Known-list fragment.
- `POST /characters/<character_id>/spell/<spell_to_character_id>/prepare` —
  toggles `prepared`, returns updated Known + Prepared fragments.
- `POST /characters/<character_id>/spell/<spell_to_character_id>/remove` —
  deletes the row, returns updated Known + Prepared fragments.

Every route follows the existing `User.owns_character` ownership check
already used in `feats.py`; no guest-mode branch (see Non-goals).

---

## 5. Backend: auto-generated slot trackers

**Caster tables.** All full casters and half casters share one progression
table, indexed by *effective caster level*:

| Effective level | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th | 9th |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | | | | | | | | |
| 2 | 3 | | | | | | | | |
| 3 | 4 | 2 | | | | | | | |
| 4 | 4 | 3 | | | | | | | |
| 5 | 4 | 3 | 2 | | | | | | |
| 6 | 4 | 3 | 3 | | | | | | |
| 7 | 4 | 3 | 3 | 1 | | | | | |
| 8 | 4 | 3 | 3 | 2 | | | | | |
| 9 | 4 | 3 | 3 | 3 | 1 | | | | |
| 10 | 4 | 3 | 3 | 3 | 2 | | | | |
| 11 | 4 | 3 | 3 | 3 | 2 | 1 | | | |
| 12 | 4 | 3 | 3 | 3 | 2 | 1 | | | |
| 13 | 4 | 3 | 3 | 3 | 2 | 1 | 1 | | |
| 14 | 4 | 3 | 3 | 3 | 2 | 1 | 1 | | |
| 15 | 4 | 3 | 3 | 3 | 2 | 1 | 1 | 1 | |
| 16 | 4 | 3 | 3 | 3 | 2 | 1 | 1 | 1 | |
| 17 | 4 | 3 | 3 | 3 | 2 | 1 | 1 | 1 | 1 |
| 18 | 4 | 3 | 3 | 3 | 3 | 1 | 1 | 1 | 1 |
| 19 | 4 | 3 | 3 | 3 | 3 | 2 | 1 | 1 | 1 |
| 20 | 4 | 3 | 3 | 3 | 3 | 2 | 2 | 1 | 1 |

Effective level = sum of full-caster class levels + (sum of half-caster
class levels ÷ 2, rounded down). Half-casters: Paladin, Ranger (round down),
Artificer (round up — the one exception). Full casters: Bard, Cleric,
Druid, Sorcerer, Wizard. This is the same table a single-class Wizard uses
(effective level = character level) and the same one a multiclass
Wizard/Paladin uses (effective level = Wizard levels + Paladin levels ÷ 2) —
one table, one formula, no special-casing single-class.

**Pact Magic (Warlock), entirely separate:**

| Warlock level | Slots | Slot level |
|---|---|---|
| 1 | 1 | 1st |
| 2 | 2 | 1st |
| 3–4 | 2 | 2nd |
| 5–6 | 2 | 3rd |
| 7–8 | 2 | 4th |
| 9–10 | 2 | 5th |
| 11–16 | 3 | 5th |
| 17–20 | 4 | 5th |

Warlock levels never feed into the full/half table above, and vice versa —
a Wizard/Warlock multiclass character gets both trackers independently.

Both tables are game mechanics (numbers), not the copyrighted flavour text
§1 flags — safe to hardcode as a plain Python constant regardless of which
spell-text source gets used.

**Sync function.** `demiplane/services/character_sheet/spell_slots.py`,
called from the existing class/level save path (wherever
`class_to_character` rows get written today — the same save that currently
updates the hit-die display) via `sync_spell_slot_trackers(character_id)`:

1. Read the character's `class_to_character` rows, compute effective caster
   level and Warlock level.
2. For each of the two possible trackers ("Spell Slots", "Pact Magic
   Slots"): if the relevant level is 0, delete the tracker if it exists
   (`auto_generated=1` guard, so a same-named manual tracker is never
   touched); otherwise look up the expected `{entry_name: count}` map
   (e.g. `{"1st Level": 4, "2nd Level": 3}`) and diff it against existing
   `tracker_entry` rows by name: update `value` where the count changed,
   insert new entries, delete entries no longer in the map. Never delete
   and recreate an unchanged entry — that's what keeps whatever marks a pip
   "used" today intact across a level-up.
3. Create the tracker itself (`auto_generated=1`) only the first time it's
   needed.

**Open verification item for implementation, not a design ambiguity:** how
"used" pip state is actually persisted (`templates/components/tracker/tracker_item.html`'s
`.tracker-toggle` spans render `aria-checked="false"` unconditionally in the
template with no server-side value visible in the row I read) should be
confirmed against `bindTrackerToggles()` in `dnd_sheet.js` before writing
the diff step above, so step 2 preserves whatever that mechanism actually
is.

---

## 6. Frontend

New `templates/components/spells/` folder, mirroring `components/feats/`:
- `spells_search_results.html` — card list for the left panel (name, level,
  school; click expands the same way a feat card does)
- `spells_known_section.html` / `spell_known_row.html` — middle list, each
  row with a "Prepare" button
- `spells_prepared_section.html` / `spell_prepared_row.html` — right list,
  each row with an "Unprepare" button
- Trackers are not re-implemented here — the Spells page includes the
  existing `components/tracker/tracker_section.html` partial below the
  three lists, unfiltered (same section as the Trackers tab renders, shown
  a second time).

**Tab wiring**, both required for the tab to appear at all:
- `templates/components/ui/sub_bar.html`: add a fifth
  `<button class="sub-bar-tab" data-tab="spells">Spells</button>` (and the
  matching `<option>` in the mobile `<select>`).
- `static/scripts/dnd_sheet.js`, `bindSubBarTabs()`: add `'spells':
  document.getElementById('sheet-page-spells')` to the `pages` map, add
  `'spells'` to `validTabs`, add a `switchTo` branch that binds the search
  input and any new autosave/toggle handlers the same way the `'feats'` and
  `'inventory'` branches do today.

---

## 7. Testing

This repo has no automated test suite for the Flask app (per the existing
`docs/superpowers/plans/2026-09-13-...` precedent) — manual browser
verification is the norm here, and that's the plan for the search/add/
prepare/remove flow and the tab wiring.

The one piece worth a written check is the slot-table math in §5, because
it's easy to get subtly wrong (off-by-one in the level table, half-caster
rounding direction, Warlock levels leaking into the full/half formula) and
a wrong result wouldn't be visually obvious. One small `assert`-based
self-check in `demiplane/services/character_sheet/spell_slots.py`
(`if __name__ == '__main__':`, no pytest, matching this repo's existing
`admin/test_postgres_to_sqlite.py` as the one precedent for a written test)
covering: a single-class Wizard at a few levels, a Paladin/Ranger rounding
case, a Wizard/Paladin multiclass, a Warlock, and a non-caster (no trackers
created).

---

## Future idea: level-scaled stats (not v1)

The source JSON carries structured scaling data that the seed script currently
flattens into plain prose and discards structurally: `scalingLevelDice` (cantrip
damage by character level, e.g. Acid Splash's `{"1": "1d6", "5": "2d6", "11":
"3d6", "17": "4d6"}`) and `{@scaledamage}` tags in `entriesHigherLevel` (upcast
damage per slot level above the spell's base level). Right now both just read
as static prose in `description` ("The damage increases by 1d6 when you reach
levels 5...").

Later, this could be surfaced as an actual computed value against the
character's effective caster level (or plain character level for cantrips,
which scale off total character level, not caster level) -- the same
effective-level concept §5 already defines for spell slots. Would need its own
columns on `spell` (the raw scaling map isn't in the current schema) and isn't
scoped or estimated yet -- flagging so it doesn't get lost, not committing to
it for this pass.

---

## Scope summary

| In v1 | Out of v1 |
|---|---|
| XPHB spell list, plain-text descriptions | Other sourcebooks, tag rendering/linking |
| Free known/prepared lists, no rules validation | Known/prepared limit enforcement, ritual/concentration mechanics |
| Auto full/half/pact slot trackers, multiclass-aware | Third-caster subclasses (Eldritch Knight, Arcane Trickster) |
| Authenticated characters | Guest (no-account) characters |
