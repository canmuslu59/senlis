"""Export reviewed, source-attributed products as a static Android catalogue.

Run against the editorial SQLite database after review. Candidate imports are
never exported. The bundled snapshot can be updated without any user data.
"""
import argparse
import json
from pathlib import Path

from .core import Store, now
from .curated import seed


def snapshot(db):
    with db.connect() as conn:
        ids = [row['id'] for row in db.many(db.query(conn,
            'SELECT id FROM products WHERE reviewed=1 ORDER BY name,id'))]
    items = []
    for product_id in ids:
        item = db.product(product_id)
        source = item.get('source') or {}
        if not source.get('url', '').startswith('https://') or not source.get('observed_at'):
            raise ValueError(f'missing product provenance: {product_id}')
        for fact in item.get('provenance', []):
            if not fact.get('source_url', '').startswith('https://'):
                raise ValueError(f'missing fact provenance: {product_id}')
        # Community totals in an editorial database are neither portable nor
        # part of product identity. Load live community aggregates separately.
        item.pop('rating', None)
        items.append(item)
    if not items:
        raise ValueError('refusing to publish an empty catalogue')
    return {'schema_version': 1, 'generated_at': now(), 'items': items}


def write_snapshot(db, path, if_changed=False):
    data = snapshot(db)
    destination = Path(path)
    if if_changed and destination.exists():
        previous = json.loads(destination.read_text(encoding='utf-8'))
        if previous.get('items') == data['items']:
            return 0
    body = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(body, encoding='utf-8')
    return len(data['items'])


def main():
    parser = argparse.ArgumentParser(description='Export only reviewed, source-linked fragrance records')
    parser.add_argument('--database', default='senlis-editorial.sqlite')
    parser.add_argument('--output', default='docs/catalogue.json')
    parser.add_argument('--asset-output', help='copy the same verified snapshot into the APK assets')
    parser.add_argument('--seed', action='store_true', help='add manually verified brand entries')
    parser.add_argument('--if-changed', action='store_true', help='keep the previous timestamp if facts are unchanged')
    args = parser.parse_args()
    db = Store(args.database)
    db.migrate()
    if args.seed:
        seed(db)
    count = write_snapshot(db, args.output, args.if_changed)
    if count and args.asset_output:
        target = Path(args.asset_output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(args.output).read_bytes())
    print(f'{count} reviewed records exported to {args.output}' if count else 'No verified catalogue changes')


if __name__ == '__main__':
    main()
