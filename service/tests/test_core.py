import os
import json
import tempfile
import unittest
import sqlite3
from unittest import mock
from urllib.parse import parse_qs, urlparse

from service.core import SCHEMA, Store, normalize_obf, local_day_due
from service import jobs
from service.jobs import deliver
from service.curated import seed


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Store(self.tmp.name + '/senlis.sqlite')
        self.db.migrate()

    def tearDown(self):
        self.tmp.cleanup()

    def test_existing_database_adds_display_name_without_losing_messages(self):
        path = self.tmp.name + '/legacy.sqlite'
        legacy = SCHEMA.replace(' display_name TEXT NOT NULL,\n', '')
        with sqlite3.connect(path) as conn:
            conn.executescript(legacy)
            conn.execute('INSERT INTO users(id,email,password_hash,created_at) VALUES(?,?,?,?)',
                         ('abcdef123456', 'legacy@example.test', 'old', '2026-01-01'))
            conn.execute('INSERT INTO messages(id,user_id,body,created_at) VALUES(?,?,?,?)',
                         ('message1', 'abcdef123456', 'Gerçek eski yorum', '2026-01-01'))
        upgraded = Store(path)
        upgraded.migrate()
        upgraded.migrate()
        self.assertEqual(upgraded.messages(None)[0]['body'], 'Gerçek eski yorum')
        self.assertEqual(upgraded.messages(None)[0]['author'], 'Üye abcdef')

    def test_catalogue_requires_real_identity_and_keeps_provenance(self):
        self.assertIsNone(normalize_obf({'code': '123', 'product_name': 'Test', 'brands': 'Acme'}))
        self.assertIsNone(normalize_obf({'code': '12345678', 'product_name': 'Test', 'brands': 'Acme', 'categories_tags': ['en:soap']}))
        row = normalize_obf({'code': '12345678', 'product_name': 'Rose Mist', 'brands': 'Acme',
                             'categories_tags': ['en:body-mists'], 'last_modified_t': 1710000000})
        self.assertEqual(row['kind'], 'body_mist')
        self.db.import_obf(row)
        self.db.import_obf(row)
        self.assertEqual(self.db.catalogue('', 20, 0), [])
        self.assertEqual(len(self.db.product_queue()), 1)
        self.db.review_product(self.db.product_queue()[0]['id'], True)
        products = self.db.catalogue('', 20, 0)
        self.assertEqual(len(products), 1)
        product = self.db.product(products[0]['id'])
        self.assertEqual(product['source']['url'], 'https://world.openbeautyfacts.org/product/12345678')
        self.assertIsNone(product['notes'])
        self.assertIsNone(product['price'])
        self.db.verified_fact(product['id'], 'notes', ['rose'],
                              'https://brand.example/rose', 'Official brand')
        verified = self.db.product(product['id'])
        self.assertEqual(verified['notes'], ['rose'])
        self.assertTrue(any(p['field'] == 'notes' and p['source_name'] == 'Official brand'
                            for p in verified['provenance']))
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            self.db.verified_fact(product['id'], 'notes', [], 'https://brand.example/rose', 'Official brand')

    def test_sync_refreshes_first_page_and_rotates_later_pages(self):
        requested = []
        def response(url):
            query = parse_qs(urlparse(url).query)
            requested.append(int(query['page'][0]))
            category = query['categories_tags'][0]
            barcode = str(10000000 + len(requested))
            return json.dumps({'products': [{'code': barcode,
                'product_name': 'Source item', 'brands': 'Source brand',
                'categories_tags': [category]}]}).encode()
        with mock.patch.dict(os.environ, {'SOURCE_CONTACT': 'editor@example.test'}), \
                mock.patch.object(jobs, 'fetch', side_effect=response), \
                mock.patch.object(jobs.time, 'sleep'):
            self.assertIsNone(jobs.sync_obf(self.db, pages=1)['error'])
            self.assertIsNone(jobs.sync_obf(self.db, pages=1)['error'])
        self.assertEqual(requested, [1, 2, 1, 2, 1, 3, 1, 3])
        self.assertEqual(len(self.db.product_queue()), 8)
        self.assertEqual(self.db.catalogue(), [])

    def test_editor_backlog_can_page_and_published_news_leaves_queue(self):
        for number in range(101):
            self.db.import_obf(normalize_obf({'code': str(10000000 + number),
                'product_name': 'Listed product', 'brands': 'Source brand',
                'categories_tags': ['en:perfumes']}))
        self.assertEqual(len(self.db.product_queue()), 100)
        self.assertEqual(len(self.db.product_queue(offset=100)), 1)
        self.db.news_candidate('Official release', 'https://example.com/release', 'Source')
        self.assertEqual(len(self.db.candidate_queue()), 1)
        self.db.publish_news('Official release', 'https://example.com/release', 'Source', True)
        self.assertEqual(self.db.candidate_queue(), [])

    def test_account_rating_and_report_moderation(self):
        self.db.import_obf(normalize_obf({'code': '12345678', 'product_name': 'Rose Mist',
            'brands': 'Acme', 'categories_tags': ['en:body-mists']}))
        self.db.review_product(self.db.product_queue()[0]['id'], True)
        product = self.db.catalogue('', 20, 0)[0]['id']
        user, token = self.db.register('a@example.test', 'long password 123')
        self.assertEqual(self.db.authenticate(token), user)
        self.db.rate(user, product, 4)
        self.db.rate(user, product, 5)
        self.assertEqual(self.db.rating_summary(product), {'count': 1, 'average': 5.0})
        post = self.db.post(user, product, 'Gerçek bir deneyim yorumu.')
        self.db.report(user, post, 'İçeriği inceleyin')
        self.db.moderate(post, 'hidden')
        self.assertEqual(self.db.messages(product, 20, 0), [])
        self.db.delete_account(user)
        self.assertEqual(self.db.rating_summary(product)['count'], 0)
        self.assertIsNone(self.db.authenticate(token))

    def test_login_throttles_bad_passwords(self):
        self.db.register('a@example.test', 'long password 123')
        for _ in range(5):
            self.assertIsNone(self.db.login('a@example.test', 'wrong password'))
        self.assertIsNone(self.db.login('a@example.test', 'long password 123'))

    def test_news_requires_source_and_deduplicates_delivery(self):
        user, _ = self.db.register('a@example.test', 'long password 123')
        self.db.preferences(user, 'Europe/Istanbul', True, True)
        self.assertEqual(self.db.news(), [])
        self.assertTrue(self.db.claim_delivery(user, 'reminder', '2026-09-27'))
        self.assertFalse(self.db.claim_delivery(user, 'reminder', '2026-09-27'))
        self.db.delivery_status(user, 'reminder', '2026-09-27', 'failed')
        self.assertTrue(self.db.claim_delivery(user, 'reminder', '2026-09-27'))
        with self.assertRaises(ValueError):
            self.db.publish_news('Başlık', 'https://example.com/a', 'Example', False)
        self.db.publish_news('Yeni bir parfüm duyurusu', 'https://example.com/a', 'Example', True)
        self.assertEqual(len(self.db.news()), 1)

    def test_timezone_due(self):
        self.assertEqual(local_day_due('Europe/Istanbul', '2026-09-27T06:00:00+00:00', 9), '2026-09-27')
        self.assertIsNone(local_day_due('Europe/Istanbul', '2026-09-27T05:59:00+00:00', 9))

    def test_verified_seed_has_sources_and_no_invented_prices(self):
        seed(self.db)
        seed(self.db)
        items = self.db.catalogue('', 50, 0)
        self.assertEqual(len(items), 10)
        for item in items:
            detail = self.db.product(item['id'])
            self.assertTrue(detail['source']['url'].startswith('https://'))
            self.assertTrue(detail['notes'])
            self.assertIsNone(detail['price'])
            self.assertEqual(detail['rating']['count'], 0)
            self.assertTrue(detail['variants'])

    def test_delivery_needs_article_and_sends_once(self):
        user, _ = self.db.register('a@example.test', 'long password 123')
        self.db.preferences(user, 'Europe/Istanbul', True, True, 'FCM-device-token')
        sent = []
        sender = lambda *args: sent.append(args)
        instant = '2026-09-27T10:05:00+00:00'  # Istanbul 13:05
        self.assertEqual(deliver(self.db, instant, sender), 1)
        self.assertEqual(sent[0][3]['kind'], 'reminder')
        self.db.publish_news('Kaynaklı ürün duyurusu', 'https://example.com/news', 'Official source', True,
                             published_at=instant)
        self.assertEqual(deliver(self.db, instant, sender), 1)
        self.assertEqual(deliver(self.db, instant, sender), 0)
        self.assertEqual(sent[-1][3]['url'], 'https://example.com/news')
        self.assertEqual(deliver(self.db, '2026-09-28T10:05:00+00:00', sender), 1)
        self.assertEqual(sent[-1][3]['kind'], 'reminder')


if __name__ == '__main__':
    unittest.main()
