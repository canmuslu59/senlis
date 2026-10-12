import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from commerce_v5_queue import (queue_action, verify_progress, pack_exports,
                               dispatch_next, validate_context, validate_metadata,
                               published_checkpoint, RUNTIME_SHA, CAMPAIGN_SHA256,
                               FEATURE_BRANCH, verify_parent, verify_checkpoint_anchor)


def summary(pending=2, complete=False):
    return dict(scope_total=174259, tasks_total=10, tasks_completed=10-pending,
                tasks_pending=pending, total_pages=8, completed_pages=8-min(pending, 8),
                pending_pages=min(pending, 8), finished=pending == 0, complete=complete,
                verified_price_products=4)


class Decisions(unittest.TestCase):
    def test_continue_only_pending_work_and_stop_with_coverage_gaps(self):
        self.assertEqual(queue_action(summary()), 'continue')
        self.assertEqual(queue_action(summary(0)), 'finished_with_gaps')
        self.assertEqual(queue_action(summary(0, True)), 'complete')

    def test_invalid_or_inconsistent_checkpoint_never_dispatches(self):
        for patch in [dict(scope_total=1), dict(tasks_pending=-1),
                      dict(tasks_pending=True), dict(finished=True),
                      dict(complete=True), dict(tasks_total=99),
                      dict(pending_pages=3), dict(finished='false')]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                queue_action(dict(summary(), **patch))

    def test_discovery_can_grow_pending_work_but_cannot_lose_completed_work(self):
        before = dict(summary(), event_count=100)
        after = dict(summary(), tasks_total=20, tasks_pending=12, event_count=101)
        verify_progress(before, after)
        for patch in [dict(event_count=99), dict(tasks_completed=7),
                      dict(completed_pages=5), dict(verified_price_products=3)]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                verify_progress(before, dict(after, **patch))

    def test_wrong_repository_branch_or_moving_controller_is_rejected(self):
        env = dict(GITHUB_REPOSITORY='canmuslu59/senlis', GITHUB_REF_NAME=FEATURE_BRANCH,
                   GITHUB_SHA='a'*40, GITHUB_EVENT_NAME='workflow_dispatch',
                   EXPECTED_CONTROLLER_SHA='a'*40, PARENT_RUN_ID='123', GITHUB_RUN_ID='456')
        validate_context(env, 'a'*40, RUNTIME_SHA)
        for patch in [dict(GITHUB_REPOSITORY='other/repo'), dict(GITHUB_REF_NAME='main'),
                      dict(EXPECTED_CONTROLLER_SHA='b'*40), dict(PARENT_RUN_ID=''),
                      dict(GITHUB_EVENT_NAME='pull_request')]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate_context(dict(env, **patch), 'a'*40, RUNTIME_SHA)
        with self.assertRaises(ValueError): validate_context(env, 'a'*40, 'c'*40)

    def test_campaign_runtime_and_event_floor_are_checked(self):
        campaign = dict(code_sha='15a827b3f5a10c4712a5fec934471348052df4e7', scope_total=174259)
        revision = dict(code_sha=RUNTIME_SHA, campaign_sha256=CAMPAIGN_SHA256)
        manifest = dict(event_count=21856, segments=[dict(event_count=21856,
                        chain_sha256='ec161b137aaa2f521995fba223d18a8d07ccb4dc0bb5ffeecef39cd087b93b7b')])
        validate_metadata(campaign, revision, manifest, CAMPAIGN_SHA256)
        for c, r, m, digest in [(dict(campaign, scope_total=2), revision, manifest, CAMPAIGN_SHA256),
                               (campaign, dict(revision, code_sha='d'*40), manifest, CAMPAIGN_SHA256),
                               (campaign, revision, dict(event_count=21855), CAMPAIGN_SHA256),
                               (campaign, revision, manifest, '0'*64)]:
            with self.assertRaises(ValueError): validate_metadata(c, r, m, digest)

    def test_later_checkpoint_must_preserve_the_known_event_prefix(self):
        campaign = dict(code_sha='15a827b3f5a10c4712a5fec934471348052df4e7', scope_total=174259)
        revision = dict(code_sha=RUNTIME_SHA, campaign_sha256=CAMPAIGN_SHA256)
        manifest = dict(event_count=21857, segments=[dict(event_count=21856, chain_sha256='0'*64),
                                                   dict(event_count=1, chain_sha256='1'*64)])
        with self.assertRaisesRegex(ValueError, 'prefix'):
            validate_metadata(campaign, revision, manifest, CAMPAIGN_SHA256)

    def test_real_git_checkpoint_must_be_clean_and_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); remote = root/'remote.git'; state = root/'state'
            def git(*args):
                return subprocess.run(['git', *map(str, args)], check=True, capture_output=True, text=True).stdout.strip()
            git('init', '--bare', remote); git('clone', remote, state)
            git('-C', state, 'checkout', '-b', 'data/commerce-v5-20261007')
            git('-C', state, 'config', 'user.email', 'test@example.com')
            git('-C', state, 'config', 'user.name', 'Queue Test')
            (state/'record').write_text('one')
            git('-C', state, 'add', '.'); git('-C', state, 'commit', '-m', 'baseline')
            git('-C', state, 'push', 'origin', 'HEAD')
            cp = SimpleNamespace(checkout=state)
            self.assertEqual(published_checkpoint(cp), git('-C', state, 'rev-parse', 'HEAD'))
            (state/'record').write_text('unpublished')
            with self.assertRaisesRegex(ValueError, 'unpublished'): published_checkpoint(cp)
            git('-C', state, 'commit', '-am', 'not pushed')
            with self.assertRaisesRegex(ValueError, 'stale'): published_checkpoint(cp)


