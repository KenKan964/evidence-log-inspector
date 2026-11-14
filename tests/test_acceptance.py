import copy,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
import eli

def preserve_evidence(name,data):
 if not os.environ.get('ELI_EVIDENCE'):return
 dest=Path(os.path.abspath(os.environ['ELI_EVIDENCE']))
 if any(p.is_symlink() for p in [dest,*dest.parents]):raise ValueError('symlink evidence path rejected')
 dest.mkdir(parents=True,exist_ok=True)
 with (dest/(name+'.json')).open('x',encoding='utf-8') as f:
  json.dump(data,f,ensure_ascii=True,indent=2)

def e(seq,event,stream='s',op='op',**kw):return dict(stream_id=stream,operation_id=op,sequence=seq,event_type=event,log_version='1',**kw)
def encode(events):return ''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in events).encode()
NORMAL=[e(1,'STARTED'),e(2,'COMPLETED',result=True)]
CASES=[
('normal',NORMAL,0,None),
('multistream',[e(1,'STARTED'),e(1,'STARTED','t'),e(2,'COMPLETED','t',result=True),e(2,'COMPLETED',result=True)],0,None),
('retry',[e(1,'STARTED'),e(2,'RETRY'),e(3,'COMPLETED',result=True)],0,None),
('hold',[e(1,'STARTED'),e(2,'UNKNOWN'),e(3,'HOLD')],0,None),
('unicode',[e(1,'STARTED',op='操作'),e(2,'COMPLETED',op='操作',result=True)],0,None),
('empty',b'',2,'EMPTY_OR_UNREADABLE_LOG'),
('gap',[e(1,'STARTED'),e(3,'COMPLETED',result=True)],1,'SEQUENCE_GAP'),
('duplicate',[e(1,'STARTED'),e(1,'COMPLETED',result=True)],1,'DUPLICATE_SEQUENCE'),
('regression',[e(1,'STARTED'),e(2,'RETRY'),e(1,'COMPLETED',result=True)],1,'SEQUENCE_REGRESSION'),
('transition',[e(1,'STARTED'),e(2,'STARTED'),e(3,'COMPLETED',result=True)],1,'FORBIDDEN_TRANSITION'),
('noresult',[e(1,'STARTED'),e(2,'COMPLETED')],1,'MISSING_RESULT'),
('unsafe_unknown',[e(1,'STARTED'),e(2,'UNKNOWN'),e(3,'COMPLETED',result=True)],1,'FORBIDDEN_TRANSITION'),
('resolve',[e(1,'STARTED'),e(2,'UNKNOWN'),e(3,'RESOLVED',evidence='receipt-1'),e(4,'COMPLETED',result=True)],0,None),
('noevidence',[e(1,'STARTED'),e(2,'UNKNOWN'),e(3,'RESOLVED'),e(4,'COMPLETED',result=True)],1,'MISSING_RESOLUTION_EVIDENCE'),
('badjson',b'{bad}\n',2,'INVALID_JSONL'),
('duplicate_json',b'{"x":1,"x":2}\n',2,'INVALID_JSONL'),
('encoding',b'\xff\n',2,'INVALID_JSONL'),
('blank',b'\n',2,'INVALID_JSONL'),
('array',b'[]\n',2,'INVALID_JSONL'),
('bool_seq',[e(True,'STARTED')],2,'INVALID_FIELD_TYPE'),
('surrogate',b'{"stream_id":"s","sequence":1,"event_type":"STARTED","operation_id":"\\ud800","log_version":"1"}\n',2,'INVALID_FIELD_TYPE'),
('unknown',[e(1,'MYSTERY')],2,'UNKNOWN_EVENT'),
('version',[dict(e(1,'STARTED'),log_version='9')],2,'LOG_VERSION_MISMATCH'),
('missing_start',[e(1,'COMPLETED',result=True)],1,'MISSING_START'),
('incomplete',[e(1,'STARTED')],2,'INCOMPLETE_OPERATION'),
('timestamp',[e(1,'STARTED',timestamp=2),e(2,'COMPLETED',timestamp=1,result=True)],1,'TIMESTAMP_REGRESSION'),
('noclock',[e(1,'STARTED',timestamp=2),e(2,'COMPLETED',timestamp=1,result=True)],0,None),
('bigline',b' '*(eli.MAX_LINE+1)+b'\n',2,'RESOURCE_LIMIT'),
('deep',b'['*33+b'0'+b']'*33+b'\n',2,'INVALID_JSONL'),
('nonfinite',b'{"a":NaN}\n',2,'INVALID_JSONL'),
('overflow',b'{"a":1e999}\n',2,'INVALID_JSONL'),
('hashmatch',NORMAL,0,None),
('hashwrong',NORMAL,1,'EXTERNAL_HASH_MISMATCH'),
('unknown_rule',NORMAL,2,'UNVERIFIABLE'),
('unsafe_policy',NORMAL,2,'UNVERIFIABLE'),
('mapping',NORMAL,0,None),
('external_url',[e(1,'STARTED',url='https://invalid.example/do-not-open',command='touch /tmp/eli-never'),e(2,'COMPLETED',result=True,secret='PRIVATE-NEVER-REPORT')],0,None),
('false_result',[e(1,'STARTED'),e(2,'COMPLETED',result=False)],1,'MISSING_RESULT'),
('firstseq',[e(4,'STARTED'),e(5,'COMPLETED',result=True)],1,'SEQUENCE_START'),
]
class Acceptance(unittest.TestCase):pass
def make(name,events,exit_code,code):
 def test(self):
  with tempfile.TemporaryDirectory() as td:
   log=Path(td)/'log.jsonl';p=copy.deepcopy(eli.default_policy());raw=events if isinstance(events,bytes) else encode(events)
   if name=='timestamp':p['same_clock']=True
   if name=='unknown_rule':p['rule_version']='unknown'
   if name=='unsafe_policy':p['transitions']['UNKNOWN'].append('COMPLETED')
   if name=='mapping':
    p['fields']={k:'x_'+k for k in eli.FIELDS};raw=encode([{'x_'+k:v for k,v in x.items()} for x in events])
   log.write_bytes(raw);before=hashlib.sha256(raw).hexdigest();external=before if name=='hashmatch' else '0'*64 if name=='hashwrong' else None
   r=eli.inspect(log,p,external);self.assertEqual(r['exit_code'],exit_code,r)
   if code:self.assertIn(code,[f['rule_id'] for f in r['findings']],r)
   self.assertEqual(before,hashlib.sha256(log.read_bytes()).hexdigest());self.assertEqual(r,eli.inspect(log,p,external))
   if name=='hashmatch':self.assertEqual(r['hash_verification'],'MATCH_ASSUMING_TRUSTED_EXTERNAL_HASH')
   elif name!='hashwrong':self.assertEqual(r['hash_verification'],'NOT_VERIFIED')
   if name=='gap':
    f=next(x for x in r['findings'] if x['rule_id']=='SEQUENCE_GAP');self.assertEqual(f['line'],2);self.assertEqual(f['file'],str(log));self.assertEqual(f['operation_id'],'op')
   if name=='external_url':self.assertNotIn('PRIVATE-NEVER-REPORT',json.dumps(r));self.assertFalse(Path('/tmp/eli-never').exists())
   preserve_evidence(name,{'expected_exit':exit_code,'expected_rule':code,'input_unchanged':True,'report':r})
 return test
