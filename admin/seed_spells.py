"""
Seed the shared `spell` reference table from vendored 5etools data files.

Source: 5etools-mirror-3/5etools-src, data/spells/spells-<book>.json -- the
2024 Player's Handbook (spells-xphb.json) plus every other sourcebook the
mirror carries (Xanathar's, Tasha's, Explorer's Guide to Wildemount, and the
various adventure/setting books), excluding spells-phb.json, the 2014
edition -- a different ruleset already superseded by XPHB in this catalog,
so seeding both would duplicate names like "Fireball" under two incompatible
rules texts. That repo's MIT license covers its own code, not the spell text
itself, which is Wizards of the Coast's -- seeding this on a public site is
a known, accepted risk (see docs/superpowers/specs).

Per-spell class availability isn't in those files -- it lives in the same
repo's data/generated/gendata-spell-source-lookup.json, a 700KB+ lookup
across every sourcebook. admin/data/spell_classes.json is a precomputed
{spell name: [classes]} slice of just that file for all 581 spells here,
built once rather than vendoring the whole lookup.

Idempotent twice over: it skips any spell whose name already exists, and ids
are derived from the spell name rather than random (see spell_id), so even
wiping the table and reseeding gives every spell back the id it had before.
That keeps spell_to_character resolving -- a random-id reseed silently
orphaned 21 of Julie's spell picks on 18 Sep 2026.
XPHB is always processed first regardless of file order, so its own 2024
text wins if a later sourcebook reprints the same spell name.

Usage (from project root):
    python admin/seed_spells.py
    DATABASE_URL="postgresql://..." python admin/seed_spells.py
    python admin/seed_spells.py --input admin/data/spells-xge.json
"""

import argparse
import glob
import json
import os
import re
import sys
import uuid as uuid_lib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from go_get_it.go_get_it import GoGetDB

DEFAULT_INPUT_GLOB = 'admin/data/spells-*.json'
DEFAULT_CLASSES_INPUT = 'admin/data/spell_classes.json'

SCHOOL_NAMES = {
    'A': 'Abjuration',
    'C': 'Conjuration',
    'D': 'Divination',
    'E': 'Enchantment',
    'V': 'Evocation',
    'I': 'Illusion',
    'N': 'Necromancy',
    'T': 'Transmutation',
}

TIME_UNIT_LABELS = {
    'action': 'Action',
    'bonus': 'Bonus Action',
    'reaction': 'Reaction',
}

TAG_RE = re.compile(r'\{@(\w+)\s*([^}]*)\}')


def _tag_text(tag: str, content: str) -> str:
    """Resolve one {@tag ...} inline markup match to plain display text."""
    parts = content.split('|')
    if tag == 'variantrule' and len(parts) >= 3 and parts[2]:
        return parts[2]
    if tag == 'dc':
        return f'DC {parts[0]}'
    return parts[0]


def strip_tags(text: str) -> str:
    """Strip 5etools' {@tag text|source|display} inline markup down to plain text."""
    return TAG_RE.sub(lambda m: _tag_text(m.group(1), m.group(2)), text)


def flatten_entries(entries: list) -> str:
    """Flatten a spell's `entries` (strings plus nested list/table/entries blocks) to plain text."""
    paragraphs = []
    for entry in entries:
        if isinstance(entry, str):
            paragraphs.append(strip_tags(entry))
            continue

        entry_type = entry.get('type')
        if entry_type in ('entries', 'item'):
            name = entry.get('name')
            body = flatten_entries(entry.get('entries', []))
            paragraphs.append(f'{name}. {body}' if name else body)
        elif entry_type == 'list':
            lines = [f'- {flatten_entries([item])}' for item in entry.get('items', [])]
            paragraphs.append('\n'.join(lines))
        elif entry_type == 'table':
            lines = []
            if entry.get('caption'):
                lines.append(entry['caption'])
            if entry.get('colLabels'):
                lines.append(' | '.join(strip_tags(c) for c in entry['colLabels']))
            for row in entry.get('rows', []):
                lines.append(' | '.join(strip_tags(str(cell)) for cell in row))
            paragraphs.append('\n'.join(lines))

    return '\n\n'.join(p for p in paragraphs if p)


def build_description(spell: dict) -> str:
    body = flatten_entries(spell.get('entries', []))
    higher_level = flatten_entries(spell.get('entriesHigherLevel', []))
    if higher_level:
        return f'{body}\n\n{higher_level}' if body else higher_level
    return body


def format_time(spell: dict) -> str:
    time = spell['time'][0]
    unit = time.get('unit')
    number = time.get('number', 1)

    if unit in TIME_UNIT_LABELS:
        label = TIME_UNIT_LABELS[unit]
        if unit == 'reaction' and time.get('condition'):
            label += f", {time['condition']}"
    else:
        label = f"{number} {unit}" + ('s' if number != 1 else '')

    if spell.get('meta', {}).get('ritual'):
        label += ' or Ritual'
    return label


def format_range(spell: dict) -> str:
    range_data = spell['range']
    if range_data['type'] in ('cone', 'cube', 'sphere', 'line', 'emanation'):
        # The book prints "Self" for these -- the shape/size lives in the
        # description text, not the Range line (confirmed against the SRD).
        return 'Self'

    distance = range_data.get('distance', {})
    distance_type = distance.get('type')
    amount = distance.get('amount')

    if distance_type in ('self', 'touch', 'unlimited', 'sight'):
        return distance_type.capitalize()
    if distance_type == 'feet':
        return f'{amount} feet'
    if distance_type == 'miles':
        return f"{amount} mile" + ('s' if amount != 1 else '')
    return distance_type or ''


