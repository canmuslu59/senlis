import tempfile
import unittest
from pathlib import Path

from service.core import Store
from service.catalogue_package import build_package
from service.editor import verify_notes


class EditorialNotesTest(unittest.TestCase):
    def test_reviewed_candidate_enters_package_only_after_independent_note_review(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Store(str(Path(directory) / 'editorial.sqlite'))
            db.migrate()
            product_id = db.import_obf({
                'code': '12345678', 'name': 'Rose Mist', 'brand': 'Example',
                'kind': 'body_mist', 'source_url': 'https://world.openbeautyfacts.org/product/12345678',
                'observed_at': '2026-09-27T00:00:00+00:00'})
            with self.assertRaisesRegex(ValueError, 'reviewed product'):
                verify_notes(db, product_id, ['Gül'], 'https://example.com/rose', 'Example')
            db.review_product(product_id, True)
            with self.assertRaisesRegex(ValueError, 'independent source'):
                verify_notes(db, product_id, ['Gül'], 'https://www.fragrantica.tr/rose', 'Fragrantica')
            with self.assertRaisesRegex(ValueError, 'independent source'):
                verify_notes(db, product_id, ['Gül'], 'https://world.openbeautyfacts.org/product/12345678', 'OBF')
            with self.assertRaisesRegex(ValueError, 'note'):
                verify_notes(db, product_id, [], 'https://example.com/rose', 'Example')
            verify_notes(db, product_id, ['Gül', 'Misk'], 'https://example.com/rose', 'Example')
            result = build_package(db, Path(directory) / 'catalogue.sqlite')
            self.assertEqual(result['fragrances'], 1)
            self.assertEqual(result['note_claims'], 2)
            self.assertEqual(db.product(product_id)['notes'], ['Gül', 'Misk'])


if __name__ == '__main__':
    unittest.main()
