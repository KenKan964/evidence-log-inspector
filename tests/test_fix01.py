import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
import eli,compare
from test_acceptance import preserve_evidence
ROOT=Path(eli.__file__).parent
class Fix01(unittest.TestCase):
 def conflict(self,kind):
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);dest=base/'evidence';dest.mkdir();marker=base/'marker';marker.write_bytes(b'FIX01 SYNTHETIC DO NOT OVERWRITE');target=dest/'normal.json'
   if kind=='existing':target.write_bytes(marker.read_bytes())
   elif kind=='file_symlink':
    try:target.symlink_to(marker)
    except OSError:self.skipTest('symlink unavailable')
   else:
    dest.rmdir()
    try:dest.symlink_to(base/'real',target_is_directory=True);(base/'real').mkdir()
    except OSError:self.skipTest('symlink unavailable')
   protected=target if kind=='existing' else marker;before=hashlib.sha256(protected.read_bytes()).hexdigest()
   r=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_acceptance.py','-v'],cwd=ROOT,env=dict(os.environ,ELI_EVIDENCE=str(dest)),capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertEqual(hashlib.sha256(protected.read_bytes()).hexdigest(),before)
   if kind=='directory_symlink':self.assertEqual(list((base/'real').iterdir()),[])
   preserve_evidence('FIX01_'+kind,{'returncode':r.returncode,'before_sha256':before,'after_sha256':hashlib.sha256(protected.read_bytes()).hexdigest(),'stdout':r.stdout,'stderr':r.stderr})
 def test_existing_evidence(self):self.conflict('existing')
 def test_file_symlink(self):self.conflict('file_symlink')
 def test_directory_symlink(self):self.conflict('directory_symlink')
 def test_clean_duplicate_fixture(self):
  # Standard parsing shows an otherwise valid series: baseline accepts it.
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'log';path.write_bytes(compare.DUPLICATE_KEY_FIXTURE)
   self.assertTrue(compare.python_baseline(path)['accepted']);r=eli.inspect(path,eli.default_policy());self.assertEqual(r['exit_code'],2);self.assertIn('INVALID_JSONL',[f['rule_id'] for f in r['findings']]);preserve_evidence('FIX01_duplicate_fixture',r)
