# regression rerun after accent-scope fix
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core
from image_sources import clean_source_url,first_image_url,fragrantica_image,normalize_image

CASES=[
 ("reject","Bath & Body Works","Cherry Blossom","Bath & Body Works Japanese Cherry Blossom / Parfüm"),
 ("reject","Victoria's Secret","Bombshell Eau de Parfum","Victoria's Secret Bombshell Bronze Eau de Parfum"),
 ("reject","Victoria's Secret","Tease Eau de Parfum","Victoria's Secret Tease Sugar Fleur Seyahat Boyu Eau De Parfum"),
 ("reject","Victoria's Secret","Very Sexy","Victoria's Secret Very Sexy Scarlet Eau de Parfum"),
 ("reject","Victoria's Secret","Very Sexy Eau de Parfum","Victoria's Secret Very Sexy Euphoric Eau de Parfum 50 ml"),
 ("reject","Oriflame","Giordani Gold Essenza (Parfum)","Oriflame Giordani Gold Essenza Supreme Vücut ve Saç Parfüm Misti"),
 ("reject","Oriflame","Eclat Femme","Oriflame Eclat Femme Weekend EdT"),
 ("reject","Oriflame","Amber Elixir","Oriflame Amber Elixir Mystery EdP"),
 ("accept","Victoria's Secret","Bombshell Eau de Parfum","Victoria's Secret Bombshell Eau de Parfum"),
 ("accept","Victoria's Secret","Very Sexy Night","Victoria's Secret Very Sexy Night Eau de Parfum"),
 ("accept","Oriflame","Amber Elixir Mystery","Oriflame Amber Elixir Mystery EdP"),
 ("accept","Oriflame","Eclat Homme","Oriflame Eclat Homme EdT"),
 ("accept","Calvin Klein","Euphoria (Eau de Parfum)","Calvin Klein Euphoria EDP 100 ml Kadın Parfüm"),
 ("reject","Calvin Klein","Deep Euphoria (Eau de Parfum)","Calvin Klein Euphoria EDP 100 ml Kadın Parfüm"),
 ("accept","Dior","Sauvage Eau de Parfum","Dior Sauvage Eau de Parfum refillable Eau de Parfum - citrus and vanilla notes"),
 ("accept","Tom Ford","Oud Wood","Tom Ford Oud Wood EDP 50 ml Parfüm"),
 ("accept","Versace","Eros (Eau de Parfum)","Versace Eros EDP 50 ml Erkek Parfüm"),
 ("reject","Versace","Eros (Eau de Parfum)","Versace Eros Pour Femme EDP 100 ml Kadın Parfüm"),
 ("reject","Victoria's Secret","Bombshell Isle Victoria's Secret Fragrance Mist (Body Mist)","Victoria's Secret Bombshell Mini Vücut Spreyi"),
 ("reject","Victoria's Secret","Coco Mist Victoria's Secret Fragrance Mist (Body Mist)","Victoria's Secret Bombshell Mini Vücut Spreyi"),
 ("reject","Victoria's Secret","Eau So Sexy Victoria's Secret Fragrance Mist","Victoria's Secret Very Sexy Vücut Spreyi"),
 ("reject","Victoria's Secret","Pure Seduction Victoria's Secret Fragrance Mist","Victoria's Secret Bombshell Seduction Seyahat Boy Vücut Spreyi"),
 ("reject","Victoria's Secret","Vanilla Lace Victoria's Secret Fragrance Mist","Victoria's Secret Bare Sueded Vanilla Vücut Spreyi"),
 ("reject","Victoria's Secret","XO, Victoria Victoria's Secret Fragrance Mist (Body Mist)","Victoria's Secret Bombshell Mini Vücut Spreyi"),
 ("reject","Victoria's Secret","Bombshell Intense Victoria's Secret Fragrance Mist","Victoria's Secret Bombshell Intense Seyahat Boyu Vücut Spreyi"),
 ("reject","Oriflame","Giordani Gold Essenza Oriflame Body Spray","Oriflame Giordani Gold Essenza Supreme Vücut ve Saç Parfüm Misti"),
 ("accept","Bath & Body Works","Bourbon Bath & Body Works Body Spray (Body Mist)","Bath & Body Works Bourbon / Vücut Spreyi"),
 ("accept","Bath & Body Works","Force Flow Body Spray (Body Mist)","Bath & Body Works Force Flow / Vücut Spreyi"),
 ("accept","Giorgio Armani","Acqua di Gio Parfum","Giorgio Armani GA Acqua di Gio Parfum 100ml"),
 ("accept","Lancôme","Idôle Eau de Parfum","Lancome Idole EDP 50 ml"),
 ("accept","Hermès","Terre d'Hermès Eau de Toilette","Hermes Terre d Hermes EDT 100 ml"),
 ("accept","Chloé","Chloé Eau de Parfum","Chloe Chloe EDP 50 ml"),
 ("reject","Dior","Eau Sauvage","Dior Sauvage Eau de Parfum"),
 ("reject","Yves Saint Laurent","Libre","Yves Saint Laurent Eau Libre"),
 ("accept","Alix Avien","Eau De Etoil","Alix Avien Eau De Etoil EDP"),
 ("reject","Giorgio Armani","Acqua di Gio","Giorgio Armani Acqua di Gioia Eau de Parfum"),
 ("reject","Dior","Sauvage Elixir","Dior Sauvage Eau de Parfum"),
 ("reject","Versace","Eros Flame","Versace Eros Eau de Parfum"),
 ("accept","Dolce & Gabbana","Light Blue","Dolce Gabbana Light Blue EDT 100 ml"),
 ("accept","Giorgio Armani","Acqua di Gio","Giorgio Armani Acqua di Gio EDT 100 ml"),
]

