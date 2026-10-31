#!/usr/bin/env python3
"""Build Merch Forge 055 RC: manifest, docs, integrity, static acceptance, self-test, deterministic ZIP."""
import hashlib, json, os, re, subprocess, sys, zipfile, shutil
import xml.etree.ElementTree as ET

WORK = '/home/claude/forge/work'
OLD = os.path.join(WORK, '054_Merch_Forge_DISCOVER_RESEARCH_RC')
NAME = '055_Merch_Forge_RESEARCH_DRAFT_RC'
NEW = os.path.join(WORK, NAME)
INNER = os.path.join(NEW, 'Merch_Forge_A5_Current')
OLDIN = os.path.join(OLD, 'Merch_Forge_A5_Current')
OUT = '/home/claude/forge/out'
SCRATCH = '/tmp/claude-0/-home-claude/dbd0f6ea-538b-507e-bcc8-0edafe44746f/scratchpad'
SOURCE_054_SHA = 'c6ea5f5071310848010a3a3f4e23fb75f4128e985a211ced86a61d61358b8383'
FIXED_TIME = (2026, 10, 10, 0, 0, 0)
os.makedirs(OUT, exist_ok=True)

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def rd(p): return open(p, 'rb').read().decode('utf-8-sig')
def wr(p, text, bom=False, crlf=False):
    if crlf: text = text.replace('\r\n', '\n').replace('\n', '\r\n')
    open(p, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8'))

# ---------- outer entrypoint + README_FIRST ----------
old_start = os.path.join(NEW, 'START_054_MERCH_FORGE.vbs')
if os.path.exists(old_start):
    b = open(old_start, 'rb').read().replace(b'Merch Forge 054 is not fully extracted', b'Merch Forge 055 is not fully extracted')
    open(os.path.join(NEW, 'START_055_MERCH_FORGE.vbs'), 'wb').write(b); os.remove(old_start)
wr(os.path.join(NEW, 'README_FIRST.txt'), """MERCH FORGE 055 - RESEARCH -> CONCEPT DRAFT RC

START
1. Extract the whole folder.
2. Run START_055_MERCH_FORGE.vbs.
3. Open Discover, select a niche, click "Create concept draft".

WHAT IS NEW
- Discover can now create a LOCAL concept draft from the selected niche.
- The draft is bound to its research provenance: niche id, exact niche row SHA-256,
  snapshot time, contract forge.discover_snapshot.v1, explicitly linked research notes.
- The draft appears in Ideas (status "Research draft") and uses the normal
  KEEP / EDIT / REGEN / SKIP owner review.
- Hook and visual direction are left empty on purpose (creative choice, never invented).
  Fill them in the Edit tab; saving creates a new local revision and clears any older decision.
- Artwork: Export brief (no dispatch), then import the finished image.
- Generate, live Accept, delivery packages and server actions are blocked for drafts.

SAFETY / STATUS
- No backend change. Drafts are local only (LocalCore state on this Windows account).
- No paid provider call, no publishing, no Supabase mutation.
- Headless self-test: Merch_Forge_A5_Current\\MerchForgeResearchDraftSelfTest.ps1 (no network).
- Native Windows WPF execution of 055 is NOT claimed yet.
""", crlf=True)

# ---------- inner README section ----------
readme = os.path.join(INNER, 'README.txt')
t = rd(readme)
if '055 RESEARCH -> CONCEPT DRAFT' not in t:
    t = t.rstrip('\r\n') + '\r\n\r\n' + """055 RESEARCH -> CONCEPT DRAFT
- Discover > select niche > Create concept draft: creates a LOCAL draft in Ideas with research provenance.
- Provenance: niche identity, exact niche row SHA-256, snapshot time, contract, explicitly linked notes only.
- Hook and visual direction are never invented; the Overview lists what is still missing.
- Edit tab saves local draft revisions; a new revision resets the owner decision to UNDECIDED.
- Export brief works as before (no dispatch). Generate, live Accept, delivery and server actions are blocked for drafts.
- Clicking Create twice on identical research reuses the existing draft.
- Drafts are stored in LocalCore state (research_drafts). 054 can still read and rewrite this state without losing drafts.
- Self-test: MerchForgeResearchDraftSelfTest.ps1 -OutputPath <file> (headless; not a WPF click test).""".replace('\n', '\r\n') + '\r\n'
    wr(readme, t, bom=open(readme, 'rb').read().startswith(b'\xef\xbb\xbf'))

# ---------- run headless self-test ----------
st_out = os.path.join(SCRATCH, 'selftest055.json')
r = subprocess.run(['pwsh', '-NoProfile', '-File', os.path.join(INNER, 'MerchForgeResearchDraftSelfTest.ps1'), '-OutputPath', st_out, '-LegacyPackageRoot', OLDIN], capture_output=True, text=True, timeout=900)
print(r.stdout.strip(), r.stderr.strip()[:500])
selftest = json.load(open(st_out, encoding='utf-8-sig'))

# ---------- manifest ----------
mp = os.path.join(INNER, 'candidate_manifest.json')
m = json.loads(rd(mp))
mods = sorted([f for f in os.listdir(os.path.join(INNER, 'Modules')) if f.endswith('.ps1')], key=str.lower)
d = m['desktop']
d['app_version'] = '2.9.0-research-draft'
d['workbench_sha256'] = sha(os.path.join(INNER, 'MerchForgeWorkbench.ps1'))
d['workbench_size_bytes'] = os.path.getsize(os.path.join(INNER, 'MerchForgeWorkbench.ps1'))
d['native_windows_parser_target_sha256'] = d['workbench_sha256']
d['native_windows_parser_verified'] = False
d['native_windows_parser_result_sha256'] = None
d['runtime_modules'] = [{'path': 'Modules\\' + f, 'sha256': sha(os.path.join(INNER, 'Modules', f)), 'size_bytes': os.path.getsize(os.path.join(INNER, 'Modules', f))} for f in mods]
d['runtime_module_count'] = len(mods)
d['current_release'] = NAME
d['discover_research_read_only'] = True
d['research_concept_draft'] = True
m['package_name'] = NAME
m['package_number'] = 55
m['stage'] = 'FORGE-055-RESEARCH-DRAFT-RC'
m['installer_generation'] = '00000000000000100238'
m['result_intent'] = 'research -> local concept draft over 054: Discover creates a provenance-bound LOCAL draft that enters the normal Ideas/owner-review/no-dispatch brief flow; no backend change, generation, Accept, paid provider, Supabase mutation or external submission'
m['research_draft_055'] = {
    'status': 'candidate_pending_native_windows_execution',
    'source_release': '054_Merch_Forge_DISCOVER_RESEARCH_RC', 'source_release_sha256': SOURCE_054_SHA,
    'module': 'Modules\\Forge.ResearchDrafts.ps1', 'draft_schema': 'forge.research_concept_draft.v1',
    'storage': 'LocalCore state research_drafts[] (forge.local_core.v2 envelope unchanged)',
    'concept_key_prefix': 'rd-', 'workflow_state': 'research_draft',
    'provenance_fields': ['contract', 'snapshot_loaded_at', 'backend_version', 'niche_identity_field', 'niche_identity', 'niche_name', 'niche_row_sha256', 'niche_row', 'score_total', 'score_confidence', 'category', 'audience', 'concept_count_at_snapshot', 'evidence_notes', 'snapshot_sources'],
    'evidence_note_match': 'explicit_niche_link_only', 'creative_fields_invented': False,
    'revision_binding': 'revision id + SHA-256 over all creative fields; new revision resets owner decision',
    'idempotent_create_on_identical_research': True,
    'blocked_for_drafts': ['Generate', 'live Accept', 'Reopen', 'Start new iteration', 'Cancel generation', 'delivery/social/owner packages', 'server publication save'],
    'allowed_for_drafts': ['owner review KEEP/EDIT/REGEN/SKIP', 'local draft edit', 'Export brief (no dispatch)', 'local artwork import', 'local exact accept (existing owner gate)'],
    'backend_change': False, 'backend_mutation': False,
    'headless_selftest': {'script': 'MerchForgeResearchDraftSelfTest.ps1', 'status': selftest['status'], 'passed': selftest['passed'], 'total': selftest['total'], 'network_calls': selftest['network_calls'], 'api_calls': selftest['api_calls']},
    'native_windows_runtime_verified': False,
}
m['nonclaims']['native_windows_runtime_verified'] = False
m['nonclaims']['owner_acceptance_performed'] = False
open(mp, 'wb').write(json.dumps(m, indent=2, ensure_ascii=False).encode('utf-8'))

# ---------- integrity ----------
files = []
for dp, dn, fn in os.walk(INNER):
    for f in fn:
        rel = os.path.relpath(os.path.join(dp, f), INNER)
        if rel == 'integrity.json': continue
        files.append(rel)
files.sort(key=lambda x: x.replace('/', '\\').lower())
integ = {'schema': 'forge.package_integrity.v1', 'hash_algorithm': 'SHA-256', 'files': [{'path': f.replace('/', '\\'), 'sha256': sha(os.path.join(INNER, f)), 'size_bytes': os.path.getsize(os.path.join(INNER, f))} for f in files]}
open(os.path.join(INNER, 'integrity.json'), 'wb').write(json.dumps(integ, indent=2).encode('utf-8'))

# ---------- static acceptance ----------
C = {}
wb = rd(os.path.join(INNER, 'MerchForgeWorkbench.ps1'))
xs = wb.index("[xml]$xaml=@'"); xb = wb.index('\n', xs) + 1; xe = wb.index("\n'@", xb)
xaml = wb[xb:xe]
try:
    root = ET.fromstring(xaml); C['xaml_xml_parse'] = True
except Exception as e:
    root = None; C['xaml_xml_parse'] = False
XN = '{http://schemas.microsoft.com/winfx/2006/xaml}'
names = [el.get(XN + 'Name') for el in root.iter() if el.get(XN + 'Name')] if root is not None else []
keys = [el.get(XN + 'Key') for el in root.iter() if el.get(XN + 'Key')] if root is not None else []
C['xaml_names_unique'] = len(names) == len(set(names))
C['xaml_create_draft_button'] = 'DiscoverCreateDraftButton' in names
C['xaml_draft_status_text'] = 'DiscoverDraftStatusText' in names
C['xaml_styles_exist'] = 'PrimaryButton' in keys and 'MetaText' in keys
C['xaml_filter_research_draft'] = 'Tag="research_draft"' in xaml
C['create_button_bound'] = "$DiscoverCreateDraftButton=X 'DiscoverCreateDraftButton'" in wb and '$DiscoverCreateDraftButton.Add_Click({Invoke-DiscoverCreateDraft})' in wb
C['module_dot_sourced_after_localcore'] = wb.index("'Forge.ResearchDrafts.ps1'") > wb.index("'Forge.LocalCore.ps1'")
C['ui_text_registered_before_bindings'] = 0 < wb.index('Register-ResearchDraftUiText\nfunction X(') < wb.index("$DiscoverCreateDraftButton=X")
C['desktop_version_290'] = "$script:AppVersion = '2.9.0-forge-research-draft'" in wb
C['backend_min_0270_unchanged'] = "$script:MinimumBackendVersion = [version]'0.2.70'" in wb
modp = os.path.join(INNER, 'Modules', 'Forge.ResearchDrafts.ps1'); mod = rd(modp)
C['module_utf8_bom'] = open(modp, 'rb').read().startswith(b'\xef\xbb\xbf')
C['module_no_network_or_dispatch'] = not any(x in mod for x in ['Invoke-ForgeApi', 'Invoke-RestMethod', 'Invoke-WebRequest', 'Queue-LocalGeneration', 'Start-Process', 'Net.WebClient', 'HttpClient'])
C['module_no_accept_call'] = not any(x in mod for x in ['Set-LocalExactAcceptance', 'Accept-LocalArtwork', 'Accept-Current', 'Build-LocalAmazonPackage'])
loc_sets = {}
for loc in ('en', 'ru', 'es'):
    blk = re.search(r"\n        %s=@\{(.*?)\n        \}" % loc, mod, re.S).group(1)
    loc_sets[loc] = set(re.findall(r"'([a-z.]+)'=", blk))
C['module_locales_complete_en_ru_es'] = loc_sets['en'] == loc_sets['ru'] == loc_sets['es'] and len(loc_sets['en']) >= 20
dom = rd(os.path.join(INNER, 'Modules', 'Forge.DomainActions.ps1'))
C['generate_guard_for_drafts'] = "function Queue-Generation {\n    if(Test-CurrentIsResearchDraft)" in dom
C['save_revision_redirects_drafts'] = "function Save-Revision {\n    if(Test-CurrentIsResearchDraft){Save-CurrentResearchDraftRevision;return}" in dom
C['live_action_guards_7'] = dom.count("draft.live.blocked") == 7
C['open_draft_errors_contained'] = 'Research draft could not be opened' in mod and "catch {\n        Write-AppLog 'ERROR' ('Research draft open failed" in mod
C['load_concept_never_sends_draft_keys'] = 'if(Test-ResearchDraftKey $Key){' in rd(os.path.join(INNER, 'Modules', 'Forge.DataViews.ps1'))
C['dataviews_crlf_preserved'] = b'\r\n' in open(os.path.join(INNER, 'Modules', 'Forge.DataViews.ps1'), 'rb').read() and b'\n' not in open(os.path.join(INNER, 'Modules', 'Forge.DataViews.ps1'), 'rb').read().replace(b'\r\n', b'')
C['gates_utf8_bom'] = open(os.path.join(INNER, 'Modules', 'Forge.Gates.ps1'), 'rb').read().startswith(b'\xef\xbb\xbf')
C['decimal_format_invariant'] = 'InvariantCulture' in mod
gates = rd(os.path.join(INNER, 'Modules', 'Forge.Gates.ps1'))
C['set_busy_refreshes_owner_controls_052'] = 'try { Update-OwnerDecisionControls } catch' in gates[gates.index('function Set-Busy'):gates.index('function Show-GateState')]
C['generate_button_disabled_for_drafts'] = gates.count('-and -not (Test-CurrentIsResearchDraft))') == 2
C['owner_review_ru_labels_053'] = all(k in wb for k in ["'owner.review.keep'", "'owner.review.skip'"]) and 'ОСТАВИТЬ' in wb
C['discover_still_read_only_api'] = re.findall(r"Invoke-ForgeApi '(\w+)'", rd(os.path.join(INNER, 'Modules', 'Forge.ProductNavigation.ps1'))) == ['discover_snapshot']
C['localcore_byte_equal_054'] = sha(os.path.join(INNER, 'Modules', 'Forge.LocalCore.ps1')) == sha(os.path.join(OLDIN, 'Modules', 'Forge.LocalCore.ps1'))
for f in ['Start Merch Forge.vbs', 'MerchForgeLauncher.cmd', 'MerchForgePreflight.ps1', 'Install Merch Forge.vbs', 'MerchForgeProviderPipelineSelfTest.ps1', 'MerchForgeGenerationWorker.ps1']:
    C['byte_equal_054_' + f.replace(' ', '_')] = sha(os.path.join(INNER, f)) == sha(os.path.join(OLDIN, f))
for f in ['Forge.GenerationProvider.ps1', 'Forge.GenerationAuthority.ps1', 'Forge.GenerationWorkerBridge.ps1', 'Forge.Media.ps1', 'Forge.ImageValidation.ps1', 'Forge.PrintChecks.ps1']:
    C['byte_equal_054_' + f] = sha(os.path.join(INNER, 'Modules', f)) == sha(os.path.join(OLDIN, 'Modules', f))
ps = subprocess.run(['pwsh', '-NoProfile', '-c', "$bad=0;Get-ChildItem -LiteralPath '%s' -Recurse -Filter *.ps1|%%{$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$t,[ref]$e);if($e.Count){$bad++}};$bad" % INNER], capture_output=True, text=True)
C['powershell_parse_all'] = ps.stdout.strip() == '0'
bad = [f for f in integ['files'] if sha(os.path.join(INNER, f['path'].replace('\\', '/'))) != f['sha256']]
C['integrity_all_pass'] = not bad
C['integrity_includes_new_files'] = all(any(f['path'] == p for f in integ['files']) for p in ['Modules\\Forge.ResearchDrafts.ps1', 'MerchForgeResearchDraftSelfTest.ps1'])
mm = json.loads(rd(mp))
C['manifest_workbench_sha'] = mm['desktop']['workbench_sha256'] == sha(os.path.join(INNER, 'MerchForgeWorkbench.ps1'))
C['manifest_package_name_055'] = mm['package_name'] == NAME
C['manifest_installer_generation_advanced'] = mm['installer_generation'] > '00000000000000100237'
C['manifest_authority_unchanged'] = all(v is False for v in mm['authority'].values())
C['research_draft_selftest_pass'] = selftest['status'] == 'PASS' and selftest['network_calls'] == 0 and selftest['api_calls'] == 0
C['package_root_contents_expected'] = set(os.listdir(NEW)) - {'FORGE_055_CHECKPOINT.json', 'FORGE_055_STATIC_ACCEPTANCE.json', 'FORGE_055_RESEARCH_DRAFT_SELFTEST.json'} == {'Merch_Forge_A5_Current', 'Mobile_ReadReview', 'README_FIRST.txt', 'START_055_MERCH_FORGE.vbs'}
passed = sum(1 for v in C.values() if v)
static = {'schema': 'forge.static_acceptance.055.v1', 'status': 'PASS' if passed == len(C) else 'FAIL', 'passed': passed, 'total': len(C), 'checks': C,
          'integrity': '%d/%d' % (len(integ['files']) - len(bad), len(integ['files'])),
          'notes': ['Static/package checks plus headless PowerShell 7 execution on Linux. Native Windows PowerShell 5.1 / WPF execution not claimed.',
                    'XAML checked for XML well-formedness, unique names and referenced style keys only; WPF XamlReader load runs in the Windows preflight.']}

# ---------- deterministic ZIP (built twice, compared) ----------
def build_zip(path):
    entries = []
    for dp, dn, fn in os.walk(NEW):
        for f in fn: entries.append(os.path.relpath(os.path.join(dp, f), WORK))
    entries.sort(key=lambda x: x.lower())
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for e in entries:
            zi = zipfile.ZipInfo(e.replace(os.sep, '/'), FIXED_TIME); zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16; zi.create_system = 0
            z.writestr(zi, open(os.path.join(WORK, e), 'rb').read(), compresslevel=9)
    return sha(path)

# outer reports (not inside integrity-covered inner folder)
checkpoint = {
    'schema': 'forge.compact_checkpoint.v1', 'project_route': 'FORGE', 'release_family': '055',
    'title': '055 research -> local concept draft', 'artifact': NAME + '.zip',
    'source_release': '054_Merch_Forge_DISCOVER_RESEARCH_RC.zip', 'source_sha256': SOURCE_054_SHA,
    'completed': [
        'Restored and audited exact 054 (outer SHA verified, inner integrity 50/50, all PowerShell parses).',
        'Verified 052 Set-Busy owner-control refresh and 053 RU/ES owner labels are intact.',
        'Added Discover "Create concept draft" producing a provenance-bound local draft (forge.research_concept_draft.v1).',
        'Draft enters normal Ideas list, owner review KEEP/EDIT/REGEN/SKIP and no-dispatch Export brief.',
        'Local draft revisions with SHA-256 binding; new revision resets stale owner decision.',
        'Generate and all live server actions blocked for drafts; no authority broadened.',
        'Headless self-test (real Forge functions, isolated state, 3 processes incl. restart and 054 rollback read): %s %d/%d, 0 network calls.' % (selftest['status'], selftest['passed'], selftest['total']),
    ],
    'unfinished': ['Native Windows WPF startup/click smoke of exact 055 bytes.', 'Owner creative review of real drafts from live research.', 'Portfolio/Performance enrichment (Stage 4).'],
    'authority': {'backend_deployment': False, 'supabase_mutation': False, 'generation_authorized': False, 'accept_authorized': False, 'paid_provider_authorized': False, 'external_submission_authorized': False},
    'static_acceptance': '%d/%d %s' % (passed, len(C), static['status']),
    'research_draft_selftest': '%d/%d %s' % (selftest['passed'], selftest['total'], selftest['status']),
    'package_integrity': static['integrity'],
    'next_exact_action': 'Owner (or a session linked to the Windows PC) runs START_055_MERCH_FORGE.vbs: Discover > select niche > Create concept draft > draft opens in Ideas > KEEP > restart > KEEP persists. Optionally run MerchForgeResearchDraftSelfTest.ps1 under Windows PowerShell 5.1.',
}
for f in ('FORGE_055_CHECKPOINT.json', 'FORGE_055_STATIC_ACCEPTANCE.json', 'FORGE_055_RESEARCH_DRAFT_SELFTEST.json'):
    p = os.path.join(NEW, f)
    if os.path.exists(p): os.remove(p)
json.dump(checkpoint, open(os.path.join(NEW, 'FORGE_055_CHECKPOINT.json'), 'w'), indent=2, ensure_ascii=False)
json.dump(static, open(os.path.join(NEW, 'FORGE_055_STATIC_ACCEPTANCE.json'), 'w'), indent=2, ensure_ascii=False)
json.dump(selftest, open(os.path.join(NEW, 'FORGE_055_RESEARCH_DRAFT_SELFTEST.json'), 'w'), indent=2, ensure_ascii=False)

z1 = build_zip(os.path.join(OUT, NAME + '.zip'))
z2 = build_zip(os.path.join(SCRATCH, 'rebuild.zip'))
with zipfile.ZipFile(os.path.join(OUT, NAME + '.zip')) as z:
    tops = {n.split('/')[0] for n in z.namelist()}
summary = {'zip': NAME + '.zip', 'sha256': z1, 'size_bytes': os.path.getsize(os.path.join(OUT, NAME + '.zip')), 'deterministic_rebuild_exact': z1 == z2, 'top_level_folders': sorted(tops),
           'static': '%d/%d %s' % (passed, len(C), static['status']), 'selftest': '%d/%d %s' % (selftest['passed'], selftest['total'], selftest['status']), 'integrity': static['integrity'],
           'failed_static': [k for k, v in C.items() if not v]}
json.dump(summary, open(os.path.join(OUT, NAME + '.SHA256.json'), 'w'), indent=2)
open(os.path.join(OUT, NAME + '.zip.sha256'), 'w').write('%s  %s.zip\n' % (z1, NAME))
print(json.dumps(summary, indent=2))
