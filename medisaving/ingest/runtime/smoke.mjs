// Same sandbox builder as runAgent. No Codex execution or Telegram connection.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const runtime = path.resolve(process.argv[2]);
const { sandboxArgs } = await import(pathToFileURL(path.join(runtime, 'src/codex.js')));
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'med-ingest-smoke-'));
for (const sub of ['work', 'codex', 'other-chat']) fs.mkdirSync(path.join(temporary, sub));
fs.writeFileSync(path.join(temporary, 'other-chat', 'private'), 'synthetic-isolation-sentinel');
const script = `
import json, os, subprocess
def med(*args):
    p=subprocess.run(['med',*args],capture_output=True,text=True,timeout=180)
    assert p.returncode == 0, p.stdout + p.stderr
    response=json.loads(p.stdout)
    assert response['ok'], response
    return response['data']
assert not os.path.exists(${JSON.stringify(path.join(temporary, 'other-chat', 'private'))})
assert subprocess.run(['/bin/bash','-lc','command -v med'],capture_output=True,text=True).returncode == 0
try:
    open('/opt/medisaving/medisaving/ingest/commands.py','a').write('')
    raise AssertionError('CLI mount is writable')
except OSError:
    pass
assert not os.path.exists('/home/f3mt0/medicinas-telegram/.env')
assert med('u','lince')['districts'][0][0]=='150116'
products=['1515:3:20mg','449:3:5mg','1058:3:0.25mg']
for query,dose,expected in [('escitalopram','20mg',products[0]),('aripiprazol','5mg',products[1]),('clonazepam','0.25mg',products[2])]:
    assert expected in [row[0] for row in med('r',query,dose)['candidates']]
dataset=med('f','150116',*products,'--stats')
assert dataset['complete'] and dataset['n']>0, dataset
details=0
for product in products:
    flags=['--form','tableta sublingual'] if product==products[2] else []
    page=med('v',dataset['dataset_id'],product,'--limit','1',*flags)
    assert len(page['offers'])==1 and page['order']=='source'
    row=page['offers'][0]
    assert row['unit_price_cents'] is None or type(row['unit_price_cents']) is int
    if flags: assert row['form']=='tableta sublingual'
    assert med('d',dataset['dataset_id'],row['offer_id'])['detail_id']
    details+=1
warm=med('f','150116',*products,'--stats')
assert warm['stats']['requests']==0 and warm['stats']['cache_hits']==3
print(json.dumps({'sandbox':'ok','readonly_cli':True,'chat_isolation':True,'offers':dataset['n'],'details':details,'warm_requests':0,'llm_calls':0,'telegram_sends':0}))
`;
try {
  const result = spawnSync('/usr/bin/bwrap', [...sandboxArgs(temporary), '/usr/bin/python3', '-c', script], {
    env: { PATH: '/usr/bin:/bin', HOME: os.homedir(), LANG: 'C.UTF-8', TZ: 'America/Lima' },
    encoding: 'utf8', timeout: 240000,
  });
  process.stdout.write(result.stdout || '');
  process.stderr.write(result.stderr || '');
  if (result.error) throw result.error;
  process.exitCode = result.status === 0 ? 0 : 1;
} finally {
  fs.rmSync(temporary, { recursive: true, force: true });
}
