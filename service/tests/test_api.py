import io
import json
import os
import tempfile
import unittest

from service import api
from service.core import Store
from service.curated import seed


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        api.db = Store(self.tmp.name + '/api.sqlite')
        api.db.migrate()
        seed(api.db)

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, method, path, payload=None, token=''):
        raw = json.dumps(payload or {}).encode()
        status = []
        def start_response(code, headers):
            status.append(int(code.split()[0]))
        route, _, query = path.partition('?')
        response = api.application({'REQUEST_METHOD': method, 'PATH_INFO': route,
            'QUERY_STRING': query, 'CONTENT_LENGTH': str(len(raw)),
            'wsgi.input': io.BytesIO(raw), 'HTTP_AUTHORIZATION': 'Bearer ' + token}, start_response)
        return status[0], json.loads(b''.join(response))

    def test_real_product_and_authenticated_community(self):
        code, products = self.request('GET', '/v1/products?q=Libre')
        self.assertEqual(code, 200)
        self.assertEqual(len(products['items']), 1)
        product_id = products['items'][0]['id']
        code, detail = self.request('GET', '/v1/products/' + product_id)
        self.assertEqual(code, 200)
        self.assertTrue(detail['source']['url'].startswith('https://www.yslbeautyus.com/'))
        self.assertIsNone(detail['price'])
        self.assertEqual(self.request('POST', '/v1/community', {'body': 'Gerçek yorum'})[0], 401)
        code, account = self.request('POST', '/v1/accounts', {'email': 'a@example.test', 'password': 'long password 123'})
        self.assertEqual(code, 200)
        token = account['token']
        self.assertEqual(self.request('PUT', '/v1/products/' + product_id + '/rating', {'stars': 4}, token)[0], 200)
        self.assertEqual(self.request('POST', '/v1/community', {'body': 'Bunu deneyen var mı?'}, token)[0], 200)
        self.assertEqual(len(self.request('GET', '/v1/community')[1]['items']), 1)
        self.assertEqual(self.request('DELETE', '/v1/me', token=token)[0], 200)
        self.assertEqual(self.request('POST', '/v1/community', {'body': 'Yeniden'}, token)[0], 401)

    def test_news_requires_editor_review(self):
        self.assertEqual(self.request('GET', '/v1/news'), (200, {'items': []}))
        self.assertEqual(self.request('POST', '/v1/editor/news', {'title': 'Hayali haber'})[0], 403)


if __name__ == '__main__':
    unittest.main()
