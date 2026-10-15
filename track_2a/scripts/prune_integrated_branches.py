"""Preview or delete unchanged integrated remote branches. Requires local Git login."""
import argparse
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--apply', action='store_true', help='Delete the verified remote refs; no local branches are deleted')
a = p.parse_args()
root = Path(__file__).resolve().parents[2]

def git(*args, check=True):
    return subprocess.run(['git', '-C', str(root), *args], check=check, text=True, capture_output=True)

url = git('remote','get-url','origin').stdout.strip()
if url not in ('https://github.com/blackmath88/apertushackathon-uzh.git','git@github.com:blackmath88/apertushackathon-uzh.git'):
    raise SystemExit('Refusing: origin is not the expected project')
git('fetch','origin','--prune')
rows = json.loads((root/'track_2a/docs/BRANCH_CLEANUP_2026-10-15.json').read_text())
remotes = dict((line.split()[1].removeprefix('refs/heads/'),line.split()[0]) for line in git('ls-remote','--heads','origin').stdout.splitlines())
worktrees = git('worktree','list','--porcelain').stdout
candidates = []
for row in rows:
    b, sha = row['branch'], row['sha']
    if row['retain'] or b not in remotes: continue
    if remotes[b] != sha:
        print('KEEP changed branch:', b); continue
    if 'branch refs/heads/'+b+'\n' in worktrees:
        print('KEEP checked-out local worktree:', b); continue
    if git('merge-base','--is-ancestor',sha,'origin/main',check=False).returncode:
        print('KEEP not contained in main:', b); continue
    candidates.append(row)
for row in candidates: print('DELETE' if a.apply else 'WOULD DELETE',row['branch'],row['sha'])
if a.apply and candidates:
    # Exact leases guard against a worker pushing between the read and deletion.
    git('push','--atomic',*[f"--force-with-lease=refs/heads/{r['branch']}:{r['sha']}" for r in candidates],
        'origin',*[f":refs/heads/{r['branch']}" for r in candidates])
else:
    print('Preview only. Once other local workers have settled, rerun with --apply from main.')
