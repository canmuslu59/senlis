"""Conservative main-product evidence, preserving original currencies and rejections."""
from decimal import Decimal, InvalidOperation
import json
import re
from urllib.parse import parse_qs, urljoin, urlsplit
from bs4 import BeautifulSoup
import commerce_v3_engine as v3
from commerce_evidence_v4 import listing_kind
from commerce_v3_http import host, public_url

CURRENCIES={'TRY','EUR','USD'}
INNATIVE_ADJECTIVES=set('temiz kremsi hindistan cevizi cicek cicekler ciceksi meyveli odunsu oryantal aromatik baharatli taze turunc notali yumusak'.split())


def money(value, currency):
    currency=str(currency).upper()
    if currency not in CURRENCIES or isinstance(value,bool):return None
    text=str(value or '').strip().replace('\u00a0','').replace('\u202f','').replace(' ','')
    tokens={'TRY':('TRY','TL','₺'),'EUR':('EUR','€'),'USD':('USD','$')}
    formatted=any(re.search(re.escape(token),text,re.I) for token in tokens[currency])
    for token in tokens[currency]:text=re.sub(re.escape(token),'',text,flags=re.I)
    if not re.fullmatch(r'\d+(?:[.,]\d+)*',text):return None
    if ',' in text and '.' in text:
        decimal=',' if text.rfind(',')>text.rfind('.') else '.'
        text=text.replace('.' if decimal==',' else ',','').replace(decimal,'.')
    elif ',' in text:
        parts=text.split(',')
        if len(parts)==2 and len(parts[1]) in (1,2):text='.'.join(parts)
        elif all(len(x)==3 for x in parts[1:]):text=''.join(parts)
        else:return None
    elif text.count('.')>1 or (formatted and re.fullmatch(r'\d{1,3}\.\d{3}',text)):
        parts=text.split('.')
        if not all(len(x)==3 for x in parts[1:]):return None
        text=''.join(parts)
    try:
        amount=Decimal(text)
        if not amount.is_finite() or not Decimal('0')<amount<=Decimal('1000000'):return None
        return str(amount.quantize(Decimal('0.01')))
    except InvalidOperation:return None


def primary_objects(soup):
    out=[]
    def walk(obj):
        if isinstance(obj,list):
            for item in obj:walk(item)
        elif isinstance(obj,dict):
            types=obj.get('@type',[]);types=[types] if isinstance(types,str) else types
            if set(types)&{'Product','ProductGroup'}:
                if obj.get('offers'):out.append(obj)
                # A ProductGroup's own offer names its selected size. Its siblings
                # cannot lend that amount to another variant.
                if not obj.get('offers'):walk(obj.get('hasVariant',[]))
            walk(obj.get('@graph',[]));walk(obj.get('mainEntity',[]))
    for script in soup.select('script[type="application/ld+json"]'):
        try:walk(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError):pass
    return out


def window_json(soup,key):
    pattern=re.compile(r'window\[([\"\'])'+re.escape(key)+r'\1\]\s*=\s*')
    for script in soup.find_all('script'):
        text=script.string or '';match=pattern.search(text)
        if match:
            try:return json.JSONDecoder().raw_decode(text[match.end():])[0]
            except (ValueError,TypeError):pass
    return None


def cleaned_name(text):
    text=v3.canonical(text)
    for phrase in ('fresh fragrance','eau fraiche','aromali parfum parfumler'):
        text=re.sub(r'\b'+phrase+r'\b',' ',text)
    return ' '.join(text.split())


def identity_reason(row,title,brand_evidence=False):
    brand=row.get('brand_name','');text=cleaned_name(title)
    has_brand=any(' '+a+' ' in ' '+text+' ' for a in v3.brand_aliases(brand))
    if not has_brand and not brand_evidence:return 'brand_unproven'
    if not has_brand:text=brand+' '+text
    product=row.get('product_name','')
    if not v3.core.form_compatible(product,text):return 'form_mismatch'
    if v3.core.special_format(product)!=v3.core.special_format(text):return 'format_mismatch'
    if v3.core.is_travel_format(product)!=v3.core.is_travel_format(text):return 'format_mismatch'
    wanted=(row.get('concentration') or v3.concentration(product)).lower();got=v3.concentration(text)
    if wanted and got and wanted!=got:return 'concentration_mismatch'
    wanted_gender=row.get('gender') or v3.gender(product);got_gender=v3.gender(text)
    if wanted_gender and got_gender and wanted_gender!=got_gender:return 'gender_mismatch'
    expected=set(v3.name_tokens(row,cleaned_name(product)));actual=set(v3.name_tokens(row,text))
    if not expected:expected={v3.norm(brand)};actual=actual or expected
    if not expected<=actual:return 'name_mismatch'
    if (actual&v3.VARIANTS)-(expected&v3.VARIANTS):return 'variant_mismatch'
    safe=v3.SAFE | (INNATIVE_ADJECTIVES if v3.norm(brand)=='innative' else set())
    extras=actual-expected-safe
    if any(not re.fullmatch('[a-z]+[0-9]+',word) for word in extras):return 'name_mismatch'
    return ''


