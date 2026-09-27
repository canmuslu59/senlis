"""Conservative upstream import, editorial queue polling and FCM delivery.

Run `python -m service.jobs sync` daily and `python -m service.jobs deliver`
hourly. Respect upstream API rate limits and keep unverified news unpublished.
"""
import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .core import Store, local_day_due, normalize_obf, now


LOG = logging.getLogger(__name__)
USER_AGENT = 'SENLIS/1.0 (catalogue sync; contact: ' + os.getenv('SOURCE_CONTACT', 'configure-contact') + ')'
FEEDS = {
    'Coty': 'https://investors.coty.com/rss/pressrelease.aspx',
    'Estée Lauder Companies': 'https://www.elcompanies.com/en/rss/press-releases',
    'Fragrance Creators Association': 'https://fragrance-creators-association.suite.accessnewswire.com/browse/rss',
}


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json, application/xml, text/xml'})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read(4_000_000)


def sync_obf(db, pages=1):
    """Search two relevant category tags; never infer notes, images or prices."""
    if not os.getenv('SOURCE_CONTACT'):
        raise RuntimeError('SOURCE_CONTACT must be a monitored address for OBF API access')
    run_id = uuid.uuid4().hex
    with db.connect() as conn:
        db.query(conn, 'INSERT INTO import_runs(id,source,started_at) VALUES(?,?,?)', (run_id, 'OBF', now()))
    accepted = rejected = 0
    error = None
    try:
        for category in ('perfumes', 'body-mists'):
            for page in range(1, max(1, min(int(pages), 5)) + 1):
                params = urllib.parse.urlencode({
                    'categories_tags': 'en:' + category, 'page': page, 'page_size': 100,
                    'fields': 'code,product_name,brands,categories_tags,last_modified_t',
                    'json': 1,
                })
                url = 'https://world.openbeautyfacts.org/api/v2/search?' + params
                records = json.loads(fetch(url)).get('products', [])
                for record in records:
                    normalized = normalize_obf(record)
                    if normalized:
                        db.import_obf(normalized)
                        accepted += 1
                    else:
                        rejected += 1
                if not records:
                    break
                time.sleep(7)  # <=10 search requests/minute/IP
    except Exception as exc:
        error = str(exc)[:500]
        LOG.exception('OBF sync failed')
    with db.connect() as conn:
        db.query(conn, '''UPDATE import_runs SET finished_at=?,accepted=?,rejected=?,error=? WHERE id=?''',
                 (now(), accepted, rejected, error, run_id))
    return {'accepted': accepted, 'rejected': rejected, 'error': error}


def poll_news(db):
    """Queue headlines from official feeds. An editor must verify and publish."""
    for source, url in FEEDS.items():
        try:
            root = ET.fromstring(fetch(url))
            for item in root.findall('.//item')[:30]:
                db.news_candidate(item.findtext('title') or '', item.findtext('link') or '', source)
        except Exception:
            LOG.exception('News feed failed: %s', source)


def send_fcm(token, title, body, data):
    """Firebase service account is supplied only as a Render secret."""
    import firebase_admin
    from firebase_admin import credentials, messaging
    if not firebase_admin._apps:
        account = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        if not account:
            raise RuntimeError('FCM credentials missing')
        firebase_admin.initialize_app(credentials.Certificate(json.loads(account)))
    return messaging.send(messaging.Message(token=token,
        notification=messaging.Notification(title=title, body=body), data=data,
        android=messaging.AndroidConfig(priority='normal')))


def deliver(db, timestamp=None, sender=send_fcm):
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    count = 0
    for user in db.subscribers():
        if not user['fcm_token']:
            continue
        for kind, enabled, hour in (('reminder', user['reminder'], 9), ('news', user['news_push'], 13)):
            day = local_day_due(user['timezone'], timestamp, hour)
            if not enabled or not day:
                continue
            article = db.unsent_news(user['id'], timestamp) if kind == 'news' else None
            if kind == 'news' and not article:
                LOG.warning('No fresh, unsent editor-verified article; news push withheld for %s', day)
                continue
            if not db.claim_delivery(user['id'], kind, day, article['id'] if article else None):
                continue
            title = 'SENLIS koku hatırlatması' if kind == 'reminder' else article['source_name'] + ' · Koku haberi'
            body = 'Bugün hangi koku sana eşlik edecek?' if kind == 'reminder' else article['title']
            data = {'kind': kind}
            if article:
                data['url'] = article['url']
            try:
                sender(user['fcm_token'], title, body, data)
                db.delivery_status(user['id'], kind, day, 'sent')
                count += 1
            except Exception:
                db.delivery_status(user['id'], kind, day, 'failed')
                LOG.exception('Push failed for user %s', user['id'])
    return count


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    db = Store()
    db.migrate()
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command == 'sync':
        print(sync_obf(db, os.getenv('OBF_PAGES', '1')))
        poll_news(db)
    elif command == 'deliver':
        print({'sent': deliver(db)})
    else:
        raise SystemExit('usage: python -m service.jobs [sync|deliver]')
