"""Durable campaign checkpoints in the separately checked-out data branch."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time

BRANCH = 'data/commerce-v4-20261005'
RELATIVE_ROOT = Path('data/commerce_v4/20261005')


def read_jsonl(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    raw = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in rows).encode()
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes(gzip.compress(raw, mtime=0)); temporary.replace(path)


def write_batch(root, records):
    if not records: return
    payload = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in records).encode()
    directory = Path(root)/'checks'; directory.mkdir(parents=True, exist_ok=True)
    name = str(time.time_ns())+'-'+hashlib.sha256(payload).hexdigest()[:12]+'.jsonl.gz'
    (directory/name).write_bytes(gzip.compress(payload, mtime=0))


def read_checks(root):
    latest = {}
    for path in sorted((Path(root)/'checks').glob('*.jsonl.gz')):
        for record in read_jsonl(path): latest[record['url']] = record
    return latest


class GitCheckpoint:
    def __init__(self, checkout):
        self.checkout = Path(checkout).resolve()
        self.root = self.checkout/RELATIVE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def git(self, *args, check=True):
        result = subprocess.run(['git', '-C', str(self.checkout), *args],
                                capture_output=True, text=True, timeout=180)
        if check and result.returncode:
            # Git diagnostics can contain credential-bearing remote URLs.
            raise RuntimeError('checkpoint git '+args[0]+' failed, exit '+str(result.returncode))
        return result

    def persist(self):
        if self.git('rev-parse', '--show-toplevel').stdout.strip() != str(self.checkout):
            raise RuntimeError('checkpoint must use its own checkout')
        branch = self.git('branch', '--show-current').stdout.strip()
        if branch != BRANCH: raise RuntimeError('unexpected checkpoint branch')
        self.git('config', 'user.name', 'SENLIS Research')
        self.git('config', 'user.email', 'senlis-research@users.noreply.github.com')
        self.git('add', '--', str(RELATIVE_ROOT))
        if self.git('diff', '--cached', '--quiet', check=False).returncode:
            self.git('commit', '-m', 'checkpoint: evidence v4 '+datetime.now(timezone.utc).isoformat())
        for attempt in range(3):
            if self.git('push', '--quiet', 'origin', 'HEAD:refs/heads/'+BRANCH, check=False).returncode == 0:
                return
            time.sleep(5*(attempt+1))
        raise RuntimeError('checkpoint push failed; stopping this worker without claiming persistence')
