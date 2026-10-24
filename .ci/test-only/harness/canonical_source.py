"""Verify canonical ResearchLocal source; no fallback to historical CI snapshots."""
from pathlib import Path
import hashlib,json

def verify_researchlocal(repo):
    repo=Path(repo).resolve()
    manifest=json.loads((repo/'reveng/RESEARCH_LOCAL_SOURCE_MANIFEST.json').read_bytes())
    root=repo/'reveng/ResearchLocal'
    expected={}
    for row in manifest['files']:
        name=row['path']
        path=repo/name
        if not path.resolve().is_relative_to(repo/'reveng'):
            raise ValueError('Canonical manifest path escapes reveng')
        if name in expected:raise ValueError('Duplicate canonical manifest path')
        expected[name]=row['sha256']
        content=path.read_bytes()
        if len(content)!=row['bytes'] or hashlib.sha256(content).hexdigest()!=row['sha256']:
            raise AssertionError('Canonical source hash mismatch: '+name)
    actual={p.relative_to(repo).as_posix() for p in root.rglob('*') if p.is_file()}
    required={name for name in expected if name.startswith('reveng/ResearchLocal/')}
    if not required or actual!=required:raise AssertionError('Canonical source inventory mismatch')
    return root
