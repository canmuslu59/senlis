"""Explicit human review commands for the runner's persistent editorial SQLite."""
import argparse
import json
from urllib.parse import urlparse

from .core import Store


def verify_notes(db, product_id, notes, source_url, source_name):
    """Record notes an editor checked on an independent product source page."""
    product = db.product(product_id)
    if product is None:
        raise ValueError('reviewed product required before adding notes')
    host = (urlparse(source_url).hostname or '').lower()
    if not source_url.startswith('https://') or not host or host == 'openbeautyfacts.org' or \
            host.endswith('.openbeautyfacts.org') or \
            host.startswith('fragrantica.') or '.fragrantica.' in host:
        raise ValueError('independent source page required for scent notes')
    cleaned = [note.strip() for note in notes]
    if not source_name.strip() or not 1 <= len(cleaned) <= 60 or not all(
            1 <= len(note) <= 80 for note in cleaned) or len({note.casefold() for note in cleaned}) != len(cleaned):
        raise ValueError('nonempty, distinct note list and source name required')
    db.verified_fact(product_id, 'notes', cleaned, source_url, source_name)


def main():
    parser = argparse.ArgumentParser(description='Review SENLIS source candidates')
    parser.add_argument('--database', default='senlis-editorial.sqlite')
    sub = parser.add_subparsers(dest='command', required=True)
    products = sub.add_parser('products')
    products.add_argument('--offset', type=int, default=0)
    news = sub.add_parser('news')
    news.add_argument('--offset', type=int, default=0)
    approve = sub.add_parser('approve-product')
    approve.add_argument('id')
    approve.add_argument('--checked-url', required=True)
    notes = sub.add_parser('verify-notes')
    notes.add_argument('id')
    notes.add_argument('--checked-url', required=True, help='Independent brand or reusable note source')
    notes.add_argument('--source-name', required=True)
    notes.add_argument('--note', action='append', required=True, help='Repeat for every checked scent note')
    story = sub.add_parser('publish-news')
    story.add_argument('id')
    story.add_argument('--checked-url', required=True)
    story.add_argument('--published-at', required=True, help='Actual source publication timestamp, ISO 8601')
    args = parser.parse_args()
    db = Store(args.database)
    db.migrate()
    if args.command == 'products':
        print(json.dumps(db.product_queue(offset=args.offset), ensure_ascii=False, indent=2))
    elif args.command == 'news':
        print(json.dumps(db.candidate_queue(offset=args.offset), ensure_ascii=False, indent=2))
    elif args.command == 'approve-product':
        with db.connect() as conn:
            candidate = db.one(db.query(conn, '''SELECT p.id,s.source_url FROM products p
                JOIN product_sources s ON s.product_id=p.id AND s.field='name'
                WHERE p.id=? AND p.reviewed=0''', (args.id,)))
        if candidate is None or candidate['source_url'] != args.checked_url:
            raise SystemExit('Candidate/source URL mismatch; inspect the queue first')
        db.review_product(args.id, True)
        print(f'Approved sourced product: {args.id}')
    elif args.command == 'verify-notes':
        verify_notes(db, args.id, args.note, args.checked_url, args.source_name)
        print(f'Verified {len(args.note)} sourced scent notes for {args.id}')
    elif args.command == 'publish-news':
        with db.connect() as conn:
            candidate = db.one(db.query(conn, '''SELECT id,title,url,source_name FROM news_candidates
                WHERE id=? AND status='pending' ''', (args.id,)))
        if candidate is None or candidate['url'] != args.checked_url:
            raise SystemExit('Candidate/source URL mismatch; inspect the queue first')
        db.publish_news(candidate['title'], candidate['url'], candidate['source_name'],
                        reviewed=True, published_at=args.published_at)
        print(f'Published reviewed story: {args.id}')


if __name__ == '__main__':
    main()
