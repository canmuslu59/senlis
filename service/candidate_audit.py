"""Read-only audit of externally assembled perfume CSV/TSV files.

Counts in an upstream download are never proof of reuse rights, true scent
notes, or distinct verified fragrances. This module does not import products.
"""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


REQUIRED = {'brand', 'name', 'source', 'source_url', 'top_notes',
            'middle_notes', 'base_notes', 'all_notes'}


def read_csv(stream, delimiter=','):
    reader = csv.DictReader(stream, delimiter=delimiter)
    if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
        raise ValueError('missing candidate columns: ' + ', '.join(sorted(REQUIRED)))
    return reader


def key(value):
    return re.sub(r'\W+', '', value.casefold(), flags=re.UNICODE)


def audit_rows(rows):
    sources = Counter()
    unique = set()
    note_sets = {}
    conflicts = set()
    report = {'rows': 0, 'distinct_brand_names': 0, 'blocked_source_rows': 0,
              'review_only_rows': 0, 'missing_identity_rows': 0,
              'rows_with_upstream_note_text': 0, 'possible_accords_as_notes': 0,
              'verified_products_added': 0}
    for row in rows:
        report['rows'] += 1
        if report['rows'] > 1_000_000:
            raise ValueError('candidate file exceeds one million rows')
        brand, name = (str(row.get(field) or '').strip() for field in ('brand', 'name'))
        source = str(row.get('source') or '').strip()
        url = str(row.get('source_url') or '').strip()
        host = (urlparse(url).hostname or '').lower()
        sources[source or '(unknown)'] += 1
        if brand and name and key(brand) and key(name):
            identity = (key(brand), key(name))
            unique.add(identity)
        else:
            report['missing_identity_rows'] += 1
            continue
        if host.endswith('.fragrantica.com') or host.endswith('.fragrantica.tr') or \
                host.endswith('.parfumo.com') or source in ('TidyTuesday-Parfumo',
                'anvo2-perfume-rec-assets'):
            report['blocked_source_rows'] += 1
        else:
            # An upstream MIT label or a name alone cannot establish the origin
            # and reuse rights of the product fields. Human review is required.
            report['review_only_rows'] += 1
        has_pyramid = any(str(row.get(field) or '').strip() for field in
                          ('top_notes', 'middle_notes', 'base_notes'))
        if has_pyramid or str(row.get('all_notes') or '').strip():
            report['rows_with_upstream_note_text'] += 1
            text = str(row.get('all_notes') or '').strip() or ';'.join(
                str(row.get(field) or '') for field in ('top_notes', 'middle_notes', 'base_notes'))
            notes = frozenset(part.strip().casefold() for part in text.split(';') if part.strip())
            if notes:
                if identity in note_sets and notes != note_sets[identity]:
                    conflicts.add(identity)
                note_sets.setdefault(identity, notes)
        if source == 'anvo2-perfume-rec-assets' and not has_pyramid and \
                str(row.get('all_notes') or '').strip():
            report['possible_accords_as_notes'] += 1
    report['distinct_brand_names'] = len(unique)
    report['distinct_note_backed_brand_names'] = len(note_sets)
    report['conflicting_note_identities'] = len(conflicts)
    report['by_source'] = dict(sorted(sources.items()))
    return report


def main():
    parser = argparse.ArgumentParser(description='Audit a candidate CSV/TSV without importing it')
    parser.add_argument('input', type=Path)
    parser.add_argument('--stage-doevent', action='store_true',
                        help='Put doevent names in a private review queue; no notes enter the app')
    parser.add_argument('--database', help='Persistent editorial SQLite, required when staging')
    args = parser.parse_args()
    if args.stage_doevent and not args.database:
        parser.error('--database is required with --stage-doevent')
    if args.input.stat().st_size > 256 * 1024 * 1024:
        raise SystemExit('Candidate file exceeds 256 MiB')
    with args.input.open(encoding='utf-8-sig', newline='') as stream:
        delimiter = '\t' if args.input.suffix.lower() == '.txt' else ','
        report = audit_rows(read_csv(stream, delimiter))
    if args.stage_doevent:
        from .core import Store
        db = Store(args.database)
        db.migrate()
        with args.input.open(encoding='utf-8-sig', newline='') as stream:
            report['private_leads'] = db.stage_doevent_names(read_csv(stream, delimiter))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
