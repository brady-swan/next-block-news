"""One-time owner-authorized overnight launch using the existing reviewed supervisor.

Same setup protocol as the completed three-hour observation: preserve prior receipts,
set this not-yet-started worker's fixed cutoff once under compare-and-set, then launch.
No credentials, model, publishing configuration, or existing Typefully drafts are changed.
Never rerun if intent or receipt exists; reconcile the exact state instead.
"""
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

sys.path.insert(0, '/Users/brady/codex/nbn-reporter-pilot/runtime')
import reporter_supervisor as s

TURN = '01a0a2f3-d44b-7e53-852a-f7fcf9ba9766'
OLD = 'pilot-20260914T205814Z'
CUTOFF = dt.datetime(2026, 9, 15, 13, 0, tzinfo=dt.timezone.utc).timestamp()
ROOT = s.CONTROL
receipt = ROOT / 'launch-overnight-20260915.json'
intent = ROOT / 'overnight-20260915-intent.json'
assert not receipt.exists() and not intent.exists(), 'Prior attempt exists; reconcile, never launch blindly.'
assert time.time() < CUTOFF - 1800, 'No late/post-cutoff launch.'
s.probe.require_pass()
old = s.api('pulse')['shift']
assert old['shift_id'] == OLD and old['status'] == 'completed' and not old['lease_alive']
assert old['expired'] and old['lease_until'] == 0
lock = (ROOT / 'supervisor.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
processes = subprocess.check_output(['ps', '-axo', 'pid,command'], text=True)
assert not any('/reporter_supervisor.py run' in line for line in processes.splitlines()), 'Existing supervisor present'
saved = json.loads(s.SESSION.read_text())
assert saved['shift_id'] == OLD
pending = ROOT / 'start-intent.json'
assert json.loads(pending.read_text())['shift_id'] == OLD
archive = ROOT / 'before-overnight-20260915'
archive.mkdir()
s.save(intent, {'owner_turn': TURN, 'previous_shift': OLD, 'cutoff_at': CUTOFF,
                'at': time.time(), 'state': 'starting'})
for p in (s.SESSION, pending):
    p.rename(archive / p.name)
s.start()
shift = json.loads(s.SESSION.read_text())
assert shift['shift_id'] != OLD and not shift.get('thread_id')
assert shift['cutoff_at'] - shift['started_at'] == 7200
payload = {'owner_turn': TURN, 'request_at': '2026-09-15T02:44:43.826Z',
           'old_cutoff': shift['cutoff_at'], 'new_cutoff': CUTOFF, 'draft_only': True,
           'scope': 'Overnight reporting and reversible execution improvements; image opportunities.'}
s.save(intent, {'shift_id': shift['shift_id'], 'state': 'setting_cutoff', **payload})
record_id = 'owner-overnight:' + TURN
code = f'''import json,time
from nbn import store,reporter_store as rs,config
assert config.AUTOPOST_ENABLED is False and config.OPERATING_MODE=='infrastructure'
con=store.connect(); ident={shift['shift_id']!r}; payload={payload!r}
with con:
 con.execute('BEGIN IMMEDIATE')
 row=rs.shift(con,ident)
 assert row['status']=='active' and row['generation']=={shift['generation']!r}
 assert not row['thread_id'] and row['cutoff_at']=={shift['cutoff_at']!r}
 assert time.time()<row['cutoff_at'] and row['started_at']=={shift['started_at']!r}
 cur=con.execute('UPDATE reporter_shifts SET cutoff_at=?,updated_at=? WHERE shift_id=? AND cutoff_at=? AND thread_id IS NULL',({CUTOFF!r},time.time(),ident,{shift['cutoff_at']!r}))
 assert cur.rowcount==1
 con.execute('INSERT INTO reporter_records(record_id,shift_id,kind,sender,at,payload_json) VALUES(?,?,?,?,?,?)',({record_id!r},ident,'owner_duration','owner',time.time(),rs.encoded(payload)))
print(json.dumps({{'shift_id':ident,'cutoff_at':rs.shift(con,ident)['cutoff_at'],'autopost':config.AUTOPOST_ENABLED}}))
'''
cmd = ['railway', 'ssh', '--project', '1e1f32d1-6153-4f71-80b3-9543050caa7e',
       '--service', 'ff9549a3-6f78-481a-a550-d8c10136af64', '--environment',
       '90c43f68-970a-4f93-a392-414c3c175502', '--', 'python', '-c', shlex.quote(code)]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=50)
if r.returncode:
    print(r.stderr[-1200:])
    raise RuntimeError('Cutoff setup uncertain; inspect remote state before retry.')
observed = json.loads(r.stdout)
assert observed['shift_id'] == shift['shift_id'] and observed['cutoff_at'] == CUTOFF and observed['autopost'] is False
shift['cutoff_at'] = CUTOFF
s.save(s.SESSION, shift)
remote = s.api('pulse')['shift']
assert remote['shift_id'] == shift['shift_id'] and remote['cutoff_at'] == CUTOFF and remote['status'] == 'active'
hashes = {n: hashlib.sha256((s.probe.WORK / n).read_bytes()).hexdigest()
          for n in ['AGENTS.md', 'orientation.md', 'calibration-examples.md']}
message_id = 'briefing:20260915:overnight-execution-v1'
s.api('message', {'shift_id': shift['shift_id'], 'record_id': message_id, 'payload': {
    'kind': 'operator_execution_delivery', 'version': 'reporter-execution-2026-09-15-v1',
    'owner_calibration_version': 'owner-calibration-2026-09-14-v2',
    'verified_owner_turn': TURN, 'workspace_files_sha256': hashes,
    'summary': 'Fresh authorized overnight draft-only shift, fixed September15 13:00UTC cutoff. Read installed orientation.md and calibration-examples.md once, then acknowledge with reply_to briefing:20260915:overnight-execution-v1. Owner asks for an earnest improvement run and more useful images by noticing opportunities, not forcing them. Follow the new concrete visual inspection/render/pixel-review workflow; charts, comparisons, quotes and readable excerpts can help readers understand at a glance. Preserve sourced numbers, dates, rights and alt text. Existing rendering only; Nano Banana remains parked. Use direct institutional indexes and original links, separate quote-post speakers, and write plain attribution without redundant audit caveats. Owner calibration is unchanged. All previous drafts remain coverage, not assignments to recreate; no duplicate image versions or existing-draft edits. Start from current intake/time, meaningful developments and open questions with promising new routes. Main audits every15minutes, with reversible execution improvements and provenance-preserving evidence sharing. No story quota. New unscheduled Typefully drafts only; autopublish OFF.'}})
log = ROOT / 'supervisor-overnight-20260915.log'
fcntl.flock(lock, fcntl.LOCK_UN)
with log.open('ab', buffering=0) as output:
    proc = subprocess.Popen([str(s.probe.PYTHON), '-u', str(s.probe.RUNTIME / 'reporter_supervisor.py'), 'run'],
                            cwd=s.probe.WORK, env=s.probe.runtime_env(), stdin=subprocess.DEVNULL,
                            stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
data = {'shift_id': shift['shift_id'], 'pid': proc.pid, 'started_at': shift['started_at'],
        'cutoff_at': CUTOFF, 'cutoff_utc': dt.datetime.fromtimestamp(CUTOFF, dt.timezone.utc).isoformat(),
        'message_id': message_id, 'owner_turn': TURN, 'hashes': hashes, 'log_path': str(log),
        'draft_only': True, 'model': 'gpt-6-astra', 'effort': 'medium', 'at': time.time()}
s.save(receipt, data)
s.save(intent, dict(data, state='launched'))
print(json.dumps(data))
