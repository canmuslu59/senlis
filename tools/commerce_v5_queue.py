#!/usr/bin/env python3
"""Orchestrate the preserved queue; execute only the separately pinned scanner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

REPO = 'canmuslu59/senlis'
FEATURE_BRANCH = 'feature/commerce-global-v5-20261006'
WORKFLOW = 'commerce-queue-v5.yml'
RUNTIME_SHA = 'd9a1976433016e65a4afcad7189adb6a14b65caf'
CAMPAIGN_SHA256 = '38b4bd2223e4a0008b3172665ef07e7a6a4e4730a2f381de0a561a0212d060e7'
BASELINE_EVENTS = 21856
BASELINE_CHAIN = 'ec161b137aaa2f521995fba223d18a8d07ccb4dc0bb5ffeecef39cd087b93b7b'
EXPORTS = ('commerce_v5.sqlite.gz', 'results.jsonl.gz', 'offers.csv.gz', 'source_audits.jsonl.gz')


def queue_action(s):
    keys = ('scope_total', 'tasks_total', 'tasks_completed', 'tasks_pending',
            'total_pages', 'completed_pages', 'pending_pages')
    if any(type(s.get(k)) is not int or s[k] < 0 for k in keys):
        raise ValueError('invalid checkpoint counters')
    if (s['scope_total'] != 174259 or
        s['tasks_total'] != s['tasks_completed'] + s['tasks_pending'] or
        s['total_pages'] != s['completed_pages'] + s['pending_pages'] or
        s['pending_pages'] > s['tasks_pending'] or
        type(s.get('finished')) is not bool or type(s.get('complete')) is not bool or
        s['finished'] != (s['tasks_pending'] == 0) or
        (s['complete'] and not s['finished'])):
        raise ValueError('inconsistent checkpoint summary')
    return 'continue' if s['tasks_pending'] else 'complete' if s['complete'] else 'finished_with_gaps'


def verify_progress(before, after):
    queue_action(before); queue_action(after)
    for k in ('tasks_completed', 'completed_pages', 'verified_price_products', 'event_count'):
        if after[k] < before[k]:
            raise ValueError('checkpoint lost progress: ' + k)


def validate_context(env, controller_head, runtime_head):
    if (env.get('GITHUB_REPOSITORY') != REPO or env.get('GITHUB_REF_NAME') != FEATURE_BRANCH or
        not re.fullmatch('[0-9a-f]{40}', env.get('GITHUB_SHA', '')) or
        controller_head != env['GITHUB_SHA'] or runtime_head != RUNTIME_SHA or
        not env.get('GITHUB_RUN_ID', '').isdigit()):
        raise ValueError('unexpected repository, branch, controller or runtime')
    event = env.get('GITHUB_EVENT_NAME')
    if event not in ('push', 'workflow_dispatch'):
        raise ValueError('unsupported launch event')
    if event == 'workflow_dispatch' and (
        env.get('EXPECTED_CONTROLLER_SHA') != controller_head or
        not env.get('PARENT_RUN_ID', '').isdigit()):
        raise ValueError('controller moved or invalid parent run')


def validate_metadata(campaign, revision, manifest, campaign_digest):
    if (campaign_digest != CAMPAIGN_SHA256 or campaign.get('scope_total') != 174259 or
        campaign.get('code_sha') != '15a827b3f5a10c4712a5fec934471348052df4e7' or
        revision.get('code_sha') != RUNTIME_SHA or
        revision.get('campaign_sha256') != CAMPAIGN_SHA256 or
        manifest.get('event_count', -1) < BASELINE_EVENTS):
        raise ValueError('campaign/runtime mismatch or rolled-back checkpoint')
    count = 0
    for segment in manifest.get('segments', []):
        count += segment['event_count']
        if count >= BASELINE_EVENTS:
            if count == BASELINE_EVENTS and segment['chain_sha256'] == BASELINE_CHAIN:
                break
            raise ValueError('preserved event prefix mismatch')
    else:
        raise ValueError('preserved event prefix missing')


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def pack_exports(root, limit=90*1024*1024, chunk_size=48*1024*1024):
    """Only generated exports may be chunked; publish a lossless manifest."""
    if not 0 < chunk_size < limit: raise ValueError('invalid export chunk sizes')
    root = Path(root); manifest = {'version': 1, 'files': {}}
    for name in EXPORTS:
        path = root/name
        if not path.exists(): continue
        entry = {'bytes': path.stat().st_size, 'sha256': file_hash(path), 'parts': []}
        if entry['bytes'] <= limit:
            entry['parts'] = [{'file': name, 'bytes': entry['bytes'], 'sha256': entry['sha256']}]
            for old in root.glob(name+'.part-*'): old.unlink()
        else:
            with tempfile.TemporaryDirectory(dir=root, prefix='export-') as tmp:
                joined = hashlib.sha256(); size = 0
                with path.open('rb') as src:
                    for i, block in enumerate(iter(lambda: src.read(chunk_size), b''), 1):
                        part = f'{name}.part-{i:04d}'
                        dest = Path(tmp)/part; dest.write_bytes(block)
                        saved = dest.read_bytes(); joined.update(saved); size += len(saved)
                        entry['parts'].append({'file': part, 'bytes': len(saved),
                                               'sha256': hashlib.sha256(saved).hexdigest()})
                if size != entry['bytes'] or joined.hexdigest() != entry['sha256']:
                    raise ValueError('export chunk verification failed')
                for old in root.glob(name+'.part-*'): old.unlink()
                for part in entry['parts']: (Path(tmp)/part['file']).replace(root/part['file'])
                path.unlink()
        manifest['files'][name] = entry
    dest = root/'exports_manifest.json'
    dest.write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


def github_api(method, path, payload=None):
    headers = {'Authorization': 'Bearer '+os.environ['GH_TOKEN'],
               'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode(); headers['Content-Type'] = 'application/json'
    request = Request('https://api.github.com/'+path, data=body, headers=headers, method=method)
    with urlopen(request, timeout=45) as response:
        raw = response.read()
    return json.loads(raw) if raw else None


def verify_parent(api, parent, controller_sha):
    run = api('GET', f'repos/{REPO}/actions/runs/{parent}')
    if (run.get('status') != 'completed' or run.get('conclusion') != 'success' or
        run.get('head_sha') != controller_sha or run.get('head_branch') != FEATURE_BRANCH or
        run.get('path') != '.github/workflows/'+WORKFLOW):
        raise ValueError('parent run is not a successful matching controller; do not scan')


def verify_checkpoint_anchor(manifest, anchor):
    """Accept new descendant events on retry, never loss of a parent's prefix."""
    sha = str(anchor.get('checkpoint_sha', '')); head = str(anchor.get('chain_sha256', ''))
    raw_count = str(anchor.get('event_count', ''))
    if (not re.fullmatch('[0-9a-f]{40}', sha) or not re.fullmatch('[0-9a-f]{64}', head) or
        not raw_count.isdigit() or int(raw_count) < BASELINE_EVENTS):
        raise ValueError('invalid parent/scan checkpoint anchor')
    expected = int(raw_count); count = 0
    for segment in manifest['segments']:
        count += segment['event_count']
        if count >= expected:
            if count == expected and segment['chain_sha256'] == head: return
            break
    raise ValueError('parent/scan checkpoint evidence lost or rewritten')


