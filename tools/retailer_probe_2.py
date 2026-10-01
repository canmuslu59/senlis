#!/usr/bin/env python3
import json, urllib.parse
from bs4 import BeautifulSoup
import requests

TESTS=[
 ("rossmann_ara","https://www.rossmann.com.tr/arama",{"q":"Calvin Klein Euphoria"}),
 ("rossmann_search","https://www.rossmann.com.tr/search",{"query":"Calvin Klein Euphoria"}),
 ("zara","https://www.zara.com/tr/tr/search",{"searchTerm":"Red Temptation"}),
 ("yvesrocher_search","https://www.yvesrocher.com.tr/search",{"q":"Comme une Evidence"}),
 ("yvesrocher_ara","https://www.yvesrocher.com.tr/arama",{"q":"Comme une Evidence"}),
 ("avon","https://www.avon.com.tr/search",{"text":"Far Away"}),
 ("oriflame","https://tr.oriflame.com/search",{"query":"Giordani Gold"}),
 ("bodyshop_ara","https://www.thebodyshop.com.tr/arama",{"q":"White Musk"}),
 ("bodyshop_search","https://www.thebodyshop.com.tr/search",{"q":"White Musk"}),
 ("victoriassecret","https://www.victoriassecret.com.tr/search",{"q":"Bare Vanilla"}),
 ("bathbodyworks","https://www.bathandbodyworks.com.tr/search",{"q":"Warm Vanilla Sugar"}),
 ("lush","https://www.lush.com.tr/search",{"q":"Karma"}),
 ("eveshop","https://www.eveshop.com.tr/arama",{"q":"Calvin Klein Euphoria"}),
 ("cosmetica","https://www.cosmetica.com.tr/arama",{"q":"Calvin Klein Euphoria"}),
 ("mizu","https://www.mizu.com/arama",{"q":"Calvin Klein Euphoria"}),
 ("n11","https://www.n11.com/arama",{"q":"Calvin Klein Euphoria"}),
 ("hepsiburada","https://www.hepsiburada.com/ara",{"q":"Calvin Klein Euphoria"}),
 ("trendyol","https://www.trendyol.com/sr",{"q":"Calvin Klein Euphoria"}),
 ("amazon","https://www.amazon.com.tr/s",{"k":"Calvin Klein Euphoria"}),
]
needles=["euphoria","red temptation","comme une evidence","far away","giordani","white musk","bare vanilla","warm vanilla","karma"]
s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"})

for name,url,params in TESTS:
    try:
        r=s.get(url,params=params,timeout=22,allow_redirects=True)
        soup=BeautifulSoup(r.text,"lxml")
        title=soup.title.get_text(" ",strip=True) if soup.title else ""
        hits=[]; seen=set()
        for a in soup.find_all("a",href=True):
            txt=" ".join(a.get_text(" ",strip=True).split())
            href=a.get("href","")
            low=txt.lower()
            if txt and any(n in low for n in needles):
                full=urllib.parse.urljoin(r.url,href)
                key=(txt[:160],full)
                if key not in seen:
                    seen.add(key); hits.append(key)
            if len(hits)>=8: break
        print("PROBE",json.dumps({
            "site":name,"status":r.status_code,"bytes":len(r.content),"url":r.url,
            "title":title[:180],"hits":hits
        },ensure_ascii=False),flush=True)
    except Exception as e:
        print("PROBE",json.dumps({"site":name,"error":repr(e)},ensure_ascii=False),flush=True)
