import importlib.util
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
FIX=Path(__file__).parent/'fixtures'

class ParserTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('commerce_v5_parser'), 'v5 parser is missing')
        import commerce_v5_parser
        self.api=commerce_v5_parser
        self.row={'id':'1','brand_name':'Lalique','product_name':'Amethyst','concentration':'EDP'}
        self.source={'id':'test','host':'shop.example','market':'US','kind':'retailer'}
    def page(self, name='Lalique Amethyst EDP 100 ml', price='125.50', currency='USD', **kw):
        offer={'@type':'Offer','price':price,'priceCurrency':currency,'availability':'https://schema.org/InStock'};offer.update(kw)
        return '<h1>'+name+'</h1><script type="application/ld+json">'+json.dumps({'@type':'Product','name':name,'brand':{'name':'Lalique'},'offers':offer})+'</script>'
    def verify(self,raw):return self.api.verify_page(raw,'https://shop.example/p',self.row,self.source)
    def test_original_currencies_have_no_try_conversion(self):
        for cur,amount in [('USD','125.50'),('EUR','90.00'),('TRY','6500.00')]:
            r=self.verify(self.page(price=amount,currency=cur));self.assertEqual(r['reason'],'verified');o=r['offers'][0]
            self.assertEqual((o['amount'],o['currency'],o['market']),(amount,cur,'US'));self.assertNotIn('price_try',o)
    def test_money_rejects_nonfinite_and_ambiguous_currency(self):
        self.assertEqual(self.api.money('1.234,50 €','EUR'),'1234.50')
        self.assertEqual(self.api.money('1,234.50','USD'),'1234.50')
        for value in ('NaN','-1','0','5 TL'):self.assertIsNone(self.api.money(value,'USD'))
    def test_conditional_discount_is_observation_only(self):
        r=self.verify(self.page(validForMemberTier='Plus'));self.assertFalse(r['offers']);self.assertEqual(r['reason'],'conditional_price');self.assertEqual(r['observations'][0]['amount'],'125.50')
    def test_unknown_volume_retains_price_without_accepting(self):
        r=self.verify(self.page(name='Lalique Amethyst EDP'));self.assertFalse(r['offers']);self.assertEqual(r['reason'],'volume_unproven');self.assertEqual(r['observations'][0]['amount'],'125.50')
    def test_wrong_main_heading_cannot_use_recommendation_price(self):
        r=self.verify(self.page().replace('<h1>Lalique Amethyst EDP 100 ml</h1>','<h1>Lalique Encre Noire EDP 100 ml</h1>'));self.assertFalse(r['offers']);self.assertEqual(r['reason'],'name_mismatch')
    def test_wrong_brand_metadata_is_explicit_conflict(self):
        r=self.verify(self.page().replace('"name": "Lalique"','"name": "Other"'));self.assertFalse(r['offers']);self.assertEqual(r['reason'],'brand_conflict')
    def test_body_mist_is_not_edp(self):
        r=self.verify(self.page(name='Lalique Amethyst Body Mist 200 ml'));self.assertFalse(r['offers']);self.assertEqual(r['reason'],'form_mismatch')
    def test_wrong_concentration_is_not_accepted(self):
        r=self.verify(self.page(name='Lalique Amethyst EDT 100 ml'));self.assertFalse(r['offers']);self.assertEqual(r['reason'],'concentration_mismatch')
    def test_trendyol_uses_selected_seller_price_not_coupon_or_recommendation(self):
        raw=(FIX/'trendyol.html').read_text();row={'id':'77268','brand_name':'INNATIVE','product_name':'BLUE ESSENCE (Eau de Parfum)'}
        url='https://www.trendyol.com/innative/e4001-eny-blue-essence-edp-50-ml-temiz-cicekler-kadin-parfumu-p-991091641'
        src={'id':'trendyol','host':'trendyol.com','market':'TR','kind':'marketplace'}
        r=self.api.verify_page(raw,url,row,src);self.assertEqual(r['reason'],'verified');o=r['offers'][0]
        self.assertEqual((o['amount'],o['currency'],o['volume_ml'],o['seller_name'],o['seller_id']),('613.29','TRY',50.0,'INNATIVE','830391'))
        r=self.api.verify_page(raw,url.replace('991091641','991091642'),row,src);self.assertFalse(r['offers'])
    def test_official_innative_marketing_adjective_no_longer_rejects_identity(self):
        row={'id':'77268','brand_name':'INNATIVE','product_name':'BLUE ESSENCE (Eau de Parfum)'}
        url='https://innativekozmetik.com/innative-e3001-eny-nocturne-kiss-edp-50-ml-baharatlikremsi-hindistan-cevizi-kadin-parfumu-2'
        r=self.api.verify_page((FIX/'77268.html').read_text(),url,row,{'id':'innative','host':'innativekozmetik.com','market':'TR','kind':'official','brand':'INNATIVE'})
        self.assertEqual(r['reason'],'verified');self.assertEqual(r['offers'][0]['amount'],'450.00')
    def test_actual_wrong_brand_stays_unverified_but_has_reason_and_price(self):
        row={'id':'2440','brand_name':'Abercrombie & Fitch','product_name':'Authentic Moment Man'}
        r=self.api.verify_page((FIX/'2440.html').read_text(),'https://yesparfumeri.com/products/abercrombie-fitch-authentic-moment-men-edt-100-ml-erkek-parfum',row,{'id':'yes','host':'yesparfumeri.com','market':'TR','kind':'retailer'})
        self.assertFalse(r['offers']);self.assertEqual(r['reason'],'brand_conflict');self.assertEqual(r['observations'][0]['amount'],'6900.00')
    def test_productgroup_selected_size_not_other_variant(self):
        url='https://fr.caudalie.com/p/528R1C/the-des-vignes-eau-fraiche-528r1c.html'
        r=self.api.verify_page((FIX/'caudalie_fr.html').read_text(),url,{'id':'1','brand_name':'Caudalie','product_name':'The des Vignes'}, {'id':'caudalie_fr','host':'fr.caudalie.com','market':'FR','kind':'official','brand':'Caudalie'})
        self.assertEqual(r['reason'],'verified');o=r['offers'][0];self.assertEqual((o['amount'],o['currency'],o['volume_ml']),('29.50','EUR',100.0));self.assertIn('MjE5=',o['purchase_url'])
    def test_shopify_variant_requires_selected_input_and_matching_volume(self):
        raw=self.page(url='https://shop.example/p?variant=42')+'<input name="id" value="42">'
        self.assertEqual(self.verify(raw)['reason'],'verified')
        self.assertFalse(self.verify(raw.replace('value="42"','value="43"'))['offers'])
    def test_unknown_source_and_cross_host_redirect_are_not_verified(self):
        self.assertFalse(self.api.verify_page(self.page(),'https://other.example/p',self.row,self.source)['offers'])
    def test_decant_and_dupe_are_rejected(self):
        for tag in ('dekant','muadili'):
            self.assertFalse(self.verify(self.page(name='Lalique Amethyst EDP 100 ml '+tag))['offers'])

    def test_secondary_product_identifier_cannot_lend_lower_price(self):
        raw=self.page()+ '<script type="application/ld+json">'+json.dumps({'@type':'Product','@id':'https://shop.example/other','name':'Lalique Amethyst EDP 100 ml','brand':{'name':'Lalique'},'offers':{'price':'9','priceCurrency':'USD'}})+'</script>'
        r=self.verify(raw);self.assertNotIn('9.00',[o['amount'] for o in r['offers']])
    def test_explicit_group_selection_conflict_cannot_be_overridden(self):
        raw=self.page(url='https://shop.example/p?variant=42').replace('"@type": "Product"','"@type": "ProductGroup", "@id": "https://shop.example/p?variant=42#ProductGroup"')+'<input name="id" value="43">'
        r=self.api.verify_page(raw,'https://shop.example/p?variant=43',self.row,self.source);self.assertFalse(r['offers'])
    def test_ambiguous_edition_needs_independent_release_evidence(self):
        row=dict(self.row,release_year='2005',competing_release_years=['2005','2019'])
        r=self.api.verify_page(self.page(),'https://shop.example/p',row,self.source)
        self.assertFalse(r['offers']);self.assertEqual(r['reason'],'identity_ambiguous')
        raw=self.page().replace('"@type": "Product"','"@type": "Product", "releaseDate": "2005-01-01"')
        self.assertEqual(self.api.verify_page(raw,'https://shop.example/p',row,self.source)['reason'],'verified')
    def test_textual_member_cart_coupon_prices_are_not_plain_offers(self):
        for description in ('Price for members only','Price with coupon','Sepette indirimli fiyat'):
            r=self.verify(self.page(description=description));self.assertFalse(r['offers']);self.assertEqual(r['reason'],'conditional_price')
    def test_formatted_turkish_thousands_does_not_become_one_lira(self):
        self.assertEqual(self.api.money('1.234 TL','TRY'),'1234.00')
        self.assertEqual(self.api.money('1.234.567 TL','TRY'),None)

if __name__=='__main__':unittest.main()
