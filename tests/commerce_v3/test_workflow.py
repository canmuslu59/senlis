import unittest
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]

class WorkflowTests(unittest.TestCase):
    def test_full_queue_is_paused_and_cannot_schedule_waves(self):
        p=ROOT/'.github/workflows/commerce-full-v3.yml'
        self.assertTrue(p.exists(),'full workflow missing')
        flow=yaml.load(p.read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(flow['permissions']['contents'],'read')
        self.assertEqual(flow['concurrency']['cancel-in-progress'],'true')
        self.assertEqual(list(flow['jobs']),['paused'])
        pilot=yaml.load((ROOT/'.github/workflows/commerce-evidence-v4.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(pilot['permissions']['contents'],'read')
        self.assertEqual(list(pilot['jobs']),['evidence-pilot'])
        job=pilot['jobs']['evidence-pilot']
        self.assertNotIn('strategy',job)
        self.assertEqual(job['timeout-minutes'],'25')

if __name__=='__main__':unittest.main()
