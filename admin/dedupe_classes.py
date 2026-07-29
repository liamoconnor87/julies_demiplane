"""
Deduplicate the "class" reference table in a PostgreSQL database.

A prior bug in json_to_postgres.py (seeding classes with fresh ids, then
importing an export that already had those same classes under different
ids) could double every class row. This finds class names with more than
one row, keeps whichever id is actually referenced by class_to_character
(or the first one if none are), repoints any class_to_character rows that
reference a duplicate onto the surviving id, then deletes the duplicates.

Defaults to a dry run — pass --apply to actually make changes.

Usage (from project root):
    DATABASE_URL="postgresql://..." python admin/dedupe_classes.py
    DATABASE_URL="postgresql://..." python admin/dedupe_classes.py --apply
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2
import psycopg2.extras


def dedupe_classes(apply: bool) -> None:
    url = os.environ.get('DATABASE_URL')
    if not url:
        print("Error: DATABASE_URL environment variable is not set.")
        sys.exit(1)

    db = psycopg2.connect(url)
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute('SELECT id, name FROM "class" ORDER BY name, id')
    rows = cursor.fetchall()

    by_name = {}
    for row in rows:
        by_name.setdefault(row['name'], []).append(row['id'])

    duplicates = {name: ids for name, ids in by_name.items() if len(ids) > 1}

    if not duplicates:
        print("No duplicate classes found — nothing to do.")
        cursor.close()
        db.close()
        return

    print(f"Found {len(duplicates)} class name(s) with duplicates:")
    for name, ids in duplicates.items():
        print(f"  {name}: {len(ids)} rows — {ids}")

    total_repointed = 0
    total_deleted = 0

    for name, ids in duplicates.items():
        cursor.execute(
            'SELECT class_id, COUNT(*) AS cnt FROM "class_to_character" '
            'WHERE class_id = ANY(%s) GROUP BY class_id',
            (ids,)
        )
        usage = {r['class_id']: r['cnt'] for r in cursor.fetchall()}
        keep_id = max(ids, key=lambda i: usage.get(i, 0))
        drop_ids = [i for i in ids if i != keep_id]

        print(f"\n{name}: keeping {keep_id} (used by {usage.get(keep_id, 0)} character(s)), dropping {drop_ids}")

        if apply:
            cursor.execute(
                'UPDATE "class_to_character" SET class_id = %s WHERE class_id = ANY(%s)',
                (keep_id, drop_ids)
            )
            repointed = cursor.rowcount
            cursor.execute('DELETE FROM "class" WHERE id = ANY(%s)', (drop_ids,))
            deleted = cursor.rowcount
            total_repointed += repointed
            total_deleted += deleted
            print(f"  repointed {repointed} class_to_character row(s), deleted {deleted} class row(s)")
        else:
            cursor.execute(
                'SELECT COUNT(*) AS cnt FROM "class_to_character" WHERE class_id = ANY(%s)',
                (drop_ids,)
            )
            would_repoint = cursor.fetchone()['cnt']
            print(f"  [dry run] would repoint {would_repoint} class_to_character row(s), would delete {len(drop_ids)} class row(s)")

    if apply:
        db.commit()
        print(f"\nDone — repointed {total_repointed} row(s), deleted {total_deleted} duplicate class row(s).")
    else:
        db.rollback()
        print("\nDry run only — no changes were made. Re-run with --apply to actually fix this.")

    cursor.close()
    db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deduplicate the class reference table')
    parser.add_argument('--apply', action='store_true', help='Actually apply the fix (default is dry-run)')
    args = parser.parse_args()

    dedupe_classes(apply=args.apply)
