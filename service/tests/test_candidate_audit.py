import io
import tempfile
import unittest

from service.candidate_audit import audit_rows
from service.core import Store


class CandidateAuditTests(unittest.TestCase):
    def test_upstream_rows_are_counted_but_never_promoted_to_verified_products(self):
        rows = [
            {'brand': 'Acme', 'name': 'Rose', 'source': 'TidyTuesday-Parfumo',
             'source_url': 'https://www.parfumo.com/Perfumes/acme/rose',
             'top_notes': 'Rose', 'middle_notes': '', 'base_notes': '', 'all_notes': 'Rose'},
            {'brand': 'Acme', 'name': 'Rose', 'source': 'anvo2-perfume-rec-assets',
             'source_url': 'https://www.fragrantica.com/perfume/Acme/Rose-1.html',
             'top_notes': '', 'middle_notes': '', 'base_notes': '', 'all_notes': 'floral; sweet'},
            {'brand': 'Fiorucci', 'name': 'Wallstreet', 'source': 'doevent-perfume',
             'source_url': 'https://huggingface.co/datasets/doevent/perfume',
             'top_notes': '', 'middle_notes': '', 'base_notes': '', 'all_notes': 'Jasmine'},
            {'brand': '', 'name': 'Unknown', 'source': 'doevent-perfume',
             'source_url': '', 'top_notes': '', 'middle_notes': '', 'base_notes': '', 'all_notes': ''},
        ]
        report = audit_rows(rows)
        self.assertEqual(report['rows'], 4)
        self.assertEqual(report['distinct_brand_names'], 2)
        self.assertEqual(report['blocked_source_rows'], 2)
        self.assertEqual(report['review_only_rows'], 1)
        self.assertEqual(report['missing_identity_rows'], 1)
        self.assertEqual(report['possible_accords_as_notes'], 1)
        self.assertEqual(report['verified_products_added'], 0)

    def test_malformed_csv_header_is_rejected(self):
        from service.candidate_audit import read_csv
        with self.assertRaisesRegex(ValueError, 'columns'):
            read_csv(io.StringIO('name,notes\nRose,rose\n'))

    def test_only_doevent_names_enter_private_lead_queue_without_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Store(directory + '/editorial.sqlite')
            db.migrate()
            rows = [
                {'brand': 'Fiorucci', 'name': 'Wallstreet', 'source': 'doevent-perfume',
                 'source_url': 'https://huggingface.co/datasets/doevent/perfume',
                 'all_notes': 'Jasmine; Lemon', 'type_hint': 'perfume'},
                {'brand': 'Fiorucci', 'name': 'Wallstreet', 'source': 'doevent-perfume',
                 'source_url': 'https://huggingface.co/datasets/doevent/perfume'},
                {'brand': 'Afnan', 'name': '9pm', 'source': 'anvo2-perfume-rec-assets',
                 'source_url': 'https://www.fragrantica.com/perfume/Afnan/9pm-65414.html'},
                {'brand': 'Example', 'name': 'Empty URL', 'source': 'doevent-perfume',
                 'source_url': ''},
            ]
            result = db.stage_doevent_names(rows)
            self.assertEqual(result, {'staged': 1, 'skipped': 3})
            self.assertEqual(db.stage_doevent_names(rows), {'staged': 0, 'skipped': 4})
            self.assertEqual(db.lead_queue()[0]['name'], 'Wallstreet')
            self.assertEqual(db.catalogue(), [])
            with db.connect() as conn:
                self.assertEqual(db.one(db.query(conn,
                    'SELECT COUNT(*) AS total FROM product_facts'))['total'], 0)


if __name__ == '__main__':
    unittest.main()
