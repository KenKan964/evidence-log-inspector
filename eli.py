"""Deterministic, read-only JSONL contract inspection. Standard library only."""
import argparse,csv,hashlib,io,json,math,os,re,sys
from pathlib import Path
VERSION='0.1.0'
MAX_LINE=65536
MAX_EVENTS=10000
MAX_BYTES=10000000
MAX_DEPTH=32
FIELDS=['stream_id','sequence','event_type','operation_id','log_version','result','evidence','timestamp']
TRANSITIONS={'STARTED':['RETRY','UNKNOWN','COMPLETED','HOLD'],'RETRY':['RETRY','UNKNOWN','COMPLETED','HOLD'],'UNKNOWN':['RESOLVED','HOLD'],'RESOLVED':['COMPLETED','HOLD'],'HOLD':[],'COMPLETED':[]}
def unique(items):
 d={}
 for k,v in items:
  if k in d:raise ValueError('duplicate_json_key')
  d[k]=v
 return d

def parse(data):
 # Bound nesting before parsing, respecting JSON string escapes.
 depth=0;quoted=False;escape=False
 for c in data:
  if quoted:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':quoted=False
  elif c=='"':quoted=True
  elif c in '[{':
   depth+=1
   if depth>MAX_DEPTH:raise ValueError('depth_limit')
  elif c in ']}':depth-=1
 def finite_float(value):
  result=float(value)
  if not math.isfinite(result):raise ValueError('nonfinite_json')
  return result
 return json.loads(data,object_pairs_hook=unique,parse_float=finite_float,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_json')))

def policy_validate(p):
 if not isinstance(p,dict) or set(p)!={'policy_version','rule_version','log_version','fields','sequence_start','same_clock','transitions'}:raise ValueError('policy_fields')
 if type(p['policy_version']) is not int or p['policy_version']!=1 or p['rule_version']!='eli-rules-v1':raise ValueError('unsupported_rule_version')
 if not isinstance(p['log_version'],str) or not p['log_version']:raise ValueError('log_version')
 if not isinstance(p['fields'],dict) or set(p['fields'])!=set(FIELDS) or not all(isinstance(x,str) and x for x in p['fields'].values()) or len(set(p['fields'].values()))!=len(FIELDS):raise ValueError('field_mapping')
 if type(p['sequence_start']) is not int or p['sequence_start']<0 or type(p['same_clock']) is not bool:raise ValueError('sequence_clock_policy')
 t=p['transitions']
 if not isinstance(t,dict) or set(t)!=set(TRANSITIONS):raise ValueError('unknown_state_rule')
 for k,v in t.items():
  if not isinstance(v,list) or not all(isinstance(x,str) and x in TRANSITIONS[k] for x in v) or len(v)!=len(set(v)):raise ValueError('unsafe_or_unknown_transition')
 return p

def default_policy():return {'policy_version':1,'rule_version':'eli-rules-v1','log_version':'1','fields':{x:x for x in FIELDS},'sequence_start':1,'same_clock':False,'transitions':TRANSITIONS}
def identity(v):return isinstance(v,str) and 0<len(v)<=128 and all(ord(c)>=32 and not 0xD800<=ord(c)<=0xDFFF for c in v)
def inspect(log,policy,expected_sha256=None):
 report={'schema_version':'eli-report-v1','tool_version':VERSION,'rule_version':None,'log_version':None,'status':'UNVERIFIABLE','exit_code':2,'findings':[],'hash_verification':'NOT_VERIFIED','scope':'Only supplied bytes and declared stream contracts; no proof of unlogged events, external missing files or global host ordering.','events':0,'operations':[]}
 file=str(Path(log));findings=report['findings'];unverifiable=False
 def add(code,line=0,op=None,stream=None,**evidence):
  findings.append({'rule_id':code,'file':file,'line':line,'operation_id':op,'stream_id':stream,'evidence':evidence})
 try:
  policy_validate(policy);report['rule_version']=policy['rule_version'];report['log_version']=policy['log_version']
  if expected_sha256 is not None and not re.fullmatch('[0-9a-fA-F]{64}',expected_sha256):raise ValueError('external_hash_format')
  h=hashlib.sha256();total=0;last={};seen={};clock={};ops={};f=policy['fields']
  with open(log,'rb') as source:
   for lineno in range(1,MAX_EVENTS+2):
    raw=source.readline(MAX_LINE+1)
    if not raw:break
    total+=len(raw);h.update(raw)
    if len(raw)>MAX_LINE or total>MAX_BYTES or lineno>MAX_EVENTS:
     add('RESOURCE_LIMIT',lineno,limit='line_bytes/total_bytes/events');unverifiable=True;break
    try:
     text=raw.decode('utf-8',errors='strict')
     if not text.strip():raise ValueError('blank_line')
     obj=parse(text)
     if not isinstance(obj,dict):raise ValueError('event_must_be_object')
    except (ValueError,RecursionError) as e:
     add('INVALID_JSONL',lineno,reason=str(e) if isinstance(e,ValueError) and str(e) in ('blank_line','duplicate_json_key','depth_limit','nonfinite_json','event_must_be_object') else type(e).__name__);unverifiable=True;continue
    report['events']+=1
    stream=obj.get(f['stream_id']);op=obj.get(f['operation_id']);seq=obj.get(f['sequence']);event=obj.get(f['event_type'])
    if not identity(stream) or not identity(op) or type(seq) is not int or seq<0 or not isinstance(event,str):
     add('INVALID_FIELD_TYPE',lineno);unverifiable=True;continue
    if obj.get(f['log_version'])!=policy['log_version']:
     add('LOG_VERSION_MISMATCH',lineno,op,stream);unverifiable=True;continue
    if event not in TRANSITIONS:
     add('UNKNOWN_EVENT',lineno,op,stream);unverifiable=True;continue
    if stream not in seen:seen[stream]=set()
    if seq in seen[stream]:add('DUPLICATE_SEQUENCE',lineno,op,stream,sequence=seq)
    if stream in last:
     if seq<last[stream]:add('SEQUENCE_REGRESSION',lineno,op,stream,previous=last[stream],observed=seq)
     elif seq>last[stream]+1:add('SEQUENCE_GAP',lineno,op,stream,expected=last[stream]+1,observed=seq)
    elif seq!=policy['sequence_start']:add('SEQUENCE_START',lineno,op,stream,expected=policy['sequence_start'],observed=seq)
    seen[stream].add(seq);last[stream]=seq
    if policy['same_clock']:
     stamp=obj.get(f['timestamp'])
     if type(stamp) not in (int,float) or not math.isfinite(stamp):add('INVALID_TIMESTAMP',lineno,op,stream);unverifiable=True
     else:
      if stream in clock and stamp<clock[stream]:add('TIMESTAMP_REGRESSION',lineno,op,stream,previous=clock[stream],observed=stamp)
      clock[stream]=stamp
    key=(stream,op);previous=ops.get(key)
    if previous is None:
     if event!='STARTED':add('MISSING_START',lineno,op,stream,event=event)
    elif event not in policy['transitions'][previous['state']]:add('FORBIDDEN_TRANSITION',lineno,op,stream,previous=previous['state'],event=event)
    # Always advance observed state, but findings remain sticky.
    ops[key]={'state':event,'line':lineno}
    if event=='COMPLETED' and obj.get(f['result']) is not True:add('MISSING_RESULT',lineno,op,stream)
    if event=='RESOLVED' and not identity(obj.get(f['evidence'])):add('MISSING_RESOLUTION_EVIDENCE',lineno,op,stream)
  report['input_sha256']=h.hexdigest();report['bytes_read']=total
  if expected_sha256:
   if any(x['rule_id']=='RESOURCE_LIMIT' for x in findings):report['hash_verification']='INCOMPLETE_INPUT'
   elif h.hexdigest().lower()!=expected_sha256.lower():report['hash_verification']='MISMATCH';add('EXTERNAL_HASH_MISMATCH')
   else:report['hash_verification']='MATCH_ASSUMING_TRUSTED_EXTERNAL_HASH'
  if report['events']==0:add('EMPTY_OR_UNREADABLE_LOG');unverifiable=True
  for (stream,op),state in sorted(ops.items()):
   report['operations'].append({'stream_id':stream,'operation_id':op,'final_state':state['state']})
   if state['state'] not in ('COMPLETED','HOLD'):add('INCOMPLETE_OPERATION',state['line'],op,stream,state=state['state']);unverifiable=True
  report['exit_code']=2 if unverifiable else int(bool(findings));report['status']=('CONSISTENT_WITH_POLICY' if not any(x['final_state']=='HOLD' for x in report['operations']) else 'HOLD') if report['exit_code']==0 else ('VIOLATION' if report['exit_code']==1 else 'UNVERIFIABLE')
 except (OSError,ValueError,TypeError,OverflowError) as e:
  add('UNVERIFIABLE',reason=type(e).__name__);report['exit_code']=2
 return report

def csv_text(report):
 out=io.StringIO(newline='');w=csv.writer(out);w.writerow(['rule_id','file','line','stream_id','operation_id','evidence'])
 def safe(v):
  s='' if v is None else str(v)
  return "'"+s if s.startswith(('=','+','-','@','\t','\r')) else s
 for f in report['findings']:w.writerow([safe(f[k]) for k in ('rule_id','file','line','stream_id','operation_id')]+[safe(json.dumps(f['evidence'],ensure_ascii=False,sort_keys=True))])
 return out.getvalue()
class Parser(argparse.ArgumentParser):
 def error(self,message):raise ValueError('invalid_arguments')
def main(argv=None):
 try:
  a=Parser();a.add_argument('--log',required=True);a.add_argument('--policy',required=True);a.add_argument('--out',required=True);a.add_argument('--expected-sha256');args=a.parse_args(argv)
  path=Path(args.policy)
  if path.stat().st_size>65536:raise ValueError('policy_size')
  policy=parse(path.read_text(encoding='utf-8'));r=inspect(args.log,policy,args.expected_sha256)
  out=Path(args.out);out.mkdir(mode=0o700)
  (out/'report.json').write_text(json.dumps(r,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
  (out/'findings.csv').write_text(csv_text(r),encoding='utf-8',newline='')
 except (OSError,ValueError,TypeError,RecursionError):
  r={'schema_version':'eli-report-v1','status':'UNVERIFIABLE','exit_code':2,'findings':[{'rule_id':'INPUT_OR_OUTPUT_ERROR','file':None,'line':0,'operation_id':None,'stream_id':None,'evidence':{}}]}
 print(json.dumps(r,ensure_ascii=True,sort_keys=True));return r['exit_code']
if __name__=='__main__':sys.exit(main())
