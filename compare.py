"""Measured parsing and practical Python baseline comparison; synthetic logs only."""
import json,subprocess,sys,tempfile,time,shutil
from pathlib import Path
import eli

DUPLICATE_KEY_FIXTURE=(b'{"stream_id":"s","operation_id":"op","sequence":1,"sequence":1,"event_type":"STARTED","log_version":"1"}\n'
 b'{"stream_id":"s","operation_id":"op","sequence":2,"event_type":"COMPLETED","result":true,"log_version":"1"}\n')

def python_baseline(path):
 # Independent fixed-field baseline checks structure, per-stream sequences,
 # operation lifecycles, resolution evidence and completion results.
 transitions={'STARTED':{'RETRY','UNKNOWN','COMPLETED','HOLD'},'RETRY':{'RETRY','UNKNOWN','COMPLETED','HOLD'},'UNKNOWN':{'RESOLVED','HOLD'},'RESOLVED':{'COMPLETED','HOLD'},'COMPLETED':set(),'HOLD':set()}
 last={};states={};issues=[]
 try:
  for line in path.read_text(encoding='utf-8').splitlines():
   x=json.loads(line);s=x['stream_id'];o=x['operation_id'];n=x['sequence'];event=x['event_type'];key=(s,o)
   if type(n) is not int or n!=last.get(s,0)+1:issues.append('sequence')
   last[s]=n
   if (key not in states and event!='STARTED') or (key in states and event not in transitions.get(states[key],set())):issues.append('transition')
   if event=='COMPLETED' and x.get('result') is not True:issues.append('result')
   if event=='RESOLVED' and not x.get('evidence'):issues.append('resolution')
   states[key]=event
  if not states or any(x not in ('HOLD','COMPLETED') for x in states.values()):issues.append('incomplete')
 except (ValueError,KeyError,TypeError):issues.append('parse_or_shape')
 return {'accepted':not issues,'issues':issues}

def event(n,t,**kw):return dict(stream_id='s',sequence=n,event_type=t,operation_id='op',log_version='1',**kw)
def main():
 cases={'normal':([event(1,'STARTED'),event(2,'COMPLETED',result=True)],True),'gap':([event(1,'STARTED'),event(3,'COMPLETED',result=True)],False),'unsafe':([event(1,'STARTED'),event(2,'UNKNOWN'),event(3,'COMPLETED',result=True)],False),'result':([event(1,'STARTED'),event(2,'COMPLETED')],False),'duplicate_key':(DUPLICATE_KEY_FIXTURE,False)}
 records=[];jq=shutil.which('jq')
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'events.jsonl'
  for name,(data,expected) in cases.items():
   raw=data if isinstance(data,bytes) else ''.join(json.dumps(e)+'\n' for e in data).encode();p.write_bytes(raw)
   for mode in ['json.tool','python','eli']+(['jq'] if jq else []):
    start=time.perf_counter()
    if mode=='json.tool':
     # json.tool takes one document; invoke once per JSONL line.
     runs=[subprocess.run([sys.executable,'-m','json.tool'],input=line,capture_output=True) for line in raw.splitlines()];r={'accepted':all(x.returncode==0 for x in runs),'processes':len(runs),'scope':'syntax only, duplicate keys accepted by default'}
    elif mode=='jq':
     x=subprocess.run([jq,'-s','all(.[]; type == "object")',str(p)],capture_output=True,text=True);r={'accepted':x.returncode==0 and x.stdout.strip()=='true','scope':'JSON parsing and object shape only'}
    elif mode=='python':r=python_baseline(p)
    else:
     a=eli.inspect(p,eli.default_policy());r={'accepted':a['exit_code']==0,'exit_code':a['exit_code'],'rule_ids':[f['rule_id'] for f in a['findings']]}
    records.append({'case':name,'mode':mode,'expected_contract_accept':expected,'result':r,'contract_matched':r['accepted']==expected,'runtime_seconds':time.perf_counter()-start})
 counts={mode:{'matched':sum(r['contract_matched'] for r in records if r['mode']==mode),'total':sum(r['mode']==mode for r in records)} for mode in sorted({r['mode'] for r in records})}
 return {'counts':counts,'records':records,'jq_status':'EXECUTED' if jq else 'NOT_INSTALLED_NOT_RUN','human_work_seconds':None,'limits':'Parsing tools do not implement lifecycle contracts. Python baseline supports fixed field names and basic contracts; ELI adds configured mappings, versions, bounds, source positions and external hash comparison. Timings include subprocess startup for parser tools; not a speed comparison.','source_physical_lines':{n:len(Path(n).read_text().splitlines()) for n in ('eli.py','compare.py')},'reproduction_commands':1}
if __name__=='__main__':print(json.dumps(main(),indent=2))