for n,v,x,c in CASES:setattr(Acceptance,'test_'+n,make(n,v,x,c))
class CLI(unittest.TestCase):
 def test_outputs_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);(base/'log').write_bytes(encode(NORMAL));(base/'policy').write_text(json.dumps(eli.default_policy()));cmd=[sys.executable,str(Path(eli.__file__)), '--log',str(base/'log'),'--policy',str(base/'policy'),'--out',str(base/'out')]
   r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertTrue((base/'out/findings.csv').exists());before=(base/'out/report.json').read_bytes()
   r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['exit_code'],2);self.assertEqual((base/'out/report.json').read_bytes(),before)
 def test_bad_args_json(self):
  r=subprocess.run([sys.executable,eli.__file__,'--invalid'],capture_output=True,text=True);self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['exit_code'],2)
 def test_csv_formula(self):
  r={'findings':[{'rule_id':'GAP','file':'=cmd','line':2,'stream_id':'@x','operation_id':'+x','evidence':{}}]};self.assertIn("'=cmd",eli.csv_text(r))
 def test_count_limit(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'log';p.write_bytes(encode([e(i,'RETRY') for i in range(1,eli.MAX_EVENTS+2)]));r=eli.inspect(p,eli.default_policy());self.assertEqual(r['exit_code'],2);self.assertIn('RESOURCE_LIMIT',[x['rule_id'] for x in r['findings']])