def offer_url_matches(url,offer_url,obj,offer,soup):
    if not public_url(offer_url) or host(offer_url)!=host(url):return False
    a,b=v3.product_url_key(url),v3.product_url_key(offer_url)
    if a[:2]!=b[:2]:return False
    aq,bq=dict(a[2]),dict(b[2])
    selected={n.get('value') for n in soup.select('input[name="id"][value]')}
    if aq and aq!=bq:return False
    if 'variant' in bq and selected and selected!={bq['variant']}:return False
    if a==b:return True
    if not aq and set(bq)=={'variant'}:
        selected={n.get('value') for n in soup.select('input[name="id"][value]')}
        return selected=={bq['variant']}
    if host(url)=='innativekozmetik.com' and not aq and set(bq)=={'vid'}:
        offers=obj.get('offers',[]);offers=offers if isinstance(offers,list) else [offers]
        return len(offers)==1 and str(obj.get('productId') or '')==bq['vid']
    # A ProductGroup may expose a selected variant URL in its own identity.
    obj_id=str(obj.get('@id') or '').split('#')[0]
    h=soup.find('h1');page_volume=v3.volume(h.get_text(' ',strip=True)) if h else None
    return (not aq and obj.get('@type')=='ProductGroup' and bool(obj_id)
            and v3.product_url_key(obj_id)==b and page_volume is not None
            and page_volume==v3.volume(str(obj.get('name',''))))


def trendyol_product(soup,url):
    state=window_json(soup,'__envoy__SHARED_PROPS') or {};p=state.get('product',{})
    match=re.search(r'-p-(\d+)(?:/|$)',urlsplit(url).path)
    if not match or str(p.get('id'))!=match.group(1):return None,'page_identity_mismatch'
    listing=p.get('merchantListing',{});winner=listing.get('winnerVariant',{});merchant=listing.get('merchant',{})
    selected=[v for v in listing.get('variants',[]) if v.get('isSelected') is True]
    if len(selected)!=1 or selected[0].get('itemNumber')!=winner.get('itemNumber'):return None,'selected_variant_unproven'
    price=winner.get('price',{});name=str(p.get('brand',{}).get('name',''))+' '+str(p.get('name',''))
    vol=v3.volume(p.get('slicingAttributes',{}).get('Volume',''))
    if vol and v3.volume(name) and vol!=v3.volume(name):return None,'volume_conflict'
    offer={'@type':'Offer','price':price.get('sellingPrice',{}).get('value'),'priceCurrency':price.get('currency'),
           'url':url,'availability':'https://schema.org/InStock' if winner.get('inStock') is True and winner.get('sellable') is True else 'https://schema.org/OutOfStock',
           'seller':{'name':merchant.get('name'),'identifier':str(merchant.get('id') or '')}}
    return {'@type':'Product','name':name,'brand':p.get('brand',{}),'offers':offer,'size':str(vol)+' ml' if vol else '',
            'sku':str(p.get('id')),'price_source':'trendyol_selected_seller','barcode':winner.get('barcode')},''