def dispatch_next(api, context, sleep=time.sleep):
    """An ambiguous POST is inspected, never automatically repeated."""
    parent = str(context['run_id']); sha = context['controller_sha']
    title = 'SENLIS v5 queue after '+parent
    def find_child():
        runs = []
        for page in range(1, 101):
            params = urlencode(dict(branch=FEATURE_BRANCH, per_page=100, page=page))
            result = api('GET', f'repos/{REPO}/actions/workflows/{WORKFLOW}/runs?{params}')
            batch = result['workflow_runs']; runs.extend(batch)
            if len(batch) < 100: break
        else: raise ValueError('too many runs to safely verify dispatch uniqueness')
        children = [r for r in runs if r.get('display_title') == title]
        if len(children) > 1: raise ValueError('duplicate successor runs; manual review required')
        if children:
            child = children[0]
            if child.get('head_sha') != sha or child.get('event') != 'workflow_dispatch':
                raise ValueError('successor controller identity mismatch')
            return child
        if any(str(r['id']) != parent and r.get('status') != 'completed' for r in runs):
            raise ValueError('another queue run is active; refusing duplicate dispatch')
        return None
    existing = find_child()
    if existing: return existing
    ref = api('GET', f'repos/{REPO}/git/ref/heads/{quote(FEATURE_BRANCH, safe="")}')
    if ref['object']['sha'] != sha: raise ValueError('controller branch moved before dispatch')
    error = None
    try:
        api('POST', f'repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches',
            {'ref': FEATURE_BRANCH, 'inputs': {'parent_run_id': parent, 'controller_sha': sha,
             'checkpoint_sha': context['checkpoint_sha'], 'event_count': str(context['event_count']),
             'chain_sha256': context['chain_sha256']}})
    except Exception as exc:
        error = type(exc).__name__+': '+str(exc)[:240]
    for _ in range(6):
        sleep(5)
        child = find_child()
        if child: return child
    raise RuntimeError('dispatch outcome ambiguous; inspect GitHub before retrying'+(' ('+error+')' if error else ''))


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def published_checkpoint(cp):
    if git(cp.checkout, 'rev-parse', '--show-toplevel') != str(cp.checkout):
        raise ValueError('checkpoint requires its own checkout')
    if git(cp.checkout, 'branch', '--show-current') != 'data/commerce-v5-20261007':
        raise ValueError('wrong checkpoint branch')
    if git(cp.checkout, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('unpublished checkpoint changes; recovery required')
    head = git(cp.checkout, 'rev-parse', 'HEAD')
    remote = git(cp.checkout, 'ls-remote', '--exit-code', 'origin', 'refs/heads/data/commerce-v5-20261007').split()[0]
    if head != remote: raise ValueError('durable checkpoint moved; refusing stale state')
    return head


def load_store(runtime, cp):
    published_checkpoint(cp)
    store = runtime.Store(cp.root, code_sha=RUNTIME_SHA)  # Replays and hashes every event.
    try:
        validate_metadata(store.campaign, store.revision or {}, store.manifest,
                          file_hash(cp.root/'campaign.json'))
        summary = store.summary(); queue_action(summary)
        summary['event_count'] = store.manifest['event_count']
        return store, summary
    except Exception:
        store.close(); raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['scan', 'handoff'])
    parser.add_argument('--runtime', required=True); parser.add_argument('--state', required=True)
    args = parser.parse_args()
    code = Path(args.runtime).resolve(); state = Path(args.state).resolve()
    controller = Path(__file__).resolve().parents[1]
    validate_context(os.environ, git(controller, 'rev-parse', 'HEAD'), git(code, 'rev-parse', 'HEAD'))
    if git(code, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('pinned runtime checkout is modified')
    sys.path.insert(0, str(code/'tools'))
    import commerce_full_v5 as runtime
    if Path(runtime.__file__).resolve() != code/'tools/commerce_full_v5.py':
        raise ValueError('runtime import came from unexpected checkout')
    cp = runtime.Checkpoint(state); store, before = load_store(runtime, cp)
    context = dict(run_id=os.environ['GITHUB_RUN_ID'], controller_sha=os.environ['GITHUB_SHA'])
    anchor_prefix = 'SCAN_' if args.command == 'handoff' else 'EXPECTED_'
    if args.command == 'handoff' or os.environ['GITHUB_EVENT_NAME'] == 'workflow_dispatch':
        anchor = {k: os.environ.get(anchor_prefix+k.upper(), '')
                  for k in ('checkpoint_sha', 'event_count', 'chain_sha256')}
        verify_checkpoint_anchor(store.manifest, anchor)
    if args.command == 'scan':
        store.close()
        if os.environ['GITHUB_EVENT_NAME'] == 'workflow_dispatch':
            verify_parent(github_api, os.environ['PARENT_RUN_ID'], context['controller_sha'])
            if queue_action(before) == 'continue':
                env = dict(os.environ, GITHUB_SHA=RUNTIME_SHA)
                subprocess.run([sys.executable, 'tools/commerce_full_v5.py', 'worker',
                                '--state', str(state), '--seconds', '5400'], cwd=code, env=env, check=True)
        store, after = load_store(runtime, cp)
        outputs = dict(checkpoint_sha=published_checkpoint(cp), event_count=store.manifest['event_count'],
                       chain_sha256=store.manifest['head_sha256'])
        store.close()
        verify_progress(before, after)
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            for k, v in outputs.items(): f.write(f'{k}={v}\n')
        print('QUEUE_SCAN_VALIDATED', json.dumps(after), flush=True)
        return
    action = queue_action(before)
    receipt = dict(context, runtime_sha=RUNTIME_SHA, action=action,
                   state_commit=git(state, 'rev-parse', 'HEAD'), summary=before)
    try:
        if action != 'continue':
            # Export is the pinned scanner's unchanged implementation; only packaging is new.
            runtime.export(store); pack_exports(cp.root)
        (cp.root/'queue_control.json').write_text(json.dumps(receipt, indent=2)+'\n')
        cp.persist(); published_checkpoint(cp)
    finally: store.close()
    if action == 'continue':
        # There is no checkpoint mutation after dispatch. The child additionally
        # requires this parent to conclude successfully before it can scan.
        context.update(checkpoint_sha=published_checkpoint(cp), event_count=before['event_count'],
                       chain_sha256=store.manifest['head_sha256'])
        child = dispatch_next(github_api, context)
        receipt['next_run_id'] = child['id']; receipt['next_run_status'] = child['status']
        receipt['dispatched_checkpoint'] = context
    (controller/'queue-handoff.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('QUEUE_HANDOFF', json.dumps(receipt), flush=True)


if __name__ == '__main__': main()
