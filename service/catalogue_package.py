"""Build an indexed, source-linked local catalogue without claiming missing notes.

This package is an intermediate delivery format. The Android preview still
reads its four-record JSON snapshot until the paged SQLite UI is integrated.
"""
import argparse
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from .core import Store, now


def build_package(editorial: Store, output: str | Path) -> dict:
    """Atomically export reviewed products that have attributable scent notes."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, pending = tempfile.mkstemp(prefix='senlis-', suffix='.sqlite', dir=target.parent)
    os.close(fd)
    package = sqlite3.connect(pending)
    count = note_count = reviewed = 0
    try:
        package.executescript('''
            PRAGMA user_version=2;
            CREATE TABLE fragrances (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, brand TEXT NOT NULL,
              kind TEXT NOT NULL, family TEXT, source_url TEXT NOT NULL,
              source_name TEXT NOT NULL, observed_at TEXT NOT NULL,
              note_source_url TEXT NOT NULL, notes_verified_at TEXT NOT NULL);
            CREATE TABLE fragrance_notes (
              fragrance_id TEXT NOT NULL REFERENCES fragrances(id),
              position INTEGER NOT NULL, note TEXT NOT NULL,
              PRIMARY KEY(fragrance_id,position));
            CREATE INDEX fragrance_notes_lookup ON fragrance_notes(note);
            CREATE VIRTUAL TABLE fragrance_search USING fts4(
              fragrance_id, name, brand, tokenize=unicode61);
            CREATE TABLE package_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')
        with editorial.connect() as source:
            reviewed = editorial.one(editorial.query(source,
                'SELECT count(*) AS total FROM products WHERE reviewed=1'))['total']
            cursor = editorial.query(source, '''SELECT p.id,p.name,p.brand,p.kind,
                identity.source_url,identity.source_name,identity.observed_at,
                notes.value AS notes,notes.source_url AS note_source_url,
                notes.verified_at AS notes_verified_at,
                family.value AS family
                FROM products p
                JOIN product_sources identity ON identity.product_id=p.id AND identity.field='name'
                JOIN product_facts notes ON notes.product_id=p.id AND notes.field='notes'
                LEFT JOIN product_facts family ON family.product_id=p.id AND family.field='family'
                WHERE p.reviewed=1 ORDER BY p.id''')
            while batch := cursor.fetchmany(500):
                for record in batch:
                    row = dict(record)
                    try:
                        notes = json.loads(row['notes'])
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f'invalid notes: {row["id"]}') from exc
                    if not isinstance(notes, list) or not notes or not all(
                        isinstance(note, str) and note.strip() for note in notes
                    ):
                        raise ValueError(f'invalid notes: {row["id"]}')
                    if not row['note_source_url'].startswith('https://') or not row['notes_verified_at']:
                        raise ValueError(f'note provenance missing: {row["id"]}')
                    if not row['source_url'].startswith('https://') or not row['source_name'] or not row['observed_at']:
                        raise ValueError(f'identity provenance missing: {row["id"]}')
                    family = json.loads(row['family']) if row['family'] else None
                    package.execute('''INSERT INTO fragrances VALUES(?,?,?,?,?,?,?,?,?,?)''',
                        (row['id'], row['name'], row['brand'], row['kind'], family,
                         row['source_url'], row['source_name'], row['observed_at'],
                         row['note_source_url'], row['notes_verified_at']))
                    package.executemany('INSERT INTO fragrance_notes VALUES(?,?,?)',
                        ((row['id'], position, note.strip().casefold())
                         for position, note in enumerate(notes)))
                    package.execute('INSERT INTO fragrance_search VALUES(?,?,?)',
                        (row['id'], row['name'], row['brand']))
                    count += 1
                    note_count += len(notes)
        metadata = {'schema_version': 2, 'generated_at': now(), 'fragrances': count,
                    'with_notes': count, 'note_claims': note_count,
                    'reviewed_without_notes': reviewed - count}
        if not count:
            raise ValueError('refusing to publish an empty note-backed catalogue')
        package.executemany('INSERT INTO package_meta VALUES(?,?)',
                            ((key, str(value)) for key, value in metadata.items()))
        package.commit()
        if package.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('catalogue integrity check failed')
        package.close()
        os.replace(pending, target)
        return metadata
    except Exception:
        package.close()
        Path(pending).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description='Build an indexed reviewed-only local catalogue')
    parser.add_argument('--database', default='senlis-editorial.sqlite')
    parser.add_argument('--output', default='docs/catalogue.sqlite')
    args = parser.parse_args()
    print(json.dumps(build_package(Store(args.database), args.output), ensure_ascii=False))


if __name__ == '__main__':
    main()
