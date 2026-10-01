#!/usr/bin/env python3
import json,re
from playwright.sync_api import sync_playwright

def compact(s):
    return re.sub(r"\s+"," ",s or "").strip()

def closest_card_text(el,max_up=6):
    node=el
    best=""
    for _ in range(max_up):
        try:
            txt=compact(node.inner_text())
            if len(txt)>len(best) and len(txt)<1800: best=txt
            node=node.locator("..")
        except: break
    return best

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(locale="tr-TR",viewport={"width":1440,"height":1000})
    page.set_extra_http_headers({"Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"})

    # Zara dynamic search proof
    try:
        page.goto("https://www.zara.com/tr/tr/search?searchTerm=Red%20Temptation",wait_until="domcontentloaded",timeout=60000)
        page.wait_for_timeout(7000)
        matches=[]
        anchors=page.locator("a").all()
        seen=set()
        for a in anchors:
            try:
                txt=compact(a.inner_text())
                href=a.get_attribute("href") or ""
                hay=(txt+" "+href).lower()
                if "red temptation" not in hay: continue
                if href in seen: continue
                seen.add(href)
                matches.append({"text":txt[:300],"href":href,"card":closest_card_text(a)[:1200]})
                if len(matches)>=12: break
            except: pass
        print("ZARA_DYNAMIC",json.dumps({
            "title":page.title(),"url":page.url,"body_bytes":len(page.content()),"matches":matches,
            "body_has_term":"red temptation" in page.locator("body").inner_text().lower()
        },ensure_ascii=False),flush=True)
    except Exception as e:
        print("ZARA_ERROR",repr(e),flush=True)

    # Oriflame: expand SSR/dynamic category until no more button.
    try:
        page.goto("https://tr.oriflame.com/fragrance",wait_until="domcontentloaded",timeout=60000)
        page.wait_for_timeout(4000)
        clicks=0
        for _ in range(20):
            page.mouse.wheel(0,5000)
            page.wait_for_timeout(800)
            btn=page.get_by_text("Daha fazla göster",exact=False)
            if btn.count()==0: break
            clicked=False
            for i in range(btn.count()):
                try:
                    b=btn.nth(i)
                    if b.is_visible():
                        b.click(timeout=5000)
                        page.wait_for_timeout(1800)
                        clicks+=1; clicked=True; break
                except: pass
            if not clicked: break
        rows=[]; seen=set()
        for a in page.locator('a[href*="/products/product?code="]').all():
            try:
                href=a.get_attribute("href") or ""
                if href in seen: continue
                seen.add(href)
                txt=compact(a.inner_text())
                card=closest_card_text(a)
                rows.append({"text":txt[:350],"href":href,"card":card[:1200]})
            except: pass
        print("ORIFLAME_DYNAMIC",json.dumps({
            "title":page.title(),"url":page.url,"clicks":clicks,"products":len(rows),
            "sample":rows[:15]
        },ensure_ascii=False),flush=True)
    except Exception as e:
        print("ORIFLAME_ERROR",repr(e),flush=True)

    browser.close()
