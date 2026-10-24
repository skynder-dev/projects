from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[3]
manifest=json.loads((root/'FILE_MANIFEST.json').read_bytes())
# Own only the proposed CI subtree/workflow names. An existing monorepo may
# contain unrelated files; they must neither be read nor changed by this check.
owned={p.relative_to(root).as_posix()for p in (root/'.ci/test-only').rglob('*')if p.is_file()}
owned|={p.relative_to(root).as_posix()for p in (root/'.github/workflows').glob('test-only-*.yml')}
# Canonical ResearchLocal is an owned source boundary, not the legacy Node/overlay.
for canonical in ['reveng/ResearchLocal','reveng/tests','forge/tests','social/socialreel','social/tests','.ci/tests']:
 owned|={p.relative_to(root).as_posix()for p in (root/canonical).rglob('*')if p.is_file()}
owned.add('reveng/RESEARCH_LOCAL_SOURCE_MANIFEST.json');owned.add('forge/tools/build_release.py');owned.add('social/CONCEPT_CORE_OFFLINE.md')
expected={n for n in manifest if n.startswith(('.ci/test-only/','.github/workflows/test-only-','reveng/ResearchLocal/','reveng/tests/','forge/tests/','social/socialreel/','social/tests/','.ci/tests/'))or n in ['reveng/RESEARCH_LOCAL_SOURCE_MANIFEST.json','forge/tools/build_release.py','social/CONCEPT_CORE_OFFLINE.md']}
assert owned==expected
for name,h in manifest.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h,name
print('PASS exact CI package inventory and hashes; unrelated repository files ignored')
