import importlib.util,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))

class SourceTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(importlib.util.find_spec('commerce_v5_sources'),'v5 sources missing')
  import commerce_v5_sources
  self.api=commerce_v5_sources
  self.rows=[{'id':'1','brand_name':'INNATIVE','product_name':'BLUE ESSENCE (Eau de Parfum)','source_url':'https://www.trendyol.com/innative/blue-essence-p-123'}, {'id':'2','brand_name':'Caudalie','product_name':'The des Vignes','source_url':'https://www.fragrantica.com/perfume/Caudalie/The-des-Vignes-12.html'}]
  self.registry={'sources':[{'id':'trendyol','host':'trendyol.com','market':'TR','kind':'marketplace'}, {'id':'caudalie_fr','host':'fr.caudalie.com','market':'FR','kind':'official','brand':'Caudalie','root':'https://fr.caudalie.com/sitemap.xml'}]}
 def test_initial_queue_contains_known_trendyol_and_official_discovery(self):
  tasks=self.api.initial_tasks(self.rows,[],self.registry)
  self.assertTrue(any(t['kind']=='product' and t['url'].endswith('-p-123') for t in tasks))
  self.assertTrue(any(t['kind']=='trendyol_directory' for t in tasks))
  self.assertTrue(any(t['kind']=='reference' and t['brand']=='INNATIVE' for t in tasks))
  self.assertTrue(any(t['kind']=='sitemap' and t['source']['market']=='FR' for t in tasks))
 def test_directory_matches_brand_alias_not_substring(self):
  task={'kind':'trendyol_directory','url':'https://www.trendyol.com/s/markalar','source':self.registry['sources'][0]}
  raw='<h1>Markalar A-Z</h1><a href="/innative-x-b1992600">INNATIVE</a><a href="/fake-x-b3">Super INNATIVE</a>'
  tasks,audit=self.api.discover(task,raw,task['url'],self.rows,self.registry)
  self.assertEqual(len(tasks),1);self.assertEqual(tasks[0]['brand'],'INNATIVE');self.assertEqual(audit['matched_brands'],1)
 def test_main_product_related_links_are_candidates_not_prices(self):
  task={'kind':'product','url':self.rows[0]['source_url'],'source':self.registry['sources'][0],'product_ids':['1']}
  raw='<a href="/innative/blue-essence-edp-50-ml-p-555">INNATIVE BLUE ESSENCE EDP 50 ml</a><a href="https://evil.example/p">BLUE ESSENCE</a>'
  tasks,audit=self.api.discover(task,raw,task['url'],self.rows,self.registry)
  self.assertEqual(len(tasks),1);self.assertEqual(tasks[0]['product_ids'],['1']);self.assertNotIn('offers',tasks[0])
 def test_sitemap_indexes_do_not_become_product_pages(self):
  task={'kind':'sitemap','url':'https://fr.caudalie.com/sitemap.xml','source':self.registry['sources'][1],'depth':0}
  raw='<sitemapindex><sitemap><loc>https://fr.caudalie.com/products.xml</loc></sitemap><sitemap><loc>https://evil.example/map.xml</loc></sitemap></sitemapindex>'
  tasks,audit=self.api.discover(task,raw,task['url'],self.rows,self.registry)
  self.assertEqual(len(tasks),1);self.assertEqual(tasks[0]['kind'],'sitemap');self.assertFalse(audit['complete'])
 def test_legacy_official_slug_is_checked_against_all_its_brand_rows(self):
  task={'kind':'sitemap','url':'https://fr.caudalie.com/sitemap.xml','source':self.registry['sources'][1]}
  tasks,audit=self.api.discover(task,'<urlset><url><loc>https://fr.caudalie.com/p/old-code.html</loc></url></urlset>',task['url'],self.rows,self.registry)
  self.assertEqual(tasks[0]['product_ids'],['2'])
 def test_official_link_needs_explicit_reference_and_homepage_brand(self):
  task={'kind':'reference','url':self.rows[1]['source_url'],'brand':'Caudalie','depth':0}
  raw='<a href="https://brand.example/">Official website</a><a href="https://ads.example/">Buy perfume</a>'
  tasks,audit=self.api.discover(task,raw,task['url'],self.rows,self.registry)
  self.assertEqual(len(tasks),1);self.assertEqual(tasks[0]['kind'],'official_home')
  home=tasks[0];raw='<script type="application/ld+json">'+json.dumps({'@type':'Organization','name':'Caudalie','url':'https://brand.example/'})+'</script>'
  tasks,audit=self.api.discover(home,raw,home['url'],self.rows,self.registry)
  self.assertTrue(audit['official_confirmed']);self.assertEqual(tasks[0]['kind'],'sitemap')
  tasks,audit=self.api.discover(home,raw.replace('Caudalie','Other brand'),home['url'],self.rows,self.registry)
  self.assertFalse(tasks);self.assertFalse(audit['complete'])
 def test_unknown_reference_is_not_complete_official_coverage(self):
  task={'kind':'reference','url':self.rows[1]['source_url'],'brand':'Caudalie','depth':0}
  tasks,audit=self.api.discover(task,'<h1>Perfume notes</h1>',task['url'],self.rows,self.registry)
  self.assertFalse(audit['complete']);self.assertEqual(audit['reason'],'official_site_unconfirmed')
 def test_robots_wildcards_block_search_but_allow_product_pages(self):
  rules='User-agent: *\nDisallow: /sr/\nDisallow: /*?q=\n'
  self.assertFalse(self.api.robots_allowed(rules,'https://www.trendyol.com/sr/innative-x-b1992600'))
  self.assertFalse(self.api.robots_allowed(rules,'https://www.trendyol.com/?q=x'))
  self.assertTrue(self.api.robots_allowed(rules,'https://www.trendyol.com/innative/blue-p-123'))
 def test_untrusted_url_never_enters_queue(self):
  self.assertIsNone(self.api.source_for('https://127.0.0.1/p','INNATIVE',self.registry))

 def test_colliding_release_editions_have_verification_context(self):
  rows=[{'id':'450','brand_name':'1000 Flowers','product_name':'Narcotic Flowers','release_year':'2005'},{'id':'451','brand_name':'1000 Flowers','product_name':'Narcotic Flowers','release_year':'2019'}]
  idx=self.api.RowsIndex(rows)
  self.assertEqual(idx.by_id['450'].get('competing_release_years'),['2005','2019'])
 def test_translation_language_is_not_verified_sales_market(self):
  task={'kind':'official_home','url':'https://brand.example','brand':'Caudalie','reference_url':'https://www.fragrantica.com/designers/Caudalie.html'}
  raw='<html lang="tr"><script type="application/ld+json">'+json.dumps({'@type':'Organization','name':'Caudalie','url':'https://brand.example'})+'</script></html>'
  tasks,audit=self.api.discover(task,raw,task['url'],self.rows,self.registry)
  self.assertEqual(tasks[0]['source']['market'],'unknown');self.assertEqual(tasks[0]['source']['language'],'tr')

if __name__=='__main__':unittest.main()
