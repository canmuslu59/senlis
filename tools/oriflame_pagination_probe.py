#!/usr/bin/env python3
import json,re,urllib.parse
import requests
from bs4 import BeautifulSoup

s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"})
for start in [0,7,8,14,16,21,24,28,35,42,49,56,63,70,77]:
    params={} if start==0 else {"from":str(start)}
    try:
        r=s.get("https://tr.oriflame.com/fragrance",params=params,timeout=20,allow_redirects=True)
        soup=BeautifulSoup(r.text,"lxml")
        items=[]
        for a in soup.find_all("a",href=True):
            href=urllib.parse.urljoin(r.url,a.get("href",""))
            if "/products/product?code=" not in href: continue
            txt=" ".join(a.get_text(" ",strip=True).split())
            m=re.search(r"code=(\d+)",href)
            if m: items.append((m.group(1),txt[:100]))
        uniq=[]
        seen=set()
        for x in items:
            if x[0] not in seen:
                seen.add(x[0]); uniq.append(x)
        print("PAGE",json.dumps({"from":start,"status":r.status_code,"count":len(uniq),"codes":[x[0] for x in uniq],"first":uniq[:3]},ensure_ascii=False),flush=True)
    except Exception as e:
        print("PAGE",json.dumps({"from":start,"error":repr(e)},ensure_ascii=False),flush=True)
