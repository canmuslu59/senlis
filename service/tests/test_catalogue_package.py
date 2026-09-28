import sqlite3
import tempfile
import unittest
from pathlib import Path

from service.core import Store
from service.curated import seed
from service.catalogue_package import build_package


class CataloguePackageTest(unittest.TestCase):
    def test_exports_only_reviewed_note_backed_fragrances_with_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Store(str(Path(directory) / 'editorial.sqlite'))
            source.migrate()
            seed(source)
            candidate = source.import_obf({
                'code': '12345678', 'name': 'Unconfirmed scent', 'brand': 'Example',
                'kind': 'perfume', 'source_url': 'https://world.openbeautyfacts.org/product/12345678',
                'observed_at': '2026-09-27T00:00:00+00:00'})
            source.review_product(candidate, True)
            output = Path(directory) / 'catalogue.sqlite'
            report = build_package(source, output)

            self.assertEqual(report['fragrances'], 4)
            self.assertEqual(report['with_notes'], 4)
            with sqlite3.connect(output) as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM fragrances').fetchone()[0], 4)
                self.assertIsNone(conn.execute('SELECT id FROM fragrances WHERE id=?', (candidate,)).fetchone())
                self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertGreater(conn.execute('SELECT count(*) FROM fragrance_variants').fetchone()[0], 0)
                row = conn.execute('''SELECT f.name,n.note,f.note_source_url FROM fragrances f
                    JOIN fragrance_notes n ON n.fragrance_id=f.id WHERE f.name LIKE '%Cheirosa 62%'
                    AND n.note='vanilya' ''').fetchone()
                self.assertEqual(row[1:], ('vanilya', 'https://soldejaneiro.com/products/cheirosa-62-hair-body-fragrance-mist'))
                self.assertEqual(conn.execute('''SELECT note_source_name FROM fragrances
                    WHERE name LIKE '%Cheirosa 62%' ''').fetchone()[0], 'Sol de Janeiro')
                self.assertEqual(conn.execute('''SELECT count(*) FROM fragrance_search
                    WHERE fragrance_search MATCH 'Cheirosa*' ''').fetchone()[0], 2)

    def test_invalid_note_provenance_does_not_replace_previous_package(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Store(str(Path(directory) / 'editorial.sqlite'))
            source.migrate()
            seed(source)
            output = Path(directory) / 'catalogue.sqlite'
            build_package(source, output)
            before = output.read_bytes()
            with source.connect() as conn:
                conn.execute("UPDATE product_facts SET source_url='http://untrusted' WHERE field='notes'")
            with self.assertRaisesRegex(ValueError, 'note provenance'):
                build_package(source, output)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
