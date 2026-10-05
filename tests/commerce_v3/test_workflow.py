import unittest
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]

class WorkflowTests(unittest.TestCase):
    def test_full_scope_has_ordered_waves_and_bounded_parallelism(self):
        p=ROOT/'.github/workflows/commerce-full-v3.yml'
        self.assertTrue(p.exists(),'full workflow missing')
        flow=yaml.load(p.read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(flow['permissions']['contents'],'write')
        self.assertEqual(flow['concurrency']['cancel-in-progress'],'false')
        jobs=flow['jobs']
        for wave in range(48):
            job=jobs[f'wave_{wave:02d}']
            self.assertEqual(job['with']['wave'],str(wave))
            self.assertIn('canary',job['needs'])
            if wave:self.assertIn(f'wave_{wave-1:02d}',job['needs'])
        batch=yaml.load((ROOT/'.github/workflows/commerce-full-v3-batch.yml').read_text(),Loader=yaml.BaseLoader)
        job=batch['jobs']['scan']
        self.assertEqual(job['strategy']['matrix']['lane'],['0','1','2','3'])
        self.assertEqual(job['strategy']['max-parallel'],'4')
        self.assertEqual(job['timeout-minutes'],'340')
        self.assertIn('wave_47',jobs['merge']['needs'])

if __name__=='__main__':unittest.main()
