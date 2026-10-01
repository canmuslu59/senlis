#!/usr/bin/env python3
import json, urllib.parse, re
import requests
from bs4 import BeautifulSoup

TESTS=[
 ("zara_women","https://www.zara.com/tr/tr/kadin-aksesuarlar-parfemler-l1017.html"),
 ("oriflame","https://tr.oriflame.com/fragrance"),
 ("yvesrocher","https://www.yvesrocher.com.tr/parfum/c/30000"),
 ("vs_perfume","https://www.victoriassecret.com.tr/vs/parfum"),
 ("vs_mist","https://www.victoriassecret.com.tr/vs/fragrance-vucut-spreyleri"),
 ("bbw","https://www.bathandbodyworks.com.tr/tum-vucut-spreyleri-ve-parfumler"),
]
KEYS=["parfum","parfüm","eau de","body mist","vücut spreyi","mist","edp","edt","fragrance"]
s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"})

for name,url in TESTS:
    try:
        r=s.get(url,timeout=25,allow_redirects=True)
        soup=BeautifulSoup(r.text,"lxml")
        links=[]; seen=set()
        for a in soup.find_all("a",href=True):
            txt=" ".join(a.get_text(" ",strip=True).split())
            href=urllib.parse.urljoin(r.url,a.get("href",""))
            low=(txt+" "+href).lower()
            if txt and any(k in low for k in KEYS):
                key=(txt[:180],href)
                if key not in seen:
                    seen.add(key); links.append(key)
            if len(links)>=30: break
        # Also inspect product JSON-LD counts.
        product_json=0
        for tag in soup.find_all("script",attrs={"type":"application/ld+json"}):
            t=tag.get_text(" ",strip=True)
            if '"Product"' in t or '"@type":"Product"' in t or '"@type": "Product"' in t:
                product_json+=1
        text=" ".join(soup.get_text(" ",strip=True).split())
        prices=re.findall(r"(?:₺\s*|)(\d{1,3}(?:[.]\d{3})*(?:,\d{2})?)\s*(?:TL|₺)",text)[:20]
        print("CATALOG",json.dumps({"site":name,"status":r.status_code,"bytes":len(r.content),"url":r.url,
          "title":soup.title.get_text(" ",strip=True)[:160] if soup.title else "",
          "links":links,"jsonld_products":product_json,"price_samples":prices},ensure_ascii=False),flush=True)
    except Exception as e:
        print("CATALOG",json.dumps({"site":name,"error":repr(e)},ensure_ascii=False),flush=True)
