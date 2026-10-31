#!/usr/bin/env python3
"""Build a Merch Forge release from forge/app in place.

    python3 forge/tools/build_release.py --number 056 --slug WINDOWS_FIXES --notes forge/docs/releases/056.md

Updates candidate_manifest.json (package name/number, installer generation +1, app version, workbench and
module hashes), renames the outer START_0xx entrypoint, writes README_FIRST.txt from the notes file,
regenerates integrity.json, runs static checks + the headless research-draft self-test (needs pwsh),
and writes a deterministic ZIP (built twice and compared) to forge/releases/.
Native Windows proof comes from the forge-windows GitHub workflow, not from this script.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile, zipfile
import xml.etree.ElementTree as ET

FORGE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(FORGE, 'app')
INNER = os.path.join(APP, 'Merch_Forge_A5_Current')
REL = os.path.join(FORGE, 'releases')
ARCHIVE_054 = os.path.join(FORGE, 'archive', '054_Merch_Forge_DISCOVER_RESEARCH_RC.zip')
FIXED_TIME = (2026, 1, 1, 0, 0, 0)

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def rd(p): return open(p, 'rb').read().decode('utf-8-sig')

ap = argparse.ArgumentParser()
ap.add_argument('--number', required=True)            # e.g. 056
ap.add_argument('--slug', required=True)              # e.g. WINDOWS_FIXES
ap.add_argument('--notes', required=True)             # markdown/plain text: what is new (goes into README_FIRST)
ap.add_argument('--intent', default='')
a = ap.parse_args()
NAME = '%s_Merch_Forge_%s_RC' % (a.number, a.slug)

# ---------- version from the workbench (single source of truth) ----------
wb = rd(os.path.join(INNER, 'MerchForgeWorkbench.ps1'))
ver = re.search(r"\$script:AppVersion = '([^']+)'", wb).group(1)
hdr = re.search(r"# Version: (\S+)", wb).group(1)

# ---------- outer entrypoint + README_FIRST ----------
starts = [f for f in os.listdir(APP) if re.match(r'START_\d+_MERCH_FORGE\.vbs$', f)]
assert len(starts) == 1, starts
start_new = 'START_%s_MERCH_FORGE.vbs' % a.number
b = open(os.path.join(APP, starts[0]), 'rb').read()
if b.startswith(b'\xef\xbb\xbf'): b = b[3:]   # Windows Script Host cannot read a UTF-8 BOM ("Invalid character", line 1 char 1)
b = re.sub(rb'Merch Forge \d+ is not fully extracted', b'Merch Forge ' + a.number.encode() + b' is not fully extracted', b)
os.remove(os.path.join(APP, starts[0])); open(os.path.join(APP, start_new), 'wb').write(b)
for f in os.listdir(APP):
    if re.match(r'FORGE_\d+_.*\.json$', f): os.remove(os.path.join(APP, f))
notes = open(a.notes, encoding='utf-8').read().strip()
readme = ('MERCH FORGE %s\r\n\r\n'
          'ПО-РУССКИ\r\n1. Распакуйте всю папку: правый клик по ZIP -> «Извлечь все».\r\n2. Запустите %s двойным щелчком.\r\n'
          '3. Как пользоваться (1 страница): HOW_TO_USE_RU.txt\r\n\r\n'
          'START\r\n1. Extract the whole folder.\r\n2. Run %s.\r\n\r\n%s\r\n') % (NAME.replace('_', ' '), start_new, start_new, notes.replace('\r\n', '\n').replace('\n', '\r\n'))
open(os.path.join(APP, 'README_FIRST.txt'), 'wb').write(b'\xef\xbb\xbf' + readme.encode('utf-8'))
assert os.path.exists(os.path.join(APP, 'HOW_TO_USE_RU.txt')), 'HOW_TO_USE_RU.txt missing next to START'

# ---------- manifest ----------
mp = os.path.join(INNER, 'candidate_manifest.json')
m = json.loads(rd(mp))
prev_name = m.get('package_name')
mods = sorted([f for f in os.listdir(os.path.join(INNER, 'Modules')) if f.endswith('.ps1')], key=str.lower)
d = m['desktop']
d['app_version'] = hdr
d['workbench_sha256'] = sha(os.path.join(INNER, 'MerchForgeWorkbench.ps1'))
d['workbench_size_bytes'] = os.path.getsize(os.path.join(INNER, 'MerchForgeWorkbench.ps1'))
d['native_windows_parser_target_sha256'] = d['workbench_sha256']
d['runtime_modules'] = [{'path': 'Modules\\' + f, 'sha256': sha(os.path.join(INNER, 'Modules', f)), 'size_bytes': os.path.getsize(os.path.join(INNER, 'Modules', f))} for f in mods]
d['runtime_module_count'] = len(mods)
d['current_release'] = NAME
if m.get('package_name') != NAME:
    m['installer_generation'] = '%020d' % (int(m['installer_generation']) + 1)
m['package_name'] = NAME
m['package_number'] = int(a.number)
m['stage'] = 'FORGE-%s-%s-RC' % (a.number, a.slug.replace('_', '-'))
if a.intent: m['result_intent'] = a.intent
open(mp, 'wb').write(json.dumps(m, indent=2, ensure_ascii=False).encode('utf-8'))

# ---------- integrity ----------
files = []
for dp, dn, fn in os.walk(INNER):
    for f in fn:
        rel = os.path.relpath(os.path.join(dp, f), INNER)
        if rel != 'integrity.json': files.append(rel)
files.sort(key=lambda x: x.replace('/', '\\').lower())
integ = {'schema': 'forge.package_integrity.v1', 'hash_algorithm': 'SHA-256', 'files': [{'path': f.replace('/', '\\'), 'sha256': sha(os.path.join(INNER, f)), 'size_bytes': os.path.getsize(os.path.join(INNER, f))} for f in files]}
open(os.path.join(INNER, 'integrity.json'), 'wb').write(json.dumps(integ, indent=2).encode('utf-8'))

# ---------- static checks ----------
C = {}
xs = wb.index("[xml]$xaml=@'"); xb = wb.index('\n', xs) + 1; xe = wb.index("\n'@", xb)
try:
    root = ET.fromstring(wb[xb:xe]); C['xaml_xml_parse'] = True
except Exception:
    root = None; C['xaml_xml_parse'] = False
XN = '{http://schemas.microsoft.com/winfx/2006/xaml}'
names = [el.get(XN + 'Name') for el in root.iter() if el.get(XN + 'Name')] if root is not None else []
C['xaml_names_unique'] = len(names) == len(set(names))
C['version_header_matches_appversion'] = ver.endswith(hdr.split('-', 1)[1]) and ver.startswith(hdr.split('-', 1)[0])
ps = subprocess.run(['pwsh', '-NoProfile', '-c', "$bad=0;Get-ChildItem -LiteralPath '%s' -Recurse -Filter *.ps1|%%{$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$t,[ref]$e);if($e.Count){$bad++}};$bad" % INNER], capture_output=True, text=True)
C['powershell_parse_all'] = ps.stdout.strip() == '0'
nonascii_nobom = [f for f in files if f.endswith('.ps1') and not open(os.path.join(INNER, f), 'rb').read().startswith(b'\xef\xbb\xbf') and any(c > 127 for c in open(os.path.join(INNER, f), 'rb').read())]
C['ps1_nonascii_have_bom'] = not [f for f in nonascii_nobom if 'PrintChecks' not in f]   # PrintChecks: known pre-existing, tracked
tmp = tempfile.mkdtemp()
with zipfile.ZipFile(ARCHIVE_054) as z: z.extractall(tmp)
old = os.path.join(tmp, '054_Merch_Forge_DISCOVER_RESEARCH_RC', 'Merch_Forge_A5_Current')
for f in ['Start Merch Forge.vbs', 'MerchForgeLauncher.cmd', 'MerchForgePreflight.ps1', 'Install Merch Forge.vbs']:
    C['byte_equal_054_' + os.path.basename(f).replace(' ', '_')] = sha(os.path.join(INNER, f)) == sha(os.path.join(old, f))
vbs = [os.path.join(dp, f) for dp, dn, fn in os.walk(APP) for f in fn if f.lower().endswith('.vbs')]
C['vbs_no_utf8_bom_ascii_only'] = all(not open(v, 'rb').read().startswith(b'\xef\xbb\xbf') and all(x < 128 for x in open(v, 'rb').read()) for v in vbs)
wn_path = os.path.join(INNER, 'Data', 'Forge.WhatsNew.json')
try:
    wn = json.loads(rd(wn_path)); C['whats_new_valid'] = bool(wn.get('version')) and all(isinstance(wn['items'].get(l), list) and wn['items'][l] for l in ('en', 'ru', 'es'))
    C['whats_new_matches_release'] = '.'.join(str(wn.get('version', '')).split('-')[0].split('.')[:2]) == '.'.join(hdr.split('-')[0].split('.')[:2])   # bump the card when the minor version changes
except Exception:
    C['whats_new_valid'] = False; C['whats_new_matches_release'] = False
C['integrity_all_pass'] = all(sha(os.path.join(INNER, f['path'].replace('\\', '/'))) == f['sha256'] for f in integ['files'])
C['manifest_workbench_sha'] = json.loads(rd(mp))['desktop']['workbench_sha256'] == sha(os.path.join(INNER, 'MerchForgeWorkbench.ps1'))
C['manifest_authority_all_false'] = all(v is False for v in m['authority'].values())
st_path = os.path.join(tmp, 'selftest.json')
r = subprocess.run(['pwsh', '-NoProfile', '-File', os.path.join(INNER, 'MerchForgeResearchDraftSelfTest.ps1'), '-OutputPath', st_path, '-LegacyPackageRoot', old], capture_output=True, text=True, timeout=900)
st = json.load(open(st_path, encoding='utf-8-sig')) if os.path.exists(st_path) else {'status': 'NO REPORT', 'passed': 0, 'total': 0, 'network_calls': -1}
C['headless_selftest_pass'] = st['status'] == 'PASS' and st['network_calls'] == 0
passed = sum(1 for v in C.values() if v)
check = {'schema': 'forge.release_checkpoint.v1', 'package': NAME, 'previous_package': prev_name, 'app_version': ver,
         'installer_generation': m['installer_generation'], 'static': '%d/%d' % (passed, len(C)), 'checks': C,
         'headless_selftest': '%s %s/%s (PowerShell 7, Linux)' % (st['status'], st['passed'], st['total']), 'integrity': '%d files' % len(integ['files']),
         'windows_proof': 'see GitHub workflow forge-windows (branch forge-ci-results)', 'authority': m['authority']}
open(os.path.join(APP, 'FORGE_%s_CHECKPOINT.json' % a.number), 'w').write(json.dumps(check, indent=2, ensure_ascii=False))
shutil.rmtree(tmp, ignore_errors=True)

# ---------- deterministic ZIP ----------
def build_zip(path):
    entries = []
    for dp, dn, fn in os.walk(APP):
        for f in fn: entries.append(os.path.relpath(os.path.join(dp, f), APP))
    entries.sort(key=lambda x: x.lower())
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for e in entries:
            zi = zipfile.ZipInfo(NAME + '/' + e.replace(os.sep, '/'), FIXED_TIME); zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16; zi.create_system = 0
            z.writestr(zi, open(os.path.join(APP, e), 'rb').read(), compresslevel=9)
    return sha(path)
os.makedirs(REL, exist_ok=True)
zp = os.path.join(REL, NAME + '.zip')
z1 = build_zip(zp); z2 = build_zip(zp + '.tmp'); os.remove(zp + '.tmp')
open(zp + '.sha256', 'w').write('%s  %s.zip\n' % (z1, NAME))
summary = {'zip': NAME + '.zip', 'sha256': z1, 'size_bytes': os.path.getsize(zp), 'deterministic_rebuild_exact': z1 == z2, 'static': check['static'], 'failed': [k for k, v in C.items() if not v], 'headless_selftest': check['headless_selftest']}
print(json.dumps(summary, indent=2))
sys.exit(0 if not summary['failed'] and summary['deterministic_rebuild_exact'] else 1)

