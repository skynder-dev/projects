"""Synthetic manifest failure tests; never modify real product sources."""
from pathlib import Path
import hashlib,json,tempfile,unittest
from canonical_source import verify_researchlocal

class CanonicalSourceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='canonical-contract-');self.addCleanup(self.temp.cleanup)
  self.repo=Path(self.temp.name);self.root=self.repo/'reveng/ResearchLocal';self.root.mkdir(parents=True)
  self.file=self.root/'example.py';self.file.write_bytes(b'# synthetic\n')
  content=self.file.read_bytes();self.row={'path':'reveng/ResearchLocal/example.py','bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()};self.save([self.row])
 def save(self,rows):
  (self.repo/'reveng/RESEARCH_LOCAL_SOURCE_MANIFEST.json').write_text(json.dumps({'files':rows}),encoding='utf-8')
 def test_returns_canonical_not_snapshot(self):self.assertEqual(verify_researchlocal(self.repo),self.root)
 def test_tampered_source_fails(self):
  self.file.write_bytes(b'# changed\n')
  with self.assertRaises(AssertionError):verify_researchlocal(self.repo)
 def test_missing_source_never_falls_back(self):
  historical=self.repo/'.ci/test-only/production/reveng028/ResearchLocal';historical.mkdir(parents=True);(historical/'example.py').write_bytes(self.file.read_bytes());self.file.unlink()
  with self.assertRaises(FileNotFoundError):verify_researchlocal(self.repo)
 def test_unlisted_file_fails(self):
  (self.root/'unexpected.py').write_bytes(b'# synthetic extra\n')
  with self.assertRaises(AssertionError):verify_researchlocal(self.repo)
 def test_duplicate_manifest_entry_fails(self):
  self.save([self.row,self.row])
  with self.assertRaises(ValueError):verify_researchlocal(self.repo)
 def test_escaping_manifest_path_fails(self):
  self.save([dict(self.row,path='../outside.py')])
  with self.assertRaises(ValueError):verify_researchlocal(self.repo)

if __name__=='__main__':unittest.main(verbosity=2)
