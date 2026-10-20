from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[3]
manifest=json.loads((root/'FILE_MANIFEST.json').read_bytes())
# Own only the proposed CI subtree/workflow names. An existing monorepo may
# contain unrelated files; they must neither be read nor changed by this check.
owned={p.relative_to(root).as_posix()for p in (root/'.ci/test-only').rglob('*')if p.is_file()}
owned|={p.relative_to(root).as_posix()for p in (root/'.github/workflows').glob('test-only-*.yml')}
expected={n for n in manifest if n.startswith(('.ci/test-only/','.github/workflows/test-only-'))}
assert owned==expected
for name,h in manifest.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h,name
print('PASS exact CI package inventory and hashes; unrelated repository files ignored')
