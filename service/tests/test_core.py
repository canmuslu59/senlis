import os
import tempfile
import unittest

from service.core import Store, normalize_obf, local_day_due
from service.jobs import deliver
from service.curated import seed


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Store(self.tmp.name + '/senlis.sqlite')
        self.db.migrate()

    def tearDown(self):
        self.tmp.cleanup()

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
        self.assertEqual(len(items), 4)
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
