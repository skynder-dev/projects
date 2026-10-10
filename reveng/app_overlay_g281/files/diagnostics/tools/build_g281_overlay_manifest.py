#!/usr/bin/env python3
"""Write docs/REVA2_G281_OVERLAY_MANIFEST.json: the exact difference between this tree and the frozen G280 closure manifest."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
BASE = json.loads((ROOT / 'docs/REVA2_POST_G280_WINDOWS_CLOSURE_MANIFEST.json').read_text(encoding='utf-8'))
OWN = 'docs/REVA2_G281_OVERLAY_MANIFEST.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
BASE_MANIFEST = 'docs/REVA2_POST_G280_WINDOWS_CLOSURE_MANIFEST.json'  # the baseline manifest does not list itself
def tree(base):
    out = {}
    for p in ROOT.rglob('*'):
        rel = p.relative_to(ROOT).as_posix()
        if not p.is_file() or rel in (OWN, BASE_MANIFEST): continue
        if '__pycache__' in p.parts and rel not in base: continue  # bytecode created by running tests is not part of the package
        out[rel] = p
    return out
def main():
    base = {f['path']: f['sha256'] for f in BASE['files']}; cur = tree(base)
    added = sorted(set(cur) - set(base)); removed = sorted(set(base) - set(cur))
    modified = sorted(p for p in set(cur) & set(base) if sha(cur[p]) != base[p])
    row = lambda p, extra=None: {'path': p, 'size': cur[p].stat().st_size, 'sha256': sha(cur[p]), **(extra or {})}
    out = {'contract': 'reveng_g281_overlay_manifest_v1', 'baseline': {'artifact': BASE['sourceArtifact'], 'sourceSha256': BASE['sourceSha256'], 'manifest': 'docs/REVA2_POST_G280_WINDOWS_CLOSURE_MANIFEST.json', 'fileCount': BASE['fileCountExcludingManifest']},
           'removed': removed, 'added': [row(p) for p in added], 'modified': [row(p, {'baselineSha256': base[p]}) for p in modified],
           'counts': {'added': len(added), 'modified': len(modified), 'removed': len(removed)}}
    (ROOT / OWN).write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    print(out['counts'])
if __name__ == '__main__': main()
