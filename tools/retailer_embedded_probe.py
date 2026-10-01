#!/usr/bin/env python3
import json,re,html
import requests
from bs4 import BeautifulSoup

TESTS=[
 ("zara","https://www.zara.com/tr/tr/search",{"searchTerm":"Red Temptation"},["red temptation","20110"]),
 ("oriflame","https://tr.oriflame.com/search",{"query":"Giordani Gold"},["giordani","gold"]),
]
s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"})
for name,url,params,needles in TESTS:
    try:
        r=s.get(url,params=params,timeout=25,allow_redirects=True)
        raw=r.text
        low=raw.lower()
        snippets=[]
        for needle in needles:
            start=0
            for _ in range(5):
                i=low.find(needle.lower(),start)
                if i<0: break
                sn=raw[max(0,i-260):min(len(raw),i+800)]
                snippets.append({"needle":needle,"snippet":re.sub(r"\s+"," ",html.unescape(sn))[:1200]})
                start=i+len(needle)
        urls=[]
        for m in re.finditer(r'https?:\\?/\\?/[^"<> ]+',raw):
            u=m.group(0).replace("\\/","/")
            if any(n.replace(" ","").lower() in u.replace("-","").replace("_","").lower() for n in needles):
                urls.append(u[:500])
            if len(urls)>=10: break
        scripts=[]
        soup=BeautifulSoup(raw,"lxml")
        for tag in soup.find_all("script"):
            t=tag.get_text(" ",strip=True)
            if t and any(n.lower() in t.lower() for n in needles):
                scripts.append({"type":tag.get("type",""),"id":tag.get("id",""),"len":len(t),"head":re.sub(r"\s+"," ",t[:1400])})
                if len(scripts)>=5: break
        print("EMBED",json.dumps({"site":name,"status":r.status_code,"bytes":len(raw),"url":r.url,
            "snippets":snippets[:10],"urls":urls[:10],"scripts":scripts},ensure_ascii=False),flush=True)
    except Exception as e:
        print("EMBED",json.dumps({"site":name,"error":repr(e)},ensure_ascii=False),flush=True)
