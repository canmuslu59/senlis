"""Publish reviewed news and send fresh, deduplicated FCM alerts from a self runner.

The service account stays in a runner secret, never in the APK or catalogue.
No news is pushed unless an editor has approved a source-linked article.
"""
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .core import Store
from .jobs import poll_news

LOG = logging.getLogger(__name__)


def firebase():
    import firebase_admin
    from firebase_admin import credentials, firestore
    key = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
    if not key:
        raise RuntimeError('SENLIS Firebase service account secret missing')
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(key)))
    return firestore.client()


def publish(db, cloud):
    """Only previously human-reviewed local articles reach the shared feed."""
    count = 0
    for article in db.news(limit=50):
        ref = cloud.collection('news').document(article['id'])
        values = {
            'title': article['title'], 'url': article['url'],
            'source_name': article['source_name'],
            'published_at': datetime.fromisoformat(article['published_at']),
            'reviewed': True,
        }
        previous = ref.get()
        if not previous.exists or previous.to_dict() != values:
            ref.set(values)
            count += 1
    return count


def due_day(zone, moment):
    try:
        local = moment.astimezone(ZoneInfo(zone))
    except (KeyError, ValueError):
        return None
    return local.date().isoformat() if 13 <= local.hour < 21 else None


def deliver(cloud, moment=None, sender=None):
    from firebase_admin import messaging
    from google.cloud.firestore_v1 import FieldFilter, Query
    moment = moment or datetime.now(timezone.utc)
    sender = sender or messaging.send
    news = cloud.collection('news').where(filter=FieldFilter('reviewed', '==', True))\
        .order_by('published_at', direction=Query.DESCENDING).limit(30).stream()
    cutoff = moment - timedelta(days=7)
    articles = [(doc.id, doc.to_dict()) for doc in news]
    articles = [(id, item) for id, item in articles if cutoff <= item['published_at'] <= moment
                and item.get('url', '').startswith('https://')]
    if not articles:
        LOG.info('No fresh, reviewed source-linked news; sending nothing')
        return 0
    delivered = 0
    users = cloud.collection('users').where(filter=FieldFilter('news_push', '==', True)).stream()
    for user in users:
        details = user.to_dict()
        token = details.get('fcm_token')
        day = due_day(details.get('timezone', 'Europe/Istanbul'), moment)
        if not token or not day:
            continue
        ref = user.reference.collection('deliveries').document(day)
        previous = ref.get()
        if previous.exists and previous.to_dict().get('status') != 'failed':
            continue
        sent_ids = {doc.to_dict().get('article_id') for doc in user.reference.collection('deliveries')
                    .order_by('sent_at', direction=Query.DESCENDING).limit(10).stream()
                    if doc.to_dict().get('status') == 'sent'}
        chosen = next(((id, story) for id, story in articles if id not in sent_ids), None)
        if not chosen:
            continue
        article_id, article = chosen
        try:
            if previous.exists:
                if previous.to_dict().get('attempts', 1) >= 3:
                    continue
                ref.update({'status': 'claimed', 'article_id': article_id,
                            'attempts': previous.to_dict().get('attempts', 1) + 1})
            else:
                ref.create({'status': 'claimed', 'article_id': article_id, 'attempts': 1,
                            'sent_at': moment})
            sender(messaging.Message(token=token,
                notification=messaging.Notification(title=article['source_name'] + ' · Koku haberi',
                                                    body=article['title']),
                data={'kind': 'news', 'url': article['url']},
                android=messaging.AndroidConfig(priority='normal')))
            ref.update({'status': 'sent', 'sent_at': moment})
            delivered += 1
        except Exception:
            LOG.exception('News delivery failed for user %s', user.id)
            if ref.get().exists:
                ref.update({'status': 'failed'})
    return delivered


def main():
    logging.basicConfig(level=logging.INFO)
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    db = Store()
    db.migrate()
    if command == 'poll':
        poll_news(db)
        print(f'{len(db.candidate_queue())} pending news candidates')
    elif command == 'publish':
        print(f'{publish(db, firebase())} reviewed news records published')
    elif command == 'deliver':
        print(f'{deliver(firebase())} genuine news notifications sent')
    else:
        raise SystemExit('usage: python -m service.firebase_sync [poll|publish|deliver]')


if __name__ == '__main__':
    main()
