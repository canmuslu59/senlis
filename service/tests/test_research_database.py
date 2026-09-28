import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from service.research_database import build_research_database


class ResearchDatabaseTests(unittest.TestCase):
    def test_retains_each_source_claim_without_inventing_consensus(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.txt'
            with source.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.writer(stream, delimiter='\t')
                writer.writerow(('brand', 'name', 'type_hint', 'top_notes', 'middle_notes',
                                 'base_notes', 'all_notes', 'main_accords', 'source', 'source_url'))
                writer.writerows([
                    ('Maison A', 'Rose', 'perfume', 'Rose', '', 'Musk', 'Rose; Musk',
                     'Floral', 'alpha', 'https://example.org/1'),
                    ('Maison A', 'Rose', 'perfume', '', '', '', 'Musk; Rose',
                     '', 'beta', 'https://example.org/2'),
                    ('Maison A', 'Amber', 'perfume', '', '', '', 'Amber; Vanilla',
                     '', 'alpha', 'https://example.org/3'),
                    ('Maison A', 'Amber', 'perfume', '', '', '', 'Amber; Pepper',
                     '', 'beta', 'https://example.org/4'),
                    ('Maison A', 'Iris', 'perfume', '', '', '', '',
                     'Floral; Powdery', 'alpha', 'https://example.org/5'),
                    ('!', '⚡', 'perfume', '', '', '', 'Jasmine',
                     '', 'alpha', 'https://example.org/6'),
                ])
            target = Path(directory) / 'research.sqlite'
            report = build_research_database(source, target)
            self.assertEqual(report['raw_rows'], 6)
            self.assertEqual(report['candidate_identity_groups'], 3)
            self.assertEqual(report['note_backed_groups'], 2)
            self.assertEqual(report['conflicted_groups'], 1)
            self.assertEqual(report['unresolved_identity_rows'], 1)
            with sqlite3.connect(target) as connection:
                self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(connection.execute('SELECT count(*) FROM observations').fetchone()[0], 6)
                self.assertEqual(connection.execute('SELECT count(*) FROM observation_notes').fetchone()[0], 9)
                self.assertEqual(connection.execute('SELECT count(*) FROM observation_notes WHERE note IN (\'Floral\', \'Powdery\')').fetchone()[0], 0)
                self.assertIsNone(connection.execute("SELECT representative_observation_id FROM identity_groups WHERE name='Amber'").fetchone()[0])
                self.assertEqual(connection.execute("SELECT note_status FROM identity_groups WHERE name='Rose'").fetchone()[0], 'single_list')
                self.assertEqual(connection.execute("SELECT count(*) FROM identity_search WHERE identity_search MATCH 'Rose'").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT count(*) FROM observations WHERE group_id IS NULL").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT tier FROM observation_notes WHERE observation_id=1 ORDER BY position").fetchall(), [('top',), ('base',)])

    def test_same_input_rebuild_is_deterministic_and_failed_input_preserves_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.txt'
            source.write_text('brand\tname\tall_notes\tsource\tsource_url\nA\tB\tRose\tx\thttps://example.org\n', encoding='utf-8')
            target = Path(directory) / 'research.sqlite'
            first = build_research_database(source, target)
            second = build_research_database(source, target)
            self.assertEqual(first['input_sha256'], second['input_sha256'])
            self.assertEqual(first['candidate_identity_groups'], second['candidate_identity_groups'])
            source.write_text('bad\theader\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                build_research_database(source, target)
            with sqlite3.connect(target) as connection:
                self.assertEqual(connection.execute('SELECT count(*) FROM identity_groups').fetchone()[0], 1)

    def test_repeated_export_headers_are_quarantined(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.txt'
            source.write_text('brand\tname\tall_notes\tsource\tsource_url\n'
                              'Brand\tName\tTop Notes\ta\tURL\n'
                              'Brand\tName\tTop Notes\ta\tURL\n'
                              'Brand\tReal perfume\tRose\ta\thttps://example.org/p\n', encoding='utf-8')
            target = Path(directory) / 'research.sqlite'
            report = build_research_database(source, target)
            self.assertEqual(report['repeated_header_rows'], 2)
            self.assertEqual(report['candidate_identity_groups'], 1)
            with sqlite3.connect(target) as connection:
                self.assertEqual(connection.execute("SELECT count(*) FROM observations WHERE identity_issue='repeated_header'").fetchone()[0], 2)

    def test_flankers_remain_separate_and_prose_is_not_a_note(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.txt'
            source.write_text('brand\tname\ttop_notes\tall_notes\tsource\tsource_url\n'
                              'Commodity\tBook\t\tCedar\ta\thttps://example.org/book\n'
                              'Commodity\tBook-\t\tMusk\ta\thttps://example.org/book-personal\n'
                              'Commodity\tBook+\t\tAmber\ta\thttps://example.org/book-bold\n'
                              'A\tPerfume\tthe top notes begin with a story and include rose\tRose\t'
                              'doevent-perfume\thttps://huggingface.co/datasets/doevent/perfume\n',
                              encoding='utf-8')
            target = Path(directory) / 'research.sqlite'
            report = build_research_database(source, target)
            self.assertEqual(report['candidate_identity_groups'], 4)
            with sqlite3.connect(target) as connection:
                notes = connection.execute('SELECT note FROM observation_notes WHERE observation_id=4').fetchall()
                self.assertEqual(notes, [('Rose',)])


if __name__ == '__main__':
    unittest.main()