class Exports(unittest.TestCase):
    def test_large_export_roundtrip_and_small_files_and_evidence_stay_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); raw = bytes(range(256))*4
            (root/'commerce_v5.sqlite.gz').write_bytes(raw)
            (root/'results.jsonl.gz').write_bytes(b'results')
            (root/'offers.csv.gz').write_bytes(b'offers')
            (root/'scope.jsonl.gz').write_bytes(raw)
            manifest = pack_exports(root, limit=100, chunk_size=64)
            entry = manifest['files']['commerce_v5.sqlite.gz']
            rebuilt = b''.join((root/p['file']).read_bytes() for p in entry['parts'])
            self.assertEqual(rebuilt, raw)
            self.assertEqual(entry['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertTrue(all(p['bytes'] <= 64 for p in entry['parts']))
            self.assertFalse((root/'commerce_v5.sqlite.gz').exists())
            self.assertEqual((root/'results.jsonl.gz').read_bytes(), b'results')
            self.assertEqual((root/'scope.jsonl.gz').read_bytes(), raw)
            self.assertEqual(json.loads((root/'exports_manifest.json').read_text()), manifest)

    def test_reexport_replaces_old_chunks_and_checks_parameters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); name = 'commerce_v5.sqlite.gz'
            (root/name).write_bytes(b'x'*50); pack_exports(root, limit=20, chunk_size=10)
            (root/name).write_bytes(b'y'*3); pack_exports(root, limit=20, chunk_size=10)
            self.assertEqual(list(root.glob(name+'.part-*')), [])
            self.assertEqual((root/name).read_bytes(), b'yyy')
            with self.assertRaises(ValueError): pack_exports(root, limit=10, chunk_size=20)


class API:
    def __init__(self, existing=None, ambiguous=False):
        self.runs = existing or []; self.posts = []; self.ambiguous = ambiguous
    def __call__(self, method, path, payload=None):
        if method == 'POST':
            self.posts.append(payload)
            if self.ambiguous: raise TimeoutError('unknown outcome')
            self.runs.append(dict(id=99, display_title='SENLIS v5 queue after 123',
                                  head_sha='a'*40, event='workflow_dispatch', status='queued'))
            return None
        if '/git/ref/' in path: return dict(object=dict(sha='a'*40))
        return dict(total_count=len(self.runs), workflow_runs=self.runs)


class Dispatch(unittest.TestCase):
    ctx = dict(run_id='123', controller_sha='a'*40, checkpoint_sha='c'*40,
               event_count=21856, chain_sha256='d'*64)
    def test_one_dispatch_is_observed_and_rerun_cannot_duplicate_it(self):
        api = API()
        self.assertEqual(dispatch_next(api, self.ctx, sleep=lambda _: None)['id'], 99)
        self.assertEqual(dispatch_next(api, self.ctx, sleep=lambda _: None)['id'], 99)
        self.assertEqual(len(api.posts), 1)
        self.assertEqual(api.posts[0]['inputs']['controller_sha'], 'a'*40)
        self.assertEqual(api.posts[0]['inputs']['event_count'], '21856')
        self.assertEqual(api.posts[0]['inputs']['chain_sha256'], 'd'*64)
        self.assertEqual(api.posts[0]['inputs']['checkpoint_sha'], 'c'*40)
        self.assertEqual(api.posts[0]['ref'], FEATURE_BRANCH)

    def test_unknown_post_outcome_is_not_repeated(self):
        api = API(ambiguous=True)
        with self.assertRaisesRegex(RuntimeError, 'ambiguous'):
            dispatch_next(api, self.ctx, sleep=lambda _: None)
        self.assertEqual(len(api.posts), 1)

    def test_unrelated_active_worker_prevents_dispatch(self):
        api = API([dict(id=77, display_title='another chain', status='in_progress')])
        with self.assertRaisesRegex(ValueError, 'active'):
            dispatch_next(api, self.ctx, sleep=lambda _: None)
        self.assertEqual(api.posts, [])

    def test_duplicate_successors_and_wrong_code_fail_closed(self):
        child = dict(id=99, display_title='SENLIS v5 queue after 123',
                     head_sha='a'*40, event='workflow_dispatch', status='queued')
        for runs in [[child, dict(child, id=100)], [dict(child, head_sha='b'*40)]]:
            api = API(runs)
            with self.assertRaises(ValueError): dispatch_next(api, self.ctx, sleep=lambda _: None)
            self.assertEqual(api.posts, [])

    def test_failed_or_unfinished_parent_prevents_child_scanning(self):
        run = dict(status='completed', conclusion='success', head_sha='a'*40,
                   head_branch=FEATURE_BRANCH, path='.github/workflows/commerce-queue-v5.yml')
        verify_parent(lambda *args: run, '123', 'a'*40)
        for patch in [dict(status='in_progress'), dict(conclusion='failure'),
                      dict(head_sha='b'*40), dict(path='another-workflow.yml')]:
            with self.subTest(patch=patch), self.assertRaisesRegex(ValueError, 'parent'):
                verify_parent(lambda *args: dict(run, **patch), '123', 'a'*40)

    def test_successor_and_handoff_cannot_accept_a_rollback_beyond_initial_baseline(self):
        anchor = dict(checkpoint_sha='c'*40, event_count='22000', chain_sha256='d'*64)
        later = dict(event_count=22001, segments=[dict(event_count=22000, chain_sha256='d'*64),
                                                dict(event_count=1, chain_sha256='e'*64)])
        verify_checkpoint_anchor(later, anchor)
        for manifest in [dict(event_count=21900, segments=[]),
                         dict(event_count=22000, segments=[dict(event_count=22000, chain_sha256='f'*64)])]:
            with self.assertRaisesRegex(ValueError, 'checkpoint'):
                verify_checkpoint_anchor(manifest, anchor)


if __name__ == '__main__': unittest.main()
