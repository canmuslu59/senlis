import importlib.util
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))

class FullScanTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('commerce_full_v4'),'full scan runner missing')
        import commerce_full_v4 as api
        self.api=api
        self.source={'id':'shop','brand':''}
        self.report={'source_id':'shop','complete':True,'entry_count':3,'catalogue_sha256':'abc'}
        self.entries=[{'url':'https://shop.example/lalique-amethyst-100','titles':['Lalique Amethyst EDP 100 ml']},
                      {'url':'https://shop.example/lalique-amethyst-eclat','titles':['Lalique Amethyst Eclat EDP']},
                      {'url':'https://shop.example/chloe-edp','titles':['Chloe EDP 50 ml']}]
        self.row={'id':'1','brand_name':'Lalique','product_name':'Amethyst'}

    def test_index_keeps_every_candidate_and_handles_eponymous_name(self):
        idx=self.api.CatalogueIndex(self.source,self.report,self.entries)
        self.assertEqual([e['url'] for e in idx.search(self.row)],[e['url'] for e in self.entries[:2]])
        self.assertEqual(idx.search({'brand_name':'Chloe','product_name':'Chloe'}),self.entries[2:])
        self.assertEqual(idx.search({'brand_name':'Other','product_name':'Amethyst'}),[])

    def test_plan_covers_all_rows_but_fetches_shared_pages_once(self):
        rows=[self.row,dict(self.row,id='2'),{'id':'3','brand_name':'Unknown','product_name':'Missing'}]
        plan=self.api.build_plan(rows,[(self.source,self.report,self.entries)])
        self.assertEqual(len(plan['queries']),3);self.assertEqual(len(plan['pages']),2)
        self.assertEqual(plan['pages'][0]['product_ids'],['1','2'])
        self.assertEqual(plan['queries'][2]['search_audits'][0]['matched_urls'],[])
        self.assertTrue(all(q['search_proven'] for q in plan['queries']))

    def test_partial_source_blocks_plan_instead_of_creating_false_absence(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):
            self.api.build_plan([self.row],[(self.source,dict(self.report,complete=False),self.entries)])

    def test_manifest_boundary_overflow_is_repaired_only_when_next_row_proves_it(self):
        good={'id':'1001','brand_name':'Brand','product_name':'Second','release_year':'2020','source_url':'https://source.example/second'}
        bad={'id':'1000','brand_name':'Brand','product_name':'First','release_year':'2019','source_url':'https://source.example/first1001',None:['Brand','Second','2020','https://source.example/second']}
        self.assertTrue(hasattr(self.api,'validated_rows'),'manifest boundary repair missing')
        rows,warnings=self.api.validated_rows([bad,good],{})
        self.assertEqual(rows[0]['source_url'],'https://source.example/first')
        self.assertNotIn(None,rows[0]);self.assertEqual(len(rows),2)
        self.assertEqual(warnings,[{'product_id':'1000','repair':'duplicated_next_row_at_chunk_boundary','next_id':'1001'}])
        bad[None][1]='Different product'
        with self.assertRaisesRegex(ValueError,'unexplained manifest'):
            self.api.validated_rows([bad,good],{})

    def test_retry_state_survives_checkpoint_and_never_means_absence(self):
        plan=self.api.build_plan([self.row],[(self.source,self.report,self.entries[:1])])
        url=plan['pages'][0]['url']
        failed={'url':url,'attempts':1,'final':False,'success':False,'retry_at':200,'decisions':[]}
        self.assertFalse(self.api.eligible(failed,199));self.assertTrue(self.api.eligible(failed,201))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.api.write_batch(root,[failed])
            restored=self.api.read_checks(root)
            self.assertEqual(restored[url],failed)
            summary=self.api.summarize(plan,restored)
            self.assertEqual(summary['pending_pages'],1);self.assertFalse(summary['finished'])
            failed.update(attempts=3,final=True)
            self.api.write_batch(root,[failed]);restored=self.api.read_checks(root)
            summary=self.api.summarize(plan,restored)
            self.assertEqual(summary['unresolved_pages'],1);self.assertTrue(summary['finished']);self.assertFalse(summary['complete'])
            self.assertEqual(self.api.product_result(plan['queries'][0],restored)['status'],'page_unavailable')

    def test_success_without_price_is_not_a_catalogue_no_match(self):
        plan=self.api.build_plan([self.row],[(self.source,self.report,self.entries[:1])])
        url=plan['pages'][0]['url']
        checks={url:{'url':url,'attempts':1,'final':True,'success':True,'decisions':[{'product_id':'1','reason':'identity_or_price_unproven','offer':None}]}}
        self.assertEqual(self.api.product_result(plan['queries'][0],checks)['status'],'no_accepted_offer')
        self.assertTrue(self.api.summarize(plan,checks)['complete'])

    def test_verified_offer_survives_other_candidate_timeout(self):
        plan=self.api.build_plan([self.row],[(self.source,self.report,self.entries)])
        offer={'price_try':500,'volume_ml':100,'stock_status':'in_stock','purchase_url':self.entries[0]['url']}
        checks={self.entries[0]['url']:{'url':self.entries[0]['url'],'final':True,'success':True,'decisions':[{'product_id':'1','reason':'verified','offer':offer}]}}
        result=self.api.product_result(plan['queries'][0],checks)
        self.assertEqual(result['status'],'verified_offer');self.assertFalse(result['verification_complete'])
        self.assertEqual(result['best_offer']['price_try'],500)

if __name__=='__main__':unittest.main()