def verify_page(raw,url,row,source):
    result={'reason':'price_unproven','offers':[],'observations':[]}
    def reject(reason):result['reason']=reason;return result
    if not source or not public_url(url) or host(url)!=source.get('host'):return reject('unapproved_source')
    kind=listing_kind(raw,url)
    if kind in ('dupe','decant'):return reject(kind)
    soup=BeautifulSoup(raw,'lxml');h=soup.find('h1');heading=h.get_text(' ',strip=True) if h else ''
    objects=primary_objects(soup)
    if host(url)=='trendyol.com':
        obj,error=trendyol_product(soup,url)
        if error:return reject(error)
        objects=[obj]
    if not objects:return reject('main_product_data_missing')
    objects=list({json.dumps(o,sort_keys=True):o for o in objects}.values())
    reasons=[]
    for obj in objects:
        name=str(obj.get('name') or heading);brand=obj.get('brand',{})
        if isinstance(brand,dict):brand=brand.get('name','')
        explicit=isinstance(brand,str) and bool(brand.strip());agrees=explicit and v3.norm(brand) in v3.brand_aliases(row['brand_name'])
        official=source.get('kind')=='official' and v3.norm(source.get('brand'))==v3.norm(row['brand_name'])
        brand_proven=agrees or official
        reason='brand_conflict' if explicit and not agrees else ''
        identifiers=[str(obj[k]).split('#')[0] for k in ('url','@id') if isinstance(obj.get(k),str) and obj[k].startswith(('http://','https://','/'))]
        if any(not offer_url_matches(url,urljoin(url,u),obj,{},soup) for u in identifiers):reason=reason or 'main_product_identifier_mismatch'
        if not identifiers and len(objects)>1:reason=reason or 'main_product_unproven'
        if len(row.get('competing_release_years',[]))>1:
            release=str(obj.get('releaseDate') or '')[:4]
            if not release or release!=str(row.get('release_year') or ''):reason=reason or 'identity_ambiguous'
        page_heading=heading
        category=obj.get('category')
        if isinstance(category,str) and v3.norm(page_heading)==v3.norm(category+' '+name):page_heading=name
        if not reason:reason=identity_reason(row,page_heading or name,brand_proven)
        if not reason:reason=identity_reason(row,name,brand_proven)
        if not heading and len(objects)>1:reason=reason or 'main_product_unproven'
        vols={v for v in (v3.volume(name),v3.volume(page_heading),v3.volume(str(obj.get('size','')))) if v}
        selected={v3.volume(n.get_text(' ',strip=True)) for n in soup.select('p.selected,option[selected],[data-selected="true"]') if re.fullmatch(r'\s*\d+(?:[.,]\d+)?\s*ml\s*',n.get_text(' ',strip=True),re.I)}
        vols|={v for v in selected if v}
        if len(vols)>1:reason=reason or 'volume_conflict'
        volume=next(iter(vols)) if len(vols)==1 else None
        wanted=(row.get('concentration') or v3.concentration(row['product_name'])).lower()
        got=v3.concentration(name+' '+page_heading)
        if not got:
            desc=str(obj.get('description',''))+' '+' '.join(n.get_text(' ',strip=True) for n in soup.select('.product-description,.html-content,[itemprop="description"]'))
            types=set(re.findall(r'\b(edp|edt|edc|extrait)\b',v3.canonical(desc)))
            if len(types)==1:got=next(iter(types))
        if wanted and wanted!=got:reason=reason or 'concentration_unproven'
        offers=obj.get('offers',[]);offers=offers if isinstance(offers,list) else [offers]
        for offer in offers:
            if not isinstance(offer,dict):continue
            why=reason;spec=offer.get('priceSpecification',{});spec=spec if isinstance(spec,dict) else {}
            cur=str(offer.get('priceCurrency') or spec.get('priceCurrency') or '').upper();cur={'TL':'TRY','₺':'TRY'}.get(cur,cur)
            amount=money(offer.get('price',spec.get('price')),cur)
            if not amount:
                reasons.append(why or ('currency_unsupported' if cur not in CURRENCIES else 'price_unproven'));continue
            seller=offer.get('seller',{});seller={'name':seller} if isinstance(seller,str) else seller
            seller=seller if isinstance(seller,dict) else {}
            purchase=urljoin(url,str(offer.get('url') or url))
            if not offer_url_matches(url,purchase,obj,offer,soup):why=why or 'offer_url_mismatch'
            offer_volume=v3.volume(str(offer.get('name','')))
            if offer_volume and volume!=offer_volume:why=why or 'volume_conflict'
            if any(o.get(k) for o in (offer,spec) for k in ('eligibleCustomerType','validForMemberTier','eligibleQuantity','eligibleTransactionVolume')):why=why or 'conditional_price'
            condition_text=v3.norm(' '.join(str(o.get(k) or '') for o in (offer,spec) for k in ('name','description')) )
            if re.search(r'\b(member(?:s)? only|member price|with coupon|coupon required|sepette|kupon|uyelere|uye fiyati|subscription|subscribe|auto replenishment|abonelik|ty plus)\b',condition_text):why=why or 'conditional_price'
            if not volume:why=why or 'volume_unproven'
            availability=str(offer.get('availability','')).lower()
            stock='out_of_stock' if 'outofstock' in availability or 'soldout' in availability else 'in_stock' if 'instock' in availability else 'unknown'
            observation={'amount':amount,'currency':cur,'market':source.get('market','unknown'),'volume_ml':volume,
                         'stock_status':stock,'purchase_url':purchase,'source_product_name':name,'source_id':source['id'],
                         'seller_name':seller.get('name') or host(url),'seller_id':str(seller.get('identifier') or ''),
                         'price_source':obj.get('price_source','main_product_jsonld'),'checkout_verified':False,
                         'reason':why or 'verified'}
            result['observations'].append(observation)
            if not why:result['offers'].append(dict(observation))
            else:reasons.append(why)
    result['reason']='verified' if result['offers'] else (reasons[0] if reasons else 'price_unproven')
    return result
