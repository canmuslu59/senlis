import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from service.core import Store
from service.firebase_sync import due_day, publish


class FakeDocument:
    exists = False
    def __init__(self): self.values = None
    def get(self): return self
    def set(self, values): self.values = values; self.exists = True
    def to_dict(self): return self.values


class FakeCloud:
    def __init__(self): self.docs = {}
    def collection(self, name): self.name = name; return self
    def document(self, id):
        key = (self.name, id)
        return self.docs.setdefault(key, FakeDocument())


class FirebaseSyncTest(unittest.TestCase):
    def test_publishes_only_human_reviewed_source_linked_story(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Store(str(Path(temp) / 'editorial.sqlite'))
            db.migrate()
            db.news_candidate('Unreviewed headline', 'https://example.org/candidate', 'Source')
            cloud = FakeCloud()
            self.assertEqual(publish(db, cloud), 0)
            db.publish_news('Verified title', 'https://example.org/verified', 'Source', True)
            self.assertEqual(publish(db, cloud), 1)
            self.assertEqual(publish(db, cloud), 0)
            self.assertEqual(len(cloud.docs), 1)
            self.assertTrue(next(iter(cloud.docs.values())).values['reviewed'])

    def test_local_news_window(self):
        moment = datetime(2026, 9, 27, 10, 30, tzinfo=timezone.utc)
        self.assertEqual(due_day('Europe/Istanbul', moment), '2026-09-27')
        self.assertIsNone(due_day('America/Los_Angeles', moment))


if __name__ == '__main__':
    unittest.main()
