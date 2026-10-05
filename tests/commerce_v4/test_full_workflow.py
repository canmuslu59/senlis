import unittest
from pathlib import Path
import yaml

class FullWorkflowTests(unittest.TestCase):
    def test_full_scan_has_one_serial_queue_and_fresh_canary_gate(self):
        p=Path(__file__).resolve().parents[2]/'.github/workflows/commerce-full-v4.yml'
        self.assertTrue(p.exists(),'full v4 workflow missing')
        f=yaml.load(p.read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(f['concurrency']['cancel-in-progress'],'false')
        self.assertEqual(f['permissions']['contents'],'write')
        self.assertEqual(set(f['jobs']),{'prepare','scan','report'})
        scan=f['jobs']['scan'];self.assertEqual(scan['needs'],'prepare')
        self.assertEqual(scan['strategy']['max-parallel'],'1')
        self.assertEqual(scan['strategy']['fail-fast'],'true')
        self.assertEqual(len(scan['strategy']['matrix']['part']),24)
        self.assertEqual(scan['timeout-minutes'],'100')
        runs='\n'.join(s.get('run','') for s in f['jobs']['prepare']['steps'])
        self.assertIn('--attempts 3',runs);self.assertIn('commerce_full_v4.py prepare',runs)
        self.assertIn('always()',f['jobs']['report']['if'])
        self.assertIn('needs.prepare.result',f['jobs']['report']['if'])

if __name__=='__main__':unittest.main()
