#!/usr/bin/env python3
# trigger retailer probe after workflow install
import json, urllib.parse
from bs4 import BeautifulSoup
import requests

SITES=[
 ("sephora","https://www.sephora.com.tr/search",{"q":"Dior Sauvage Eau de Parfum"}),
 ("sevil","https://www.sevil.com.tr/search",{"q":"Dior Sauvage Eau de Parfum"}),
 ("rossmann","https://www.rossmann.com.tr/search",{"q":"Calvin Klein Euphoria"}),
 ("watsons","https://www.watsons.com.tr/search",{"q":"Calvin Klein Euphoria"}),
 ("gratis","https://www.gratis.com/search",{"q":"Calvin Klein Euphoria"}),
 ("beymen","https://www.beymen.com/tr/search",{"q":"Tom Ford Oud Wood"}),
 ("boyner","https://www.boyner.com.tr/search",{"q":"Tom Ford Oud Wood"}),
]
s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"})
for name,url,params in SITES:
    try:
        r=s.get(url,params=params,timeout=20,allow_redirects=True)
        soup=BeautifulSoup(r.text,"lxml")
        title=soup.title.get_text(" ",strip=True) if soup.title else ""
        links=[]
        for a in soup.find_all("a",href=True):
            txt=" ".join(a.get_text(" ",strip=True).split())
            href=a.get("href","")
            if txt and any(k in txt.lower() for k in ["sauvage","euphoria","oud wood"]):
                links.append((txt[:180],urllib.parse.urljoin(r.url,href)))
            if len(links)>=8: break
        print("PROBE",json.dumps({"site":name,"status":r.status_code,"bytes":len(r.content),"url":r.url,"title":title[:160],"hits":links},ensure_ascii=False),flush=True)
    except Exception as e:
        print("PROBE",json.dumps({"site":name,"error":repr(e)},ensure_ascii=False),flush=True)
