"""Opt-in live ingestion benchmark; reads an existing rollout, never starts an LLM.

Run using uv run --no-project --with tiktoken python tests/ingest/benchmark.py.
"""
import argparse,hashlib,json,subprocess,sys,time,tempfile
from pathlib import Path
import tiktoken
enc=tiktoken.get_encoding('o200k_base')
parser=argparse.ArgumentParser()
parser.add_argument('--rollout', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--start', default='2026-09-12T18:35:06.233Z')
parser.add_argument('--end', default='2026-09-12T18:40:49.860Z')
args=parser.parse_args()
events=[json.loads(l) for l in open(args.rollout)]
start=args.start
prior=final=None
old_outputs=[]
for event in events:
 if event.get('timestamp','') > args.end: continue
 p=event.get('payload',{})
 if p.get('type')=='token_count' and p.get('info'):
  final=p['info']['total_token_usage']
  if event['timestamp']<start: prior=final
 if event['timestamp']>=start and p.get('type') in ('custom_tool_call_output','function_call_output'):
  text=p.get('output',''); old_outputs.append(text if isinstance(text,str) else json.dumps(text,ensure_ascii=False))
if prior is None or final is None:
 raise ValueError('Rollout must contain token usage before and after start')
summary={'historical_turn_usage':{k:final[k]-prior[k] for k in final},'historical_tool_outputs':{'count':len(old_outputs),'bytes':sum(len(x.encode()) for x in old_outputs),'o200k_tokens':sum(len(enc.encode(x)) for x in old_outputs)},'tokenizer':'o200k_base (comparison proxy, not claimed model tokenizer)','model_calls_new':0}
summary['rollout_sha256']=hashlib.sha256(Path(args.rollout).read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='ingest-benchmark-') as directory:
 def run(args):
  begin=time.perf_counter()
  p=subprocess.run([sys.executable,'-m','medisaving','--data-dir',directory,'ingest',*args],capture_output=True,text=True)
  if p.returncode: raise RuntimeError(p.stdout+p.stderr)
  return {'command':' '.join(args),'ms':round((time.perf_counter()-begin)*1000,2),'bytes':len(p.stdout.encode()),'o200k_tokens':len(enc.encode(p.stdout)),'response':json.loads(p.stdout)['data']}
 for phase in ['cold','warm']:
  measured=[]
  for args in [['u','lince'],['r','escitalopram','20mg'],['r','aripiprazol','5mg'],['r','clonazepam','0.25mg','--sl'],['f','150116','1515:3:20mg','449:3:5mg','1058:3:0.25mg','--stats']]: measured.append(run(args))
  fetched=measured[-1]['response']; dataset=json.loads(Path(directory,fetched['dataset_id']+'.json').read_text())
  # First source row per group, not price ranking. Only test acquisition of three details.
  seen=set()
  for row in dataset['offers']:
   if row['source_group'] not in seen:
    seen.add(row['source_group']); measured.append(run(['d',fetched['dataset_id'],row['offer_id']]))
  summary[phase]={'ms':round(sum(x['ms'] for x in measured),2),'bytes':sum(x['bytes'] for x in measured),'o200k_tokens':sum(x['o200k_tokens'] for x in measured),'commands':len(measured),'fetch':fetched,'steps':[{k:v for k,v in x.items() if k!='response'} for x in measured]}
  # Output-only measurement without opt-in diagnostics (no additional API call).
  minimal={'ok':True,'schema_version':1,'data':{k:v for k,v in fetched.items() if k not in ('stats','stats_id')}}
  minimal_text=json.dumps(minimal,ensure_ascii=False)+'\n'
  summary[phase]['fetch_default']={'bytes':len(minimal_text.encode()),'o200k_tokens':len(enc.encode(minimal_text))}
Path(args.output).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
