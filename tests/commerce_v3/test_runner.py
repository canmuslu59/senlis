import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('commerce_full_v3'),'full runner missing')
        import commerce_full_v3
        self.api=commerce_full_v3

    def test_all_ids_have_exactly_one_shard(self):
        rows=[{'id':str(i),'brand_name':'X','product_name':'Y'} for i in range(1,1001)]
        parts=[self.api.assign(rows,n,192) for n in range(192)]
        ids=[r['id'] for p in parts for r in p]
        self.assertEqual(len(ids),1000)
        self.assertEqual(len(set(ids)),1000)
        self.assertEqual(max(map(len,parts))-min(map(len,parts)),1)

    def test_deferred_rows_are_not_terminal(self):
        for status in ['deferred_search','deferred_page','worker_error','pending']:
            self.assertFalse(self.api.terminal({'link_status':status,'method_version':'v3.1'}))
        self.assertTrue(self.api.terminal({'link_status':'not_found','method_version':'v3.1'}))

    def test_checkpoint_replay_keeps_latest_result_and_retries_deferred(self):
        records=[{'product_id':'1','link_status':'deferred_search','method_version':'v3.1','checked_at':'2026-10-04T12:00:00Z'},
                 {'product_id':'1','link_status':'verified_link','method_version':'v3.1','checked_at':'2026-10-04T13:00:00Z'},
                 {'product_id':'2','link_status':'deferred_page','method_version':'v3.1','checked_at':'2026-10-04T13:00:00Z'}]
        latest=self.api.latest_records(records)
        self.assertEqual(len(latest),2)
        self.assertEqual(latest['1']['link_status'],'verified_link')
        self.assertFalse(self.api.terminal(latest['2']))

    def test_pending_ids_survive_partial_merge(self):
        rows=[{'id':'1','brand_name':'A','product_name':'P'}, {'id':'2','brand_name':'B','product_name':'Q'}]
        records=[{'product_id':'1','link_status':'not_found','method_version':'v3.1','checked_at':'2026-10-04T12:00:00Z'}]
        merged=self.api.merge_records(rows,records)
        self.assertEqual(len(merged),2)
        self.assertEqual(merged[1]['link_status'],'pending')
        summary=self.api.summarize(merged,2,10)
        self.assertEqual(summary['completed'],1)
        self.assertEqual(summary['remaining'],1)
        self.assertFalse(summary['complete'])

    def test_atomic_local_chunk_is_replayable_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=self.api.Journal(Path(tmp),0,publisher=None)
            row={'product_id':'1','link_status':'not_found','method_version':'v3.1','checked_at':'2026-10-04T12:00:00Z'}
            journal.append(row);journal.flush()
            recovered=self.api.read_chunks(Path(tmp))
            self.assertEqual(recovered,[row])

    def test_unflushed_local_journal_survives_process_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=self.api.Journal(Path(tmp),0,publisher=None)
            row={'product_id':'1','link_status':'not_found','method_version':'v3.1','checked_at':'2026-10-04T12:00:00Z'}
            journal.append(row)
            self.assertEqual(self.api.read_chunks(Path(tmp)),[row])

    def test_retry_record_respects_host_cooldown(self):
        self.assertEqual(self.api.retry_at({'events':[{'retry_at':2000}]},1000),2000)
        self.assertEqual(self.api.retry_at({'events':[]},1000),1120)


if __name__=='__main__':unittest.main()
