import tempfile
import unittest
from pathlib import Path

from service.core import Store
from service.curated import seed
from service.export_catalog import snapshot, write_snapshot


class ExportCatalogTest(unittest.TestCase):
    def test_only_reviewed_source_linked_products_without_community_data(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Store(str(Path(temp) / 'editorial.sqlite'))
            db.migrate()
            seed(db)
            db.import_obf({'code': '12345678', 'name': 'Unreviewed', 'brand': 'Example',
                           'kind': 'perfume', 'source_url': 'https://world.openbeautyfacts.org/product/12345678',
                           'observed_at': '2026-09-27T00:00:00+00:00'})
            data = snapshot(db)
            self.assertEqual(len(data['items']), 4)
            for item in data['items']:
                self.assertEqual(item['reviewed'], 1)
                self.assertNotIn('rating', item)
                self.assertIsNone(item['price'])
                self.assertTrue(item['source']['url'].startswith('https://'))
                self.assertTrue(item['provenance'])
            output = Path(temp) / 'catalogue.json'
            self.assertEqual(write_snapshot(db, output), 4)
            before = output.read_bytes()
            self.assertEqual(write_snapshot(db, output, if_changed=True), 0)
            self.assertEqual(output.read_bytes(), before)
            self.assertIn('Cheirosa 62', output.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
