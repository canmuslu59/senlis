"""Build an indexed, source-linked local catalogue without claiming missing notes.

Only editor-reviewed identities and independently verified notes are shipped.
"""
import argparse
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from .core import Store, independent_https, now, recent_observation


def build_package(editorial: Store, output: str | Path) -> dict:
    """Atomically export reviewed products that have attributable scent notes."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, pending = tempfile.mkstemp(prefix='senlis-', suffix='.sqlite', dir=target.parent)
    os.close(fd)
    package = sqlite3.connect(pending)
    count = note_count = reviewed = photo_count = offer_count = 0
    try:
        package.executescript('''
            PRAGMA user_version=4;
            CREATE TABLE fragrances (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, brand TEXT NOT NULL,
              kind TEXT NOT NULL, family TEXT, source_url TEXT NOT NULL,
              source_name TEXT NOT NULL, observed_at TEXT NOT NULL,
              source_license TEXT NOT NULL, note_source_url TEXT NOT NULL,
              note_source_name TEXT NOT NULL, notes_verified_at TEXT NOT NULL,
              family_source_url TEXT, family_source_name TEXT, family_verified_at TEXT);
            CREATE TABLE fragrance_notes (
              fragrance_id TEXT NOT NULL REFERENCES fragrances(id),
              position INTEGER NOT NULL, note TEXT NOT NULL,
              PRIMARY KEY(fragrance_id,position));
            CREATE INDEX fragrance_notes_lookup ON fragrance_notes(note);
            CREATE TABLE fragrance_variants (
              fragrance_id TEXT NOT NULL REFERENCES fragrances(id),
              label TEXT NOT NULL, size_ml INTEGER, concentration TEXT,
              source_url TEXT NOT NULL, observed_at TEXT NOT NULL,
              PRIMARY KEY(fragrance_id,label));
            CREATE TABLE fragrance_photos (
              fragrance_id TEXT PRIMARY KEY REFERENCES fragrances(id),
              image_url TEXT NOT NULL, source_url TEXT NOT NULL,
              license_name TEXT NOT NULL, license_url TEXT NOT NULL,
              attribution TEXT NOT NULL, verified_at TEXT NOT NULL);
            CREATE TABLE fragrance_offers (
              fragrance_id TEXT NOT NULL REFERENCES fragrances(id),
              retailer TEXT NOT NULL, offer_url TEXT NOT NULL,
              amount_minor INTEGER NOT NULL, currency TEXT NOT NULL,
              country TEXT NOT NULL, variant_label TEXT NOT NULL,
              observed_at TEXT NOT NULL,
              PRIMARY KEY(fragrance_id,offer_url,variant_label));
            CREATE VIRTUAL TABLE fragrance_search USING fts4(
              fragrance_id, name, brand, tokenize=unicode61);
            CREATE TABLE package_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')
        with editorial.connect() as source:
            reviewed = editorial.one(editorial.query(source,
                'SELECT count(*) AS total FROM products WHERE reviewed=1'))['total']
            cursor = editorial.query(source, '''SELECT p.id,p.name,p.brand,p.kind,
                identity.source_url,identity.source_name,identity.observed_at,
                identity.license AS source_license,
                notes.value AS notes,notes.source_url AS note_source_url,
                notes.source_name AS note_source_name,notes.verified_at AS notes_verified_at,
                family.value AS family,family.source_url AS family_source_url,
                family.source_name AS family_source_name,family.verified_at AS family_verified_at
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
                    if not row['note_source_name']:
                        raise ValueError(f'note source name missing: {row["id"]}')
                    if not row['source_url'].startswith('https://') or not row['source_name'] or not row['observed_at']:
                        raise ValueError(f'identity provenance missing: {row["id"]}')
                    family = json.loads(row['family']) if row['family'] else None
                    package.execute('''INSERT INTO fragrances VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (row['id'], row['name'], row['brand'], row['kind'], family,
                         row['source_url'], row['source_name'], row['observed_at'], row['source_license'],
                         row['note_source_url'], row['note_source_name'], row['notes_verified_at'],
                         row['family_source_url'], row['family_source_name'], row['family_verified_at']))
                    package.executemany('INSERT INTO fragrance_notes VALUES(?,?,?)',
                        ((row['id'], position, note.strip().casefold())
                         for position, note in enumerate(notes)))
                    package.execute('INSERT INTO fragrance_search VALUES(?,?,?)',
                        (row['id'], row['name'], row['brand']))
                    count += 1
                    note_count += len(notes)
            variants = editorial.query(source, '''SELECT v.product_id,v.label,v.size_ml,
                v.concentration,v.source_url,v.observed_at FROM product_variants v
                JOIN products p ON p.id=v.product_id
                JOIN product_facts n ON n.product_id=p.id AND n.field='notes'
                WHERE p.reviewed=1 ORDER BY v.product_id,v.label''')
            while batch := variants.fetchmany(500):
                for v in batch:
                    v = dict(v)
                    if not v['source_url'].startswith('https://') or not v['observed_at']:
                        raise ValueError(f'variant provenance missing: {v["product_id"]}')
                    package.execute('INSERT INTO fragrance_variants VALUES(?,?,?,?,?,?)',
                        (v['product_id'], v['label'], v['size_ml'], v['concentration'],
                         v['source_url'], v['observed_at']))
            photos = editorial.query(source, '''SELECT m.* FROM product_photos m
                JOIN products p ON p.id=m.product_id
                JOIN product_facts n ON n.product_id=p.id AND n.field='notes'
                WHERE p.reviewed=1 ORDER BY m.product_id''')
            while batch := photos.fetchmany(500):
                for photo in batch:
                    m = dict(photo)
                    if not all(independent_https(m[field]) for field in ('image_url', 'source_url', 'license_url')) or \
                            not m['license_name'] or not m['attribution'] or not m['verified_at']:
                        raise ValueError(f'photo provenance missing: {m["product_id"]}')
                    package.execute('INSERT INTO fragrance_photos VALUES(?,?,?,?,?,?,?)',
                        (m['product_id'], m['image_url'], m['source_url'], m['license_name'],
                         m['license_url'], m['attribution'], m['verified_at']))
                    photo_count += 1
            offers = editorial.query(source, '''SELECT o.* FROM product_offers o
                JOIN products p ON p.id=o.product_id
                JOIN product_facts n ON n.product_id=p.id AND n.field='notes'
                WHERE p.reviewed=1 ORDER BY o.product_id,o.observed_at DESC''')
            while batch := offers.fetchmany(500):
                for offer in batch:
                    o = dict(offer)
                    if not recent_observation(o['observed_at']):
                        continue
                    if not independent_https(o['offer_url']) or o['amount_minor'] <= 0:
                        raise ValueError(f'offer provenance missing: {o["product_id"]}')
                    package.execute('INSERT INTO fragrance_offers VALUES(?,?,?,?,?,?,?,?)',
                        (o['product_id'], o['retailer'], o['offer_url'], o['amount_minor'],
                         o['currency'], o['country'], o['variant_label'], o['observed_at']))
                    offer_count += 1
        metadata = {'schema_version': 4, 'generated_at': now(), 'fragrances': count,
                    'with_notes': count, 'note_claims': note_count,
                    'reviewed_without_notes': reviewed - count,
                    'photos': photo_count, 'current_offers': offer_count}
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
