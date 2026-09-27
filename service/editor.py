"""Explicit human review commands for the runner's persistent editorial SQLite."""
import argparse
import json

from .core import Store


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
