import importlib.util
import json
import sys
import unittest
from unittest.mock import patch,Mock
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('commerce_evidence_v4'))
        import commerce_evidence_v4
        self.api=commerce_evidence_v4
        self.row={'id':'90677','brand_name':'Lalique','product_name':'Amethyst','concentration':'EDP'}

    def page(self,extra='',name='Lalique Amethyst EDP 100 ml'):
        obj={'@type':'Product','name':name,'brand':{'name':'Lalique'},'offers':{'@type':'Offer','price':'3000','priceCurrency':'TRY','availability':'https://schema.org/InStock'}}
        return '<title>'+name+'</title><h1>'+name+'</h1><script type="application/ld+json">'+json.dumps(obj)+'</script>'+extra

    def test_sitemap_product_urls_exclude_image_locations(self):
        xml='<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:i="http://www.google.com/schemas/sitemap-image/1.1"><url><loc>https://shop.example/products/amethyst</loc><i:image><i:loc>https://cdn.example/a.jpg</i:loc><i:title>Lalique Amethyst</i:title></i:image></url></urlset>'
        kind,entries=self.api.parse_sitemap(xml)
        self.assertEqual(kind,'urlset');self.assertEqual(len(entries),1)
        self.assertEqual(entries[0]['url'],'https://shop.example/products/amethyst')
        self.assertIn('Lalique Amethyst',entries[0]['titles'])

    def test_http_200_captcha_is_not_a_catalogue(self):
        with self.assertRaises(ValueError):self.api.parse_sitemap('<html>Verify you are human</html>')

    def test_catalogue_must_cover_every_selected_product_map(self):
        self.assertFalse(self.api.catalogue_complete({'root_ok':True,'expected_maps':3,'ok_maps':2,'entry_count':200,'errors':[]}))
        self.assertTrue(self.api.catalogue_complete({'root_ok':True,'expected_maps':3,'ok_maps':3,'entry_count':200,'errors':[]}))

    def test_query_uses_catalogue_title_when_slug_is_legacy(self):
        row={'brand_name':'INNATIVE','product_name':'BERRY AURA (Eau de Parfum)'}
        entry={'url':'https://innativekozmetik.com/old-nocturne-name','titles':['INNATIVE BERRY AURA EDP 50 ml']}
        self.assertTrue(self.api.entry_matches(row,entry,'INNATIVE'))

    def test_numeric_name_does_not_match_substring(self):
        row={'brand_name':'Mad Parfumeur','product_name':'1923'}
        self.assertFalse(self.api.entry_matches(row,{'url':'https://madparfum.com/urun/mad-11923','titles':[]},'Mad Parfumeur'))

    def test_decant_is_rejected_even_when_title_is_exact(self):
        raw=self.page('<p>Bu seçeneklerden satın alınan ürünler sadece dekant şişesinde iletilmektedir. Orijinal şişesinde gönderilmemektedir.</p>')
        offer,reason=self.api.verify_listing(raw,'https://www.perfumepoint.com.tr/amethyst',self.row)
        self.assertIsNone(offer);self.assertEqual(reason,'decant')

    def test_dupe_in_title_is_rejected_even_when_h1_matches(self):
        raw=self.page().replace('<title>Lalique Amethyst EDP 100 ml</title>','<title>Lalique Amethyst muadili</title>')
        offer,reason=self.api.verify_listing(raw,'https://www.perfumepoint.com.tr/amethyst',self.row)
        self.assertIsNone(offer);self.assertEqual(reason,'dupe')

    def test_missing_bottle_volume_is_not_verified_price(self):
        offer,reason=self.api.verify_listing(self.page(name='Lalique Amethyst EDP'),'https://www.perfumepoint.com.tr/amethyst',self.row)
        self.assertIsNone(offer);self.assertEqual(reason,'volume_unproven')

    def test_matching_original_bottle_has_a_price(self):
        offer,reason=self.api.verify_listing(self.page(),'https://www.perfumepoint.com.tr/amethyst',self.row)
        self.assertEqual(reason,'verified');self.assertEqual((offer['price_try'],offer['volume_ml']),(3000,100))

    def test_zero_searches_or_partial_catalogue_never_proves_search(self):
        self.assertFalse(self.api.search_proven([]))
        self.assertFalse(self.api.search_proven([{'complete':False,'searched_entries':200,'catalogue_sha256':'abc'}]))
        self.assertTrue(self.api.search_proven([{'complete':True,'searched_entries':200,'catalogue_sha256':'abc'}]))

    def test_blocked_responses_preserve_evidence_without_becoming_success(self):
        from commerce_v3_http import PoliteClient
        for status,body in [(403,b'Forbidden by store'),(429,b'Rate limit exceeded'),(200,b'<h1>Verify you are human</h1>')]:
            with self.subTest(status=status):
                client=PoliteClient(0,1,retain_error_bodies=True)
                response=Mock(status_code=status,headers={'Content-Type':'text/html'},encoding='utf-8')
                response.iter_content.return_value=iter([body])
                context=Mock();context.__enter__=Mock(return_value=response);context.__exit__=Mock(return_value=False)
                session=Mock();session.get.return_value=context
                with patch.object(client,'_public_dns',return_value=True),patch.object(client,'_pace',return_value=True),patch.object(client,'_session',return_value=session):
                    fetched=client.fetch('https://shop.example/product')
                self.assertFalse(fetched.ok);self.assertEqual(fetched.text,body.decode())

    def test_error_evidence_is_bounded_and_marked_when_truncated(self):
        from commerce_v3_http import PoliteClient
        client=PoliteClient(0,1,retain_error_bodies=True)
        response=Mock(status_code=403,headers={},encoding='utf-8')
        response.iter_content.return_value=iter([b'x'*150000])
        context=Mock();context.__enter__=Mock(return_value=response);context.__exit__=Mock(return_value=False)
        session=Mock();session.get.return_value=context
        with patch.object(client,'_public_dns',return_value=True),patch.object(client,'_pace',return_value=True),patch.object(client,'_session',return_value=session):
            fetched=client.fetch('https://shop.example/product')
        self.assertEqual(len(fetched.text),131072);self.assertTrue(fetched.body_limited)

if __name__=='__main__':unittest.main()
