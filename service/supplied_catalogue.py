"""Build a local discovery snapshot from the user's supplied, source-labelled TSV.

This first pass uses only the doevent subset, whose dataset card declares MIT.
It preserves the uploader's attribution and distinguishes these listed notes
from manufacturer-checked claims. Other upstream subsets need their own route.
"""
import argparse
import csv
import json
import os
import sqlite3
import tempfile
import uuid
from contextlib import closing
from pathlib import Path

from .candidate_audit import key
from .catalogue_package import build_package
from .core import Store


SOURCE = 'https://huggingface.co/datasets/doevent/perfume'
SOURCE_DATE = '2024-05-01T00:00:00+00:00'
NOTE_EQUIVALENTS = {'vanilla': 'vanilya', 'rose': 'gül', 'jasmine': 'yasemin',
                    'sandalwood': 'sandal ağacı', 'bergamot': 'bergamot',
                    'amber': 'amber', 'musk': 'misk',
                    'orange blossom': 'portakal çiçeği'}


def listed_notes(value):
    result = []
    for raw in str(value or '').split(';'):
        note = raw.strip().casefold()
        if not note or len(note) > 100 or note in ('n/a', 'none', 'unknown', '-'):
            continue
        note = NOTE_EQUIVALENTS.get(note, note)
        if note not in result:
            result.append(note)
    return result


def build_supplied_package(editorial: Store, supplied: str | Path, output: str | Path) -> dict:
    supplied, output = Path(supplied), Path(output)
    if supplied.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('supplied file exceeds 256 MiB')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, scratch = tempfile.mkstemp(prefix='senlis-supplied-', suffix='.sqlite', dir=output.parent)
    os.close(fd)
    Path(scratch).unlink()
    try:
        metadata = build_package(editorial, scratch)
        selected = {}
        conflicting = set()
        with supplied.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream, delimiter='\t' if supplied.suffix.lower() == '.txt' else ',')
            if not reader.fieldnames or not {'brand', 'name', 'all_notes', 'source', 'source_url'}.issubset(reader.fieldnames):
                raise ValueError('supplied file lacks required columns')
            for row in reader:
                if row['source'] != 'doevent-perfume' or row['source_url'] != SOURCE:
                    continue
                brand, name = row['brand'].strip(), row['name'].strip()
                if not 2 <= len(brand) <= 120 or not 2 <= len(name) <= 180 or not key(brand) or not key(name):
                    continue
                notes = listed_notes(row['all_notes'])
                if not notes:
                    continue
                identity = (key(brand), key(name))
                if identity in selected:
                    if set(notes) != set(selected[identity][2]):
                        conflicting.add(identity)
                else:
                    selected[identity] = (brand, name, notes)

        with closing(sqlite3.connect(scratch)) as package, package:
            curated = {(key(brand), key(name)) for brand, name in package.execute(
                'SELECT brand,name FROM fragrances')}
            added = note_count = 0
            for identity, (brand, name, notes) in sorted(selected.items()):
                if identity in conflicting or identity in curated:
                    continue
                fragrance_id = uuid.uuid5(uuid.NAMESPACE_URL, SOURCE + '#' + '/'.join(identity)).hex
                package.execute('INSERT INTO fragrances VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (fragrance_id, name, brand, 'unknown', None, SOURCE,
                     'doevent/perfume veri seti', SOURCE_DATE,
                     'MIT etiketi; özgün alan kaynağı belirtilmemiş veri seti',
                     SOURCE, 'doevent/perfume veri seti', SOURCE_DATE,
                     None, None, None))
                package.executemany('INSERT INTO fragrance_notes VALUES(?,?,?)',
                    ((fragrance_id, position, note) for position, note in enumerate(notes)))
                package.execute('INSERT INTO fragrance_search VALUES(?,?,?)', (fragrance_id, name, brand))
                added += 1
                note_count += len(notes)
            metadata['fragrances'] += added
            metadata['with_notes'] += added
            metadata['note_claims'] += note_count
            metadata['dataset_added'] = added
            metadata['conflicting_identities'] = len(conflicting)
            metadata['dataset_source'] = SOURCE
            package.executemany('INSERT OR REPLACE INTO package_meta VALUES(?,?)',
                ((field, str(value)) for field, value in metadata.items()))
            if package.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('catalogue integrity check failed')
        os.replace(scratch, output)
        return metadata
    finally:
        Path(scratch).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description='Build a local dataset-labelled fragrance snapshot')
    parser.add_argument('input', type=Path)
    parser.add_argument('--database', required=True, help='editorial SQLite with checked products')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build_supplied_package(Store(args.database), args.input, args.output), ensure_ascii=False))


if __name__ == '__main__':
    main()
