import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from service.core import Store
from service.curated import seed
from service.supplied_catalogue import build_supplied_package


class SuppliedCatalogueTests(unittest.TestCase):
    def test_dataset_notes_enter_index_but_conflicts_and_accords_do_not(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'supplied.txt'
            source = 'https://huggingface.co/datasets/doevent/perfume'
            rows = [
                ('Acme', 'Rose', 'Rose; Musk', 'Floral', 'doevent-perfume', source),
                ('Acme', 'Rose', 'Musk; Rose', 'Floral', 'doevent-perfume', source),
                ('Acme', 'Amber', 'Amber; Vanilla', '', 'doevent-perfume', source),
                ('Acme', 'Amber', 'Amber; Pepper', '', 'doevent-perfume', source),
                ('Acme', 'Iris', '', 'Floral', 'doevent-perfume', source),
                ('Acme', 'Not sourced', 'Jasmine', '', 'other', source),
            ]
            with path.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.writer(stream, delimiter='\t')
                writer.writerow(('brand', 'name', 'all_notes', 'main_accords', 'source', 'source_url'))
                writer.writerows(rows)
            db = Store(str(Path(directory) / 'editorial.sqlite'))
            db.migrate()
            seed(db)
            package = Path(directory) / 'catalogue.sqlite'
            report = build_supplied_package(db, path, package)
            self.assertEqual(report['fragrances'], 11)
            self.assertEqual(report['dataset_added'], 1)
            self.assertEqual(report['conflicting_identities'], 1)
            with sqlite3.connect(package) as conn:
                self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(conn.execute("SELECT count(*) FROM fragrance_search WHERE fragrance_search MATCH 'Acme*'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT kind FROM fragrances WHERE name='Rose' AND brand='Acme'").fetchone()[0], 'unknown')
                self.assertEqual([x[0] for x in conn.execute("SELECT note FROM fragrance_notes n JOIN fragrances f ON f.id=n.fragrance_id WHERE f.brand='Acme' ORDER BY position")], ['gül', 'misk'])
                self.assertEqual(conn.execute('SELECT count(*) FROM fragrance_photos').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