bad=[]
for expected,brand,product,candidate in CASES:
    got=core.variant_compatible(brand,product,candidate);want=expected=="accept"
    print(("PASS" if got==want else "FAIL"),expected,brand,"|",product,"|",candidate,"=>",got)
    if got!=want:bad.append((expected,brand,product,candidate,got))
if bad:
    print("REGRESSION_FAILURES",len(bad))
    for x in bad:print("BAD",x)
    raise SystemExit(1)

helpers=0
assert core.norm("Lancôme Idôle Hermès Chloé")=="lancome idole hermes chloe";helpers+=1
assert core.match_norm("Eau de Parfum 60ml")=="edp 60 ml";helpers+=1
assert core.parse_try_price("1.299")==1299.0;helpers+=1
assert core.parse_try_price("1.299,90 TL")==1299.9;helpers+=1
assert core.visible_price("500 TL ve üzeri alışverişe kupon. Ürün 1.299 TL","Ürün")==1299.0;helpers+=1
assert core.volume_ml("Acqua di Gio 50 ml","önerilen 100 ml")==50.0;helpers+=1
assert "giorgio armani acqua di gio" in core.slug_title("https://www.beymen.com/tr/p_giorgio-armani-acqua-di-gio-parfum-100ml_1526190");helpers+=1
assert clean_source_url("https://www.fragrantica.com/perfume/X/Y-79082.html1001","1000").endswith(".html");helpers+=1
assert fragrantica_image("https://www.fragrantica.com/perfume/X/Y-79082.html").endswith("375x500.79082.jpg");helpers+=1
assert first_image_url({"type":"ImageObject","contentUrl":["https://x/a.jpg","https://x/b.jpg"]})=="https://x/a.jpg";helpers+=1
assert "/perfumes/" in normalize_image("https://media.parfumo.com/perfume_social/a-b-c_1200.jpg");helpers+=1
assert core.commerce_in_scope({"brand_name":"Lancôme","source_url":"https://example.com/x"}) is True;helpers+=1
print("HELPERS_OK",helpers)

class NoNetwork:
    def get(self,*args,**kwargs):raise RuntimeError("network access attempted for indexed product")
indexed_row={"id":"121536","brand_name":"Oriflame","product_name":"Amber Elixir Mystery","release_year":"","source_url":""}
indexed=core.extract_commerce(NoNetwork(),indexed_row)
assert indexed["commerce_status"]=="verified",indexed
assert float(indexed["price_try"])==1199.0,indexed
assert indexed["seller_name"]=="tr.oriflame.com",indexed
assert "code=35681" in indexed["purchase_url"],indexed
print("STATIC_INDEX_OK",indexed["price_try"],indexed["seller_name"],indexed["purchase_url"])
print("REGRESSION_OK",len(CASES))