def format_components(spell: dict) -> str:
    components = spell.get('components', {})
    parts = []
    if components.get('v'):
        parts.append('V')
    if components.get('s'):
        parts.append('S')
    material = components.get('m')
    if material:
        text = material.get('text', '') if isinstance(material, dict) else material
        parts.append(f'M ({text})')
    return ', '.join(parts)


def format_duration(spell: dict) -> str:
    duration = spell['duration'][0]
    duration_type = duration.get('type')

    if duration_type == 'instant':
        return 'Instantaneous'
    if duration_type == 'special':
        return 'Special'
    if duration_type == 'permanent':
        return 'Until dispelled or triggered' if 'trigger' in duration.get('ends', []) else 'Until dispelled'

    timed = duration.get('duration', {})
    amount = timed.get('amount', 1)
    unit = timed.get('type', '')
    base = f"{amount} {unit}" + ('s' if amount != 1 else '')
    return f'Concentration, up to {base}' if duration.get('concentration') else base


# Fixed namespace for spell ids. Never change it: every id in every database
# is derived from it, so a new namespace would orphan every character's spells.
_SPELL_ID_NAMESPACE = uuid_lib.UUID('90a4f83a-a568-4eb4-9037-730a5434e385')


def spell_id(name: str) -> str:
    """Stable id for a spell, derived from its name.

    Deliberately not random. The seeder skips by name, so name is already the
    identity of a spell here, and deriving the id from it makes a reseed
    idempotent: wipe the table, run again, and every spell comes back with the
    id it had before, so spell_to_character keeps resolving.

    Random ids cost us this once already -- emptying the table on 18 Sep 2026
    and reseeding gave all 581 spells new ids and silently orphaned 21 of
    Julie's picks, with no error anywhere because spell_id has no FK.

    Args:
        name: the spell's name, exactly as it appears in the source data.

    Returns:
        32 lowercase hex characters, matching the TEXT(32) id column.
    """
    return uuid_lib.uuid5(_SPELL_ID_NAMESPACE, name).hex


def map_spell(spell: dict, classes_by_name: dict) -> dict:
    return {
        'id': spell_id(spell['name']),
        'name': spell['name'],
        'level': spell['level'],
        'school': SCHOOL_NAMES.get(spell.get('school'), spell.get('school', '')),
        'casting_time': format_time(spell),
        'range': format_range(spell),
        'components': format_components(spell),
        'duration': format_duration(spell),
        'description': build_description(spell),
        'classes': ', '.join(classes_by_name.get(spell['name'], [])),
        'source': spell.get('source', 'XPHB'),
    }


def _ordered_input_paths(paths: list) -> list:
    """XPHB first (its 2024 text should win any name collision), then the rest as given."""
    xphb = [p for p in paths if os.path.basename(p) == 'spells-xphb.json']
    rest = [p for p in paths if os.path.basename(p) != 'spells-xphb.json']
    return xphb + rest


def seed_spells(input_paths: list, classes_input_path: str) -> None:
    with open(classes_input_path, 'r', encoding='utf-8') as f:
        classes_by_name = json.load(f)

    db = GoGetDB()
    db.go_create_db()

    total_added = 0
    total_skipped = 0
    for input_path in _ordered_input_paths(input_paths):
        with open(input_path, 'r', encoding='utf-8') as f:
            spells = json.load(f)['spell']

        added = 0
        skipped = 0
        for raw_spell in spells:
            if db.go_get_one('spell', {'name': raw_spell['name']}):
                skipped += 1
                continue
            db.go_add_new('spell', map_spell(raw_spell, classes_by_name))
            added += 1

        print(f'Seeded {added} spells ({skipped} already present) from {input_path}')
        total_added += added
        total_skipped += skipped

    print(f'Total: {total_added} spells added, {total_skipped} already present, across {len(input_paths)} files')


def self_check() -> None:
    """Assert spell ids are stable and well-formed. Run with --self-check.

    These ids are load-bearing across databases: local SQLite and live Postgres
    only agree because both derive the same id from the same name. If any of
    these assertions ever fails, reseeding will orphan characters' spells.
    """
    assert spell_id('Fireball') == spell_id('Fireball'), 'not deterministic'
    assert spell_id('Fireball') != spell_id('Ice Knife'), 'collides across names'
    assert spell_id('Fireball') != spell_id('fireball'), 'case must matter, names are case-sensitive'

    got = spell_id('Fireball')
    assert len(got) == 32, f'id must fit TEXT(32), got {len(got)}'
    assert all(c in '0123456789abcdef' for c in got), f'id must be lowercase hex, got {got!r}'

    # Pinned values. A change here means the namespace or derivation moved,
    # which silently re-ids every spell in every database.
    assert spell_id('Fireball') == '2467cf52a65c56488722c9670097654c', 'Fireball id drifted'
    assert spell_id('Acid Splash') == '3e14558a85425ee895146d47e4091a7c', 'Acid Splash id drifted'

    print('self-check passed: spell ids are deterministic, 32-char hex, and unchanged')


def main() -> None:
    parser = argparse.ArgumentParser(description='Seed the spell reference table from vendored 5etools JSON files')
    parser.add_argument('--input', nargs='+', default=None, help=f'Source JSON file(s) (default: everything matching {DEFAULT_INPUT_GLOB})')
    parser.add_argument('--classes-input', default=DEFAULT_CLASSES_INPUT, help=f'Path to the spell-classes JSON file (default: {DEFAULT_CLASSES_INPUT})')
    parser.add_argument('--self-check', action='store_true', help='Verify spell id generation is stable, then exit without touching the database')
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return
    input_paths = args.input if args.input else sorted(glob.glob(DEFAULT_INPUT_GLOB))
    seed_spells(input_paths, args.classes_input)


if __name__ == '__main__':
    main()
