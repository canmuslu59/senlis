"""Build a private, source-preserving research database from an attributed TSV.

Every imported row remains an observation, including duplicate and conflicting
claims. A product's note list is only a candidate consensus when all nonempty
lists agree; this database makes no assertion that an upstream claim is licensed
for publication or independently verified.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import unicodedata
import uuid
from collections import Counter
from pathlib import Path

REQUIRED = {'brand', 'name', 'all_notes', 'source', 'source_url'}
NOTE_COLUMNS = (('top_notes', 'top'), ('middle_notes', 'middle'),
                ('base_notes', 'base'))
UNKNOWN_NOTES = {'n/a', 'none', 'unknown', '-'}


def _identity_key(value):
    """Conservative candidate key: Book, Book- and Book+ remain distinct."""
    normalized = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', value).casefold()).strip()
    return normalized if any(character.isalnum() for character in normalized) else ''


def _notes(row):
    """Return actual note text, never the separate main_accords column."""
    claims = []
    seen = set()
    # This uploaded doevent subset has 33 prose descriptions in tier fields.
    # Its separate all_notes list remains a source claim, not a checked pyramid.
    for column, tier in (() if row.get('source') == 'doevent-perfume' else NOTE_COLUMNS):
        for raw in str(row.get(column) or '').split(';'):
            note = raw.strip()
            normalized = note.casefold()
            if note and len(note) <= 150 and normalized not in UNKNOWN_NOTES and normalized not in seen:
                claims.append((tier, note, normalized))
                seen.add(normalized)
    for raw in str(row.get('all_notes') or '').split(';'):
        note = raw.strip()
        normalized = note.casefold()
        if note and len(note) <= 150 and normalized not in UNKNOWN_NOTES and normalized not in seen:
            claims.append(('unspecified', note, normalized))
            seen.add(normalized)
    return claims


def _schema(connection):
    connection.executescript('''
        PRAGMA user_version=1;
        PRAGMA foreign_keys=ON;
        CREATE TABLE identity_groups (
            id TEXT PRIMARY KEY, brand TEXT NOT NULL, name TEXT NOT NULL,
            brand_key TEXT NOT NULL, name_key TEXT NOT NULL,
            observation_count INTEGER NOT NULL, source_count INTEGER NOT NULL,
            note_status TEXT NOT NULL CHECK(note_status IN
                ('no_notes','single_list','conflicting_lists')),
            distinct_note_lists INTEGER NOT NULL,
            representative_observation_id INTEGER,
            UNIQUE(brand_key,name_key));
        CREATE TABLE observations (
            id INTEGER PRIMARY KEY, group_id TEXT REFERENCES identity_groups(id)
                DEFERRABLE INITIALLY DEFERRED,
            brand TEXT NOT NULL, name TEXT NOT NULL, type_hint TEXT NOT NULL,
            top_notes TEXT NOT NULL, middle_notes TEXT NOT NULL,
            base_notes TEXT NOT NULL, all_notes TEXT NOT NULL,
            main_accords TEXT NOT NULL, source TEXT NOT NULL,
            source_url TEXT NOT NULL, note_signature TEXT,
            identity_issue TEXT);
        CREATE INDEX observations_group ON observations(group_id);
        CREATE INDEX observations_source ON observations(source);
        CREATE TABLE observation_notes (
            observation_id INTEGER NOT NULL REFERENCES observations(id),
            position INTEGER NOT NULL, tier TEXT NOT NULL,
            note TEXT NOT NULL, note_key TEXT NOT NULL,
            PRIMARY KEY(observation_id,position));
        CREATE INDEX observation_notes_key ON observation_notes(note_key);
        CREATE VIRTUAL TABLE identity_search USING fts4(
            group_id, name, brand, tokenize=unicode61);
        CREATE TABLE source_summary (
            source TEXT PRIMARY KEY, observations INTEGER NOT NULL,
            distinct_source_urls INTEGER NOT NULL);
        CREATE TABLE database_meta (key TEXT PRIMARY KEY,value TEXT NOT NULL);
    ''')


def build_research_database(supplied: str | Path, output: str | Path) -> dict:
    supplied, output = Path(supplied), Path(output)
    if supplied.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('input exceeds 256 MiB')
    digest = hashlib.sha256()
    with supplied.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='senlis-research-', suffix='.sqlite', dir=output.parent)
    os.close(fd)
    connection = sqlite3.connect(temporary)
    try:
        _schema(connection)
        groups = {}
        sources = Counter()
        urls = {}
        raw_rows = unresolved = note_rows = note_claims = 0
        exact_pairs = set()
        header_rows = 0
        with supplied.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream, delimiter='\t' if supplied.suffix.lower() == '.txt' else ',')
            if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
                raise ValueError('input lacks brand, name, all_notes, source or source_url')
            for row in reader:
                raw_rows += 1
                if raw_rows > 1_000_000:
                    raise ValueError('input exceeds one million rows')
                fields = {field: str(row.get(field) or '').strip() for field in
                          ('brand', 'name', 'type_hint', 'top_notes', 'middle_notes',
                           'base_notes', 'all_notes', 'main_accords', 'source', 'source_url')}
                # A punctuation-only name/brand is kept for review, not assigned
                # a fictitious or colliding product identity.
                identity = (_identity_key(fields['brand']), _identity_key(fields['name']))
                fake_header = (fields['brand'].casefold(), fields['name'].casefold(),
                               fields['source_url'].casefold()) == ('brand', 'name', 'url')
                usable = bool(identity[0] and identity[1]) and not fake_header
                if fake_header:
                    header_rows += 1
                if usable:
                    exact_pairs.add((fields['brand'], fields['name']))
                group_id = uuid.uuid5(uuid.NAMESPACE_URL,
                    'senlis-research:' + '\0'.join(identity)).hex if usable else None
                notes = [] if fake_header else _notes(fields)
                signature = json.dumps(sorted({note_key for _, _, note_key in notes}),
                                       ensure_ascii=False) if notes else None
                if notes:
                    note_rows += 1
                    note_claims += len(notes)
                sources[fields['source']] += 1
                urls.setdefault(fields['source'], set()).add(fields['source_url'])
                if usable:
                    group = groups.setdefault(identity, {
                        'id': group_id, 'brand': fields['brand'], 'name': fields['name'],
                        'count': 0, 'sources': set(), 'signatures': {},
                    })
                    group['count'] += 1
                    group['sources'].add(fields['source'])
                    if signature is not None:
                        # Prefer a row with a described pyramid, then the first
                        # observation. The note content itself is never merged.
                        rank = (bool(fields['top_notes'] or fields['middle_notes'] or
                                     fields['base_notes']), -raw_rows)
                        previous = group['signatures'].get(signature)
                        if previous is None or rank > previous[0]:
                            group['signatures'][signature] = (rank, raw_rows)
                else:
                    unresolved += 1
                connection.execute('''INSERT INTO observations VALUES
                    (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (raw_rows, group_id, fields['brand'], fields['name'], fields['type_hint'],
                     fields['top_notes'], fields['middle_notes'], fields['base_notes'],
                     fields['all_notes'], fields['main_accords'], fields['source'],
                     fields['source_url'], signature,
                     None if usable else 'repeated_header' if fake_header else 'empty_normalized_identity'))
                connection.executemany('INSERT INTO observation_notes VALUES(?,?,?,?,?)',
                    ((raw_rows, position, tier, note, note_key)
                     for position, (tier, note, note_key) in enumerate(notes)))
        note_backed = conflicted = single_list = 0
        for (brand_key, name_key), group in sorted(groups.items()):
            signatures = group['signatures']
            status = ('no_notes' if not signatures else
                      'single_list' if len(signatures) == 1 else 'conflicting_lists')
            if signatures:
                note_backed += 1
            if status == 'single_list':
                single_list += 1
            if status == 'conflicting_lists':
                conflicted += 1
            representative = next(iter(signatures.values()))[1] if status == 'single_list' else None
            connection.execute('INSERT INTO identity_groups VALUES(?,?,?,?,?,?,?,?,?,?)',
                (group['id'], group['brand'], group['name'], brand_key, name_key,
                 group['count'], len(group['sources']), status, len(signatures), representative))
            connection.execute('INSERT INTO identity_search VALUES(?,?,?)',
                (group['id'], group['name'], group['brand']))
        connection.executemany('INSERT INTO source_summary VALUES(?,?,?)',
            ((source, count, len(urls[source])) for source, count in sorted(sources.items())))
        report = {
            'schema_version': 1, 'input_sha256': digest.hexdigest(),
            'input_bytes': supplied.stat().st_size, 'raw_rows': raw_rows,
            'candidate_identity_groups': len(groups),
            'exact_brand_name_pairs': len(exact_pairs),
            'unresolved_identity_rows': unresolved, 'repeated_header_rows': header_rows,
            'note_text_rows': note_rows, 'observation_note_claims': note_claims,
            'note_backed_groups': note_backed, 'single_list_groups': single_list,
            'conflicted_groups': conflicted,
            'no_note_groups': len(groups) - note_backed,
            'published_products': 0, 'source_rows': dict(sorted(sources.items())),
        }
        connection.executemany('INSERT INTO database_meta VALUES(?,?)',
                               ((name, json.dumps(value, ensure_ascii=False))
                                for name, value in report.items()))
        connection.commit()
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('research database integrity check failed')
        if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise ValueError('research database has broken references')
        connection.close()
        os.replace(temporary, output)
        return report
    except Exception:
        connection.close()
        Path(temporary).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description='Build a source-preserving private research database')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build_research_database(args.input, args.output), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
