#!/usr/bin/env python3
"""All-row named-catalogue queries and a deduplicated, resumable page queue."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time
from urllib.parse import unquote, urlsplit

from commerce_evidence_v4 import SOURCES, Evidence, verify_listing, utc, search_proven
from commerce_v3_engine import canonical, norm, name_tokens, brand_aliases
from commerce_v3_http import PoliteClient, host
from commerce_full_v3 import load_rows, TOTAL
from commerce_v4_state import GitCheckpoint, read_jsonl, write_jsonl, read_checks, write_batch

VERSION = 'v4.1-catalogue-evidence'
MAX_ATTEMPTS = 3


def validated_rows(rows, overrides):
    """Repair legacy chunk-boundary duplication only with the next row as proof."""
    by_id = {r['id']:r for r in rows}; cleaned = []; warnings = []
    for original in rows:
        row = dict(original)
        if None in row:
            next_id = str(int(row['id'])+1); following = by_id.get(next_id)
            expected = [following.get(k) for k in ('brand_name','product_name','release_year','source_url')] if following else None
            if row[None] != expected or not row.get('source_url','').endswith(next_id):
                raise ValueError('unexplained manifest overflow at '+row['id'])
            row.pop(None); row['source_url'] = row['source_url'][:-len(next_id)]
            warnings.append({'product_id':row['id'],'repair':'duplicated_next_row_at_chunk_boundary','next_id':next_id})
        row.update(overrides.get(row['id'], {})); cleaned.append(row)
    return cleaned, warnings


class CatalogueIndex:
    def __init__(self, source, report, entries):
        self.source, self.report, self.entries = source, report, entries
        self.tokens = defaultdict(set); self.texts = []; self.brands = {}
        for i, entry in enumerate(entries):
            text = ' '+canonical(' '.join(entry.get('titles', []))+' '+unquote(urlsplit(entry['url']).path))+' '
            self.texts.append(text)
            for token in set(text.split()): self.tokens[token].add(i)

    def search(self, row):
        brand = row['brand_name']
        if self.source['brand'] and norm(self.source['brand']) != norm(brand): return []
        if brand not in self.brands:
            possible = set()
            if self.source['brand']: possible.update(range(len(self.entries)))
            else:
                for alias in brand_aliases(brand):
                    sets = [self.tokens.get(t, set()) for t in alias.split()]
                    indices = set.intersection(*sets) if sets else set()
                    possible.update(i for i in indices if ' '+alias+' ' in self.texts[i])
            self.brands[brand] = possible
        terms = set(name_tokens(row, row['product_name'])) or set(canonical(row['product_name']).split())
        if not terms: return []
        result = self.brands[brand].copy()
        for term in terms: result.intersection_update(self.tokens.get(term, set()))
        return [self.entries[i] for i in sorted(result)]


def build_plan(rows, catalogues):
    if not catalogues or any(not report.get('complete') for _, report, _ in catalogues):
        raise ValueError('incomplete source catalogue blocks full scan')
    indices = [CatalogueIndex(*catalogue) for catalogue in catalogues]
    queries = []; pages = {}
    for row in rows:
        audits = []
        for index in indices:
            source, report = index.source, index.report
            if source['brand'] and norm(source['brand']) != norm(row['brand_name']): continue
            matches = index.search(row)
            audits.append({'source_id': source['id'], 'complete': True,
                'searched_entries': len(index.entries), 'catalogue_sha256': report['catalogue_sha256'],
                'query_brand': row['brand_name'], 'query_name': row['product_name'],
                'query_tokens': sorted(set(name_tokens(row, row['product_name'])) or set(canonical(row['product_name']).split())),
                'matched_urls': [entry['url'] for entry in matches], 'match_count': len(matches)})
            for entry in matches:
                page = pages.setdefault(entry['url'], {'url': entry['url'], 'source_id': source['id'], 'product_ids': []})
                page['product_ids'].append(str(row['id']))
        queries.append({'product_id': str(row['id']), 'identity': row, 'search_proven': search_proven(audits),
                        'search_audits': audits})
    if not all(q['search_proven'] for q in queries): raise ValueError('unproven query blocks full scan')
    # Interleave hosts so a site cooldown does not block unrelated sources.
    groups = defaultdict(list)
    for page in sorted(pages.values(), key=lambda p: p['url']): groups[host(page['url'])].append(page)
    ordered = []
    for i in range(max((len(g) for g in groups.values()), default=0)):
        ordered.extend(group[i] for group in groups.values() if i < len(group))
    return {'queries': queries, 'pages': ordered}


def eligible(check, now):
    return not check or (not check.get('final') and check.get('retry_at', 0) <= now)


def product_result(query, checks):
    urls = list(dict.fromkeys(u for a in query['search_audits'] for u in a['matched_urls']))
    offers = [d['offer'] for url in urls for d in checks.get(url, {}).get('decisions', [])
              if d['product_id'] == query['product_id'] and d.get('offer')]
    completed = all(checks.get(url, {}).get('final') for url in urls)
    failed = any(checks.get(url, {}).get('final') and not checks[url].get('success') for url in urls)
    status = ('verified_offer' if offers else 'no_catalog_match' if not urls else
              'pending_pages' if not completed else 'page_unavailable' if failed else 'no_accepted_offer')
    result = {'product_id': query['product_id'], **{k:query['identity'].get(k, '') for k in ('brand_name','product_name','release_year')},
              'status': status, 'search_proven': query['search_proven'], 'verification_complete': completed and not failed,
              'scope': 'named_source_product_catalogues_only', 'method_version': VERSION,
              'candidate_count': len(urls), 'offers': offers, 'search_audits': query['search_audits']}
    if offers:
        result['best_offer'] = min(offers, key=lambda o: ({'in_stock':0,'unknown':1,'out_of_stock':2}.get(o['stock_status'],1),o['price_try']))
    return result


def summarize(plan, checks):
    pages = plan['pages']; done = sum(bool(checks.get(p['url'], {}).get('final')) for p in pages)
    errors = sum(bool(checks.get(p['url'], {}).get('final')) and not checks[p['url']].get('success') for p in pages)
    priced = {d['product_id'] for check in checks.values() for d in check.get('decisions', []) if d.get('offer')}
    return {'method_version':VERSION, 'updated_at':utc(), 'scope_total':len(plan['queries']),
            'proven_searches':sum(q['search_proven'] for q in plan['queries']),
            'candidate_products':sum(any(a['matched_urls'] for a in q['search_audits']) for q in plan['queries']),
            'total_pages':len(pages), 'completed_pages':done, 'pending_pages':len(pages)-done,
            'page_progress_pct':round(100*done/len(pages),3) if pages else 100,
            'unresolved_pages':errors, 'verified_price_products':len(priced),
            'finished':done==len(pages), 'complete':done==len(pages) and errors==0,
            'global_absence_proven':False}


def save_summary(root, plan, checks, start=None, starting_completed=0):
    summary = summarize(plan, checks)
    if start is not None:
        elapsed = time.time()-start; gained = summary['completed_pages']-starting_completed
        summary.update(worker_seconds=round(elapsed,1), worker_completed=gained)
        if gained:
            summary['measured_remaining_hours'] = round(summary['pending_pages']*elapsed/gained/3600,2)
    (root/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print('CHECKPOINT', json.dumps(summary), flush=True)
    return summary


def step_summary(summary):
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    if path:
        with open(path, 'a') as f:
            f.write(f"\n### SENLIS evidence v4\n\nSearch proven: {summary['proven_searches']}/{summary['scope_total']}. "
                    f"Page checks: {summary['completed_pages']}/{summary['total_pages']} ({summary['page_progress_pct']}%). "
                    f"Price products: {summary['verified_price_products']}. Pending: {summary['pending_pages']}. "
                    f"Unresolved: {summary['unresolved_pages']}. Scope: five named catalogues only.\n")


def load_plan(root):
    return {'queries':read_jsonl(root/'queries.jsonl.gz'), 'pages':read_jsonl(root/'pages.jsonl.gz')}


def prepare(args):
    checkpoint = GitCheckpoint(args.state); root = checkpoint.root
    if (root/'campaign.json').exists(): raise ValueError('campaign already exists; resume workers, never overwrite evidence')
    bootstrap = Path(args.evidence)
    summary = json.loads((bootstrap/'summary.json').read_text())
    results = json.loads((bootstrap/'results.json').read_text())
    required = {'36013','77267','90677','100781','113828'}
    accepted = {r['product_id'] for r in results if r['offers']}
    if not summary.get('gate_passed') or summary['sources_complete'] != len(SOURCES) or not required <= accepted:
        raise ValueError('fresh full-scan canary gate failed')
    reports = {r['source_id']:r for r in json.loads((bootstrap/'source_reports.json').read_text())}
    catalogues = []
    for source in SOURCES:
        report = reports[source['id']]; raw = gzip.decompress((bootstrap/report['catalogue_file']).read_bytes())
        if hashlib.sha256(raw).hexdigest() != report['catalogue_sha256']: raise ValueError('catalogue hash mismatch')
        entries = [json.loads(line) for line in raw.decode().splitlines() if line]
        if len(entries) != report['entry_count']: raise ValueError('catalogue row-count mismatch')
        catalogues.append((source, report, entries))
    definitions = json.loads(Path('data/commerce_v3_seeds.json').read_text())
    rows, warnings = validated_rows(load_rows(), definitions.get('identity_overrides', {}))
    plan = build_plan(rows, catalogues)
    if len(plan['queries']) != TOTAL: raise ValueError('manifest coverage mismatch')
    shutil.copytree(bootstrap, root/'bootstrap', dirs_exist_ok=True)
    (root/'manifest_repairs.json').write_text(json.dumps(warnings,indent=2)+'\n')
    write_jsonl(root/'queries.jsonl.gz', plan['queries']); write_jsonl(root/'pages.jsonl.gz', plan['pages'])
    metadata = {'created_at':utc(), 'code_sha':os.environ.get('GITHUB_SHA','local'),
                'run_id':os.environ.get('GITHUB_RUN_ID','local'), 'scope_total':TOTAL,
                'query_file_sha256':hashlib.sha256((root/'queries.jsonl.gz').read_bytes()).hexdigest(),
                'pages_file_sha256':hashlib.sha256((root/'pages.jsonl.gz').read_bytes()).hexdigest(),
                'sources':[{'id':s['id'],'catalogue_sha256':r['catalogue_sha256']} for s,r,_ in catalogues]}
    (root/'campaign.json').write_text(json.dumps(metadata, indent=2)+'\n')
    summary = save_summary(root, plan, {}); checkpoint.persist(); step_summary(summary)
    return 0


def checked_plan(root):
    metadata = json.loads((root/'campaign.json').read_text())
    for filename, key in [('queries.jsonl.gz','query_file_sha256'),('pages.jsonl.gz','pages_file_sha256')]:
        if hashlib.sha256((root/filename).read_bytes()).hexdigest() != metadata[key]: raise ValueError('campaign plan hash mismatch')
    if os.environ.get('GITHUB_SHA') and metadata['code_sha'] != os.environ['GITHUB_SHA']:
        raise ValueError('campaign code changed; explicit new campaign required')
    plan = load_plan(root)
    if len(plan['queries']) != metadata['scope_total']: raise ValueError('campaign row-count mismatch')
    return plan


def worker(args):
    checkpoint = GitCheckpoint(args.state); root = checkpoint.root
    plan = checked_plan(root); checks = read_checks(root)
    initial = summarize(plan, checks)
    if initial['finished']: step_summary(initial); return 0
    rows = {q['product_id']:q['identity'] for q in plan['queries']}
    start = time.time(); client = PoliteClient(0,1,slot=6,deadline=start+args.seconds-120,retain_error_bodies=True)
    evidence = Evidence(root); buffer = []; flushed = time.time()
    for check in checks.values():
        h = host(check['url']); client.cooldowns[h] = max(client.cooldowns.get(h,0),check.get('retry_at',0))
    def flush():
        nonlocal buffer, flushed
        write_batch(root, buffer); buffer = []
        summary = save_summary(root, plan, checks, start, initial['completed_pages'])
        checkpoint.persist(); flushed = time.time()
        return summary
    try:
        while time.time() < client.deadline-60:
            pending = [p for p in plan['pages'] if not checks.get(p['url'],{}).get('final')]
            if not pending: break
            ready = [p for p in pending if eligible(checks.get(p['url']),time.time()) and client.available_at(p['url'])<=time.time()]
            if not ready:
                due = min(max(checks.get(p['url'],{}).get('retry_at',0),client.available_at(p['url'])) for p in pending)
                time.sleep(min(30,max(0.1,due-time.time()))); continue
            for page in ready:
                if time.time() >= client.deadline-60: break
                if client.available_at(page['url']) > time.time(): continue
                r, event = evidence.fetch(client, page['url'])
                prior = checks.get(page['url'], {})
                skipped = r.error in ('host_cooldown','deadline')
                attempts = prior.get('attempts',0)+(0 if skipped else 1)
                decisions = []
                if r.ok:
                    for pid in page['product_ids']:
                        offer, reason = verify_listing(r.text, r.url, rows[pid])
                        if offer: offer.update(checked_at=event['fetched_at'], evidence_sha256=event['decoded_sha256'],
                                               source_id=page['source_id'], checkout_verified=False)
                        decisions.append({'product_id':pid, 'reason':reason, 'offer':offer})
                record = {'url':page['url'], 'source_id':page['source_id'], 'attempts':attempts,
                    'final':r.ok or r.status in (404,410) or attempts>=MAX_ATTEMPTS,
                    'success':r.ok, 'error':r.error, 'retry_at':max(r.retry_at,time.time()+60) if not r.ok else 0,
                    'page_evidence':event, 'decisions':decisions, 'observed_at':utc()}
                checks[page['url']] = record; buffer.append(record)
                if len(buffer)>=50 or time.time()-flushed>=300: flush()
            if buffer: flush()
    finally:
        # This also preserves successful pages preceding a parser/process failure.
        summary = flush(); step_summary(summary)
    return 0


def report(args):
    checkpoint = GitCheckpoint(args.state); root = checkpoint.root
    plan = checked_plan(root); checks = read_checks(root)
    results = [product_result(q, checks) for q in plan['queries']]
    write_jsonl(root/'results.jsonl.gz', results)
    columns = ['product_id','brand_name','product_name','release_year','status','search_proven','verification_complete',
               'scope','method_version','price_try','currency','volume_ml','stock_status','purchase_url','seller_name','checked_at']
    with tempfile.TemporaryDirectory() as tmp:
        dbpath = Path(tmp)/'commerce_v4.sqlite'; db = sqlite3.connect(dbpath)
        db.execute('CREATE TABLE commerce ('+','.join('"'+c+'" '+('REAL' if c in ('price_try','volume_ml') else 'TEXT') for c in columns)+', PRIMARY KEY(product_id))')
        with gzip.open(root/'results.csv.gz','wt',encoding='utf-8-sig',newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore'); writer.writeheader()
            for result in results:
                row = dict(result, **result.get('best_offer',{})); writer.writerow(row)
                db.execute('INSERT INTO commerce VALUES ('+','.join('?' for _ in columns)+')',[row.get(c) for c in columns])
        db.commit(); db.close()
        with dbpath.open('rb') as source, gzip.open(root/'commerce_v4.sqlite.gz','wb') as dest: shutil.copyfileobj(source,dest)
    summary = save_summary(root, plan, checks)
    summary['status_counts'] = dict(Counter(r['status'] for r in results))
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    checkpoint.persist(); step_summary(summary)
    return 0 if summary['complete'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('command', choices=['prepare','worker','report'])
    parser.add_argument('--state', default='state'); parser.add_argument('--evidence',default='commerce_v4_evidence')
    parser.add_argument('--seconds',type=int,default=5400)
    args = parser.parse_args(); raise SystemExit(globals()[args.command](args))
