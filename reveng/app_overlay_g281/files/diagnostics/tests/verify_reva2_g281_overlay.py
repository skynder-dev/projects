#!/usr/bin/env python3
"""G281 overlay verifier: (1) lineage - every frozen G280 file is byte-identical unless declared modified; nothing removed; every extra file is declared;
(2) the overlay tests pass. Offline, no network, no spend."""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
res = []
def ck(name, ok, detail=''): res.append({'name': name, 'ok': bool(ok), 'detail': str(detail)[:300]})
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
BASE = json.loads((ROOT / 'docs/REVA2_POST_G280_WINDOWS_CLOSURE_MANIFEST.json').read_text(encoding='utf-8'))
OV = json.loads((ROOT / 'docs/REVA2_G281_OVERLAY_MANIFEST.json').read_text(encoding='utf-8'))
base = {f['path']: f['sha256'] for f in BASE['files']}
own, bman = 'docs/REVA2_G281_OVERLAY_MANIFEST.json', 'docs/REVA2_POST_G280_WINDOWS_CLOSURE_MANIFEST.json'
cur = {}
for p in ROOT.rglob('*'):
    rel = p.relative_to(ROOT).as_posix()
    if not p.is_file() or rel in (own, bman): continue
    if '__pycache__' in p.parts and rel not in base: continue
    cur[rel] = p
declared_mod = {m['path']: m for m in OV['modified']}; declared_add = {a['path']: a for a in OV['added']}
ck('baseline_manifest_is_g280', BASE['sourceSha256'] == OV['baseline']['sourceSha256'] and BASE['fileCountExcludingManifest'] == OV['baseline']['fileCount'])
ck('nothing_removed', not (set(base) - set(cur)) and not OV['removed'], sorted(set(base) - set(cur))[:5])
undeclared_mod = [p for p in set(cur) & set(base) if sha(cur[p]) != base[p] and p not in declared_mod]
ck('no_undeclared_modification_of_g280_files', not undeclared_mod, sorted(undeclared_mod)[:5])
ck('declared_modifications_match', all(p in cur and sha(cur[p]) == m['sha256'] and m['baselineSha256'] == base.get(p) for p, m in declared_mod.items()))
undeclared_add = sorted(set(cur) - set(base) - set(declared_add))
ck('no_undeclared_added_files', not undeclared_add, undeclared_add[:5])
ck('declared_additions_match', all(p in cur and sha(cur[p]) == a['sha256'] and cur[p].stat().st_size == a['size'] for p, a in declared_add.items()))
ck('counts_consistent', OV['counts'] == {'added': len(OV['added']), 'modified': len(OV['modified']), 'removed': len(OV['removed'])})
ck('only_index_html_modified', sorted(declared_mod) == ['app/index.html'])
# overlay tests
tests = sorted((ROOT / 'diagnostics/tests').glob('reva2_g281_*.mjs'))
for t in tests:
    r = subprocess.run(['node', str(t)], capture_output=True, text=True, timeout=120); ck(t.name, r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1:] )
r = subprocess.run([sys.executable, str(ROOT / 'diagnostics/tests/test_reva2_g281_global_ranking_page.py')], capture_output=True, text=True, timeout=240)
ck('test_reva2_g281_global_ranking_page.py', r.returncode == 0, r.stdout[-200:] + r.stderr[-200:])
failed = [x for x in res if not x['ok']]
print(json.dumps({'status': 'PASS' if not failed else 'FAIL', 'passed': len(res) - len(failed), 'total': len(res), 'failures': failed}, indent=1))
sys.exit(1 if failed else 0)
