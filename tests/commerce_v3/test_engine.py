import importlib.util
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('commerce_v3_http'), 'polite client missing')
        import commerce_v3_http
        self.api = commerce_v3_http

    def test_four_lanes_have_disjoint_host_slots(self):
        starts = sorted(self.api.next_slot(100, lane, 4, 2.5) for lane in range(4))
        self.assertEqual(starts, [100, 102.5, 105, 107.5])
        self.assertGreaterEqual(min(b-a for a,b in zip(starts,starts[1:])), 2.5)
        self.assertEqual(self.api.next_slot(100.6, 0, 4, 2.5),110)

    def test_retry_after_seconds_and_date(self):
        self.assertEqual(self.api.retry_seconds('120',0),120)
        self.assertEqual(self.api.retry_seconds('Thu, 01 Jan 1970 00:03:00 GMT',60),120)

    def test_private_and_credentialed_urls_are_rejected(self):
        for url in ['http://example.com','https://127.0.0.1/x','https://169.254.169.254/',
                    'https://[::1]/','https://user:pass@example.com','https://localhost/x']:
            self.assertFalse(self.api.public_url(url),url)
        self.assertTrue(self.api.public_url('https://www.sevil.com.tr/a.html'))

    def test_challenge_is_not_an_empty_search(self):
        self.assertTrue(self.api.is_challenge('<html>Verify you are human CAPTCHA</html>'))
        self.assertFalse(self.api.is_challenge('<h1>Amethyst EDP</h1>'))

    def test_regular_product_with_captcha_field_is_not_a_challenge_page(self):
        self.assertFalse(self.api.is_challenge('<h1>A Drop d Issey</h1><form><input name="g-recaptcha-response"></form>'))

    def test_configured_proxy_can_resolve_public_host_when_local_dns_cannot(self):
        client=self.api.PoliteClient(0,1)
        with patch('commerce_v3_http.requests.utils.get_environ_proxies',return_value={'https':'http://proxy.example:8080'}):
            with patch('commerce_v3_http.socket.getaddrinfo',side_effect=self.api.socket.gaierror()):
                self.assertTrue(client._public_dns('tr.caudalie.com'))


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('commerce_v3_engine'), 'engine missing')
        import commerce_v3_engine
        self.api = commerce_v3_engine
        self.row={'id':'90677','brand_name':'Lalique','product_name':'Amethyst','release_year':'2007','concentration':'EDP'}

    def page(self,name='Lalique Amethyst EDP 100 ml',price='3162.50',currency='TRY',extra=''):
        obj={'@type':'Product','name':name,'brand':{'name':'Lalique'},'offers':{'@type':'Offer','price':price,'priceCurrency':currency,'availability':'https://schema.org/InStock'}}
        return '<html><h1>'+name+'</h1><script type="application/ld+json">'+json.dumps(obj)+'</script>'+extra+'</html>'

    def test_main_product_page_offer(self):
        o=self.api.parse_page(self.page(), 'https://www.perfumepoint.com.tr/lalique-amethyst-edp-100-ml',self.row)
        self.assertEqual(o['price_try'],3162.50)
        self.assertEqual(o['volume_ml'],100)
        self.assertEqual(o['stock_status'],'in_stock')

    def test_official_description_supplies_concentration_and_selected_volume(self):
        row={'brand_name':'Caudalie','product_name':'Ange des Vignes','concentration':'EDP'}
        obj={'@type':'Product','name':'Ange des Vignes Parfüm','brand':{'name':'Caudalie'},
             'offers':{'@type':'Offer','price':'1650','priceCurrency':'TRY'}}
        raw='<h1>Ange des Vignes Parfüm</h1><div class="html-content">Ange des Vignes, Caudalie Eau de Parfum.</div><p class="selected">50mL</p><script type="application/ld+json">'+json.dumps(obj)+'</script>'
        offer=self.api.parse_page(raw,'https://tr.caudalie.com/p/531R1/ange.html',row)
        self.assertIsNotNone(offer)
        self.assertEqual((offer['price_try'],offer['volume_ml']),(1650,50))

    def test_recommendation_cannot_supply_target_price_on_wrong_product_page(self):
        html=self.page().replace('<h1>Lalique Amethyst EDP 100 ml</h1>','<h1>Lalique Encre Noire EDT 100 ml</h1>')
        self.assertIsNone(self.api.parse_page(html,'https://www.perfumepoint.com.tr/encre-noire',self.row))

    def test_euro_offer_is_not_relabelled_try(self):
        o=self.api.parse_page(self.page(currency='EUR'),'https://www.perfumepoint.com.tr/amethyst',self.row)
        self.assertTrue(o is None or o.get('price_try') is None)

    def test_conflicting_brand_cannot_fall_back_to_og_price(self):
        raw=self.page(name='Amethyst EDP 100 ml').replace('"name": "Lalique"','"name": "Different Brand"')
        raw+='<meta property="product:price:currency" content="TRY"><meta property="product:price:amount" content="123">'
        self.assertIsNone(self.api.parse_page(raw,'https://www.perfumepoint.com.tr/amethyst',self.row))

    def test_retailer_name_does_not_supply_missing_product_brand(self):
        raw='<h1>Amethyst EDP 100 ml</h1><meta property="product:price:currency" content="TRY"><meta property="product:price:amount" content="123">'
        self.assertIsNone(self.api.parse_page(raw,'https://www.perfumepoint.com.tr/amethyst',self.row))

    def test_microdata_recommendation_cannot_supply_main_price(self):
        raw='<h1>Lalique Amethyst EDP 100 ml</h1><div itemscope itemtype="https://schema.org/Product"><span itemprop="name">Dior Sauvage EDT 60 ml</span><meta itemprop="price" content="999"><meta itemprop="priceCurrency" content="TRY"></div>'
        self.assertIsNone(self.api.parse_page(raw,'https://www.perfumepoint.com.tr/amethyst',self.row))

    def test_meta_fallback_requires_concentration_from_product_name(self):
        row={'brand_name':'Lalique','product_name':'Amethyst EDP'}
        raw='<h1>Lalique Amethyst</h1><meta property="product:price:currency" content="TRY"><meta property="product:price:amount" content="123">'
        self.assertIsNone(self.api.parse_page(raw,'https://www.perfumepoint.com.tr/amethyst',row))

    def test_each_offer_must_match_selected_bottle_and_url(self):
        obj={'@type':'Product','name':'Lalique Amethyst EDP 100 ml','brand':{'name':'Lalique'},'offers':[
             {'@type':'Offer','name':'50 ml','price':'100','priceCurrency':'TRY','url':'https://www.perfumepoint.com.tr/amethyst-50'},
             {'@type':'Offer','name':'100 ml','price':'200','priceCurrency':'TRY','url':'https://www.perfumepoint.com.tr/amethyst-100'}]}
        raw='<h1>Lalique Amethyst EDP 100 ml</h1><script type="application/ld+json">'+json.dumps(obj)+'</script>'
        offer=self.api.parse_page(raw,'https://www.perfumepoint.com.tr/amethyst-100',self.row)
        self.assertIsNotNone(offer)
        self.assertEqual((offer['price_try'],offer['volume_ml'],offer['purchase_url']),(200,100,'https://www.perfumepoint.com.tr/amethyst-100'))

    def test_offer_link_for_other_variant_is_not_current_page_price(self):
        raw=self.page().replace('"@type": "Offer"','"@type": "Offer", "url": "https://www.perfumepoint.com.tr/amethyst-50"')
        self.assertIsNone(self.api.parse_page(raw,'https://www.perfumepoint.com.tr/amethyst-100',self.row))

    def test_other_bottle_product_object_cannot_override_heading(self):
        raw=self.page(name='Lalique Amethyst EDP 50 ml').replace('<h1>Lalique Amethyst EDP 50 ml</h1>','<h1>Lalique Amethyst EDP 100 ml</h1>')
        self.assertIsNone(self.api.parse_page(raw,'https://www.perfumepoint.com.tr/amethyst-100',self.row))

    def test_turkey_block_overrides_offer(self):
        o=self.api.parse_page(self.page(extra='<p>This product is not salable in Turkey</p>'),'https://www.dsquared2.com/tr/p',self.row)
        self.assertIsNone(o)

    def test_unknown_extra_variant_is_rejected(self):
        self.assertFalse(self.api.matches(self.row,'Lalique Amethyst Eclat EDP 100 ml'))

    def test_fragrance_concentration_does_not_erase_eau_sauvage_name(self):
        row={'brand_name':'Dior','product_name':'Eau Sauvage','release_year':''}
        self.assertFalse(self.api.matches(row,'Dior Sauvage Eau de Parfum'))

    def test_gender_override_prevents_1923_collision(self):
        row={'brand_name':'Mad Parfumeur','product_name':'1923','gender':'male','release_year':'2025'}
        self.assertFalse(self.api.matches(row,'Mad 1923 Kadın 100 ml Parfüm'))
        self.assertTrue(self.api.matches(row,'Mad 1923 Erkek 100 ml Parfüm'))

    def test_model_code_and_descriptive_suffix_are_allowed_for_innative(self):
        row={'brand_name':'INNATIVE','product_name':'BERRY AURA (Eau de Parfum)','release_year':''}
        self.assertTrue(self.api.matches(row,'INNATIVE E2002 Eny BERRY AURA Edp 50 ml Sulu Armut Ve Taze Çiçekler Kadın Parfümü'))

    def test_two_wood_retains_product_number(self):
        row={'brand_name':'DSQUARED²','product_name':'2 Wood','release_year':'2021'}
        self.assertFalse(self.api.matches(row,'DSQUARED2 Wood EDT 100 ml'))
        self.assertTrue(self.api.matches(row,'DSQUARED2 2 Wood EDT 100 ml'))

    def test_short_names_do_not_match_longer_names(self):
        row={'brand_name':'Dolce & Gabbana','product_name':'By','release_year':''}
        self.assertFalse(self.api.matches(row,'Dolce Gabbana K By EDT 100 ml'))

    def test_price_has_correct_thousand_separator(self):
        self.assertEqual(self.api.price_number('10,900 TL'),10900)
        self.assertEqual(self.api.price_number('3.162,50 TL'),3162.5)

    def test_queries_keep_numeric_names_and_support_non_latin_names(self):
        self.assertIn('1923',self.api.queries({'brand_name':'Mad Parfumeur','product_name':'1923','release_year':'2025'})[0])
        self.assertIn('шипр',self.api.queries({'brand_name':'Северное сияние','product_name':'Шипр духи','release_year':''})[0])

    def test_ddg_redirect_is_decoded_to_product_url(self):
        html='<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Ftr.caudalie.com%2Fp%2F531.html">Caudalie Ange des Vignes</a>'
        results=self.api.search_links('ddg',html)
        self.assertEqual(results,[('Caudalie Ange des Vignes','https://tr.caudalie.com/p/531.html')])


if __name__=='__main__': unittest.main()
