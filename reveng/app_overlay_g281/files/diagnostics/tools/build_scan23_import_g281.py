#!/usr/bin/env python3
"""Build the DRY-RUN import package for scan #2 or the scan #3 extension (edge-first, owner-independent, manual public reading; uncertain ideas deep-screened) into the app's own inbox tables:
Usage: build_scan23_import_g281.py <2|3>
reveng.catalog_discovery_runs, reveng.catalog_candidate_inbox, reveng.catalog_discovery_run_candidates.
Pure file transform: reads samples/g281_scanN/*, writes server/REVA2_G281_SCANN_IMPORT.json/.sql and app/data/g281_scanN_view.js.
No network, no database. The SQL ends with ROLLBACK; only the owner replaces it with COMMIT (external write = owner-gated).
Evidence stays class agent_reported everywhere: the independent re-read is stored as a separate 'recheck' note and never promotes the class."""
import datetime, hashlib, json, sys
from pathlib import Path
N = int(sys.argv[1]) if len(sys.argv) > 1 else 2
if N not in (2, 3): sys.exit('usage: build_scan23_import_g281.py <2|3>')
ROOT = Path(__file__).resolve().parents[2]
S = ROOT / 'samples' / f'g281_scan{N}'
OUT = ROOT / 'server'
RUN_KEY = {2: 'g281-scan2-manual-edge-first-20261010', 3: 'g281-scan3-extension-edge-first-20261010'}[N]
SCAN2_KEY = 'g281-scan2-manual-edge-first-20261010'
agg = json.load(open(S / 'aggregate.json'))
cands = []
for f in sorted((S / 'candidates').glob('*.json')):
    cands += json.load(open(f))['candidates']
rechecks = {}
for f in sorted((S / 'verify').glob('result_*.json')):
    for r in json.load(open(f))['results']:
        rechecks[(r['candidateId'], r['evidenceId'])] = r
for f in sorted((S / 'verify').glob('deep_result_*.json')):
    for r in json.load(open(f))['results']:
        rechecks[(r['candidateId'], r['evidenceId'])] = r
deeps = {f.stem: json.load(open(f)) for f in sorted((S / 'deep').glob('*.json'))}
summ = {c['id']: c for c in agg['candidates']}
if len(cands) != len(summ) or {c['id'] for c in cands} != set(summ): sys.exit('aggregate.json does not match candidate files: rerun aggregate_scan_g281.mjs <N>')

def sha(*parts): return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()
def clip(s, n): s = str(s or ''); return s if len(s) <= n else s[:n - 1] + '…'
rows = []
for c in cands:
    s = summ[c['id']]
    dp = deeps.get(c['id'])
    final = dp['verdict'] if dp else c['researcherVerdict']
    killed = final == 'killed'
    reason = None
    if killed:
        reason = ('KILLED_AFTER_DEEP_SCREEN (agent_reported): ' + clip(dp['verdictReason'], 880)) if dp else ('KILLED_BY_RESEARCHER (agent_reported): ' + clip(c['verdictReason'], 900))
    hints = []
    for e in list(c['evidence']) + (dp['newEvidence'] if dp else []):
        rc = rechecks.get((c['id'], e['id']))
        hints.append({'url': e['url'], 'signal': clip(e['quote'], 240), 'source': e.get('publisher'), 'evidence_class': 'agent_reported', 'kind': e['kind'],
                      'date': e.get('date'), 'stage': 'deep' if '-D' in e['id'] else 'scan', 'recheck': ({'status': rc['status'], 'note': clip(rc['note'], 220)} if rc else None)})
    alts = [{'label': a['label'], 'kind': a['kind'], 'usd_per_month': a['costUsdPerMonth'], 'covers_wedge': a['coversWedge'], 'url': a['sourceLocator']} for a in c['alternativesSurvey']['alternatives'] + (dp.get('newAlternatives', []) if dp else [])]
    deep = c.get('deep') or {}
    dkr = (dp or {}).get('killReasons', [])
    rows.append({
        'candidate_key': f"G281-SCAN{N}-{c['id']}", 'fingerprint': sha('niche', c['name'], c['buyer']), 'analysis_level': 'niche',
        'raw_name': c['name'], 'normalized_name': c['name'], 'buyer_segment': c['buyer'], 'core_job': c['pain'], 'primary_outcome': c['wedge'],
        'suggested_model_key': None, 'suggested_market_key': c['family'], 'status': 'rejected' if killed else 'research_queue', 'source_count': max(1, len(hints)),
        'evidence_hints': hints, 'rejection_reason': reason,
        'metadata': {
            'scan_run': RUN_KEY, 'engine_id': c['id'], 'family': c['family'], 'global_independent': True,
            'rejection_basis': 'independent_manual_reading_agent_reported' if killed else None,
            'researcher_verdict': c['researcherVerdict'], 'final_verdict': final, 'verdict_reason': clip(dp['verdictReason'] if dp else c['verdictReason'], 1200),
            'v6_component_scores': None,
            'v6_provisional': {'raw': s['raw'], 'adjusted': s['adjusted'], 'grade': s['grade'], 'cap_reason': s['cap'], 'component_scores': c['componentScores'],
                               'basis': 'researcher_judged_scores_edge_not_independently_evidenced',
                               'note': 'Provisional: scores judged by the researcher from agent_reported evidence; the entrant-edge hard gate caps them. This is NOT a v6 rank.'},
            'entrant_edge': {'type': c['entrantEdge']['type'], 'status': c['entrantEdge']['status'], 'statement': clip(c['entrantEdge']['statement'], 700)},
            'alternatives': alts, 'cheapest_alternative': s['cheapestAlternative'],
            'hard_gates_passed': False, 'hard_gates_failed': s['gatesFailed'],
            'economics': {'survives_pessimistic': bool(deep.get('economics', {}).get('survivesPessimistic')), 'note': clip(deep.get('economics', {}).get('note'), 600)},
            'kill_reasons': [{'severity': k['severity'], 'reason': clip(k['reason'], 400), 'ref': k.get('ref'), 'ref_class': 'agent_reported'} for k in deep.get('killReasons', []) + dkr],
            'legal_notes': [clip(n, 400) for n in c.get('legalNotes', []) + (dp.get('legalNotes', []) if dp else [])],
            'deep_screen': {'done': bool(deep.get('done')), 'complete': bool(deep.get('complete')), 'method': 'manual_reading_agent_reported',
                            **({'second_pass': True, 'verdict': dp['verdict'], 'reason': clip(dp['verdictReason'], 700),
                                'economics': {'revenue365_usd': dp['economics']['revenue365'], 'cost365_usd': dp['economics']['cost365'], 'pessimistic_profit365_usd': dp['economics']['pessimisticProfit365'], 'survives_pessimistic': dp['economics']['survivesPessimistic']},
                                'answers': [{'question': clip(a['question'], 220), 'answer': clip(a['answer'], 420)} for a in dp['answers'][:6]],
                                'unverified': [clip(u, 200) for u in dp.get('unverified', [])[:6]]} if dp else {})},
            'next_step': None if killed else 'Resolve the named open question with provider-cited or primary-source evidence before any v6 ranking: ' + clip(dp['verdictReason'] if dp else c['verdictReason'], 400),
        }})
fams = sorted({r['metadata']['family'] for r in rows})
OBJ = {2: 'Second global, owner-independent scan, edge-first: 4 candidates x 8 required families, each researched to the same depth; uncertain ideas deep-screened; no winner declared.',
       3: 'Extension of scan 2 to six more families (5 candidates each), same protocol; uncertain ideas deep-screened; valid only together with scan 2; no winner declared.'}
TIMES = json.load(open(S / 'TIMES.json'))  # UTC start/end of the original research (copying files changes mtimes, so they are recorded)
run = {'run_key': RUN_KEY, 'objective': OBJ[N],
       'family_scope': fams, 'source_plan': {'method': 'manual_public_review', 'scraping': False, 'note': 'Public pages read like a normal reader with WebSearch/WebFetch; no logins, no automated crawling; evidence class agent_reported'},
       'status': 'completed', 'candidate_count': len(rows), 'normalized_count': sum(r['status'] != 'rejected' for r in rows), 'rejected_count': sum(r['status'] == 'rejected' for r in rows),
       'started_at': TIMES['started_at'], 'completed_at': TIMES['completed_at'],
       'metadata': {'verdict': 'no_winner', 'survivors_after_gates': 0, 'hard_blockers': agg['decision']['hard_blockers'],
                    'researcher_verdicts': agg['counts'], 'final_verdicts': {v: sum(1 for r in rows if r['metadata']['final_verdict'] == v) for v in ('killed', 'uncertain', 'survives')}, 'deep_screened': len(deeps),
                    **({'extends': SCAN2_KEY, 'combined_with_extended': agg['combinedWithScan2']} if N == 3 else {}), 'independent_recheck': {'checked': len(rechecks), 'scope': 'key quotes behind the verdicts, incl. deep-screen kill reasons', 'confirmed': sum(r['status'] == 'confirmed' for r in rechecks.values()), 'partially_supported': sum(r['status'] == 'partially_supported' for r in rechecks.values()), 'contradicted_or_missing': sum(r['status'] in ('contradicted', 'not_found', 'unreachable') for r in rechecks.values())},
                    'caveat': 'All evidence is agent_reported (pages read by research agents, key quotes re-read by independent agents); no provider-verified citations; the entrant-edge hard gate fails for every candidate; scores are provisional.' + (' This extension is not a valid scan on its own (fewer than 8 families).' if N == 3 else '')}}
pkg = {'contract': 'reveng_scan_import_dryrun_g281_v1', 'target_tables': ['reveng.catalog_discovery_runs', 'reveng.catalog_candidate_inbox', 'reveng.catalog_discovery_run_candidates'],
       'owner_gated_write': True, 'run': run, 'candidates': rows}
(OUT / f'REVA2_G281_SCAN{N}_IMPORT.json').write_text(json.dumps(pkg, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
(ROOT / 'app' / 'data' / f'g281_scan{N}_view.js').write_text('window.REVENG_GLOBAL_VIEW_DATA_EXTRA=(window.REVENG_GLOBAL_VIEW_DATA_EXTRA||[]).concat([' + json.dumps(pkg, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + ']);\n', encoding='utf-8')

def q(v):
    if v is None: return 'NULL'
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, (dict, list)): return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    if isinstance(v, int): return str(v)
    return "'" + str(v).replace("'", "''") + "'"
L = [f'-- REVA2-G281 scan #{N} import. DRY RUN: this script ends with ROLLBACK and writes nothing.',
     '-- Writing to Supabase is owner-gated: only the owner may replace the final ROLLBACK with COMMIT.',
     "-- Target: project media-business-projects, schema reveng (the app's own discovery inbox). No new tables.",
     'BEGIN;',
     'INSERT INTO reveng.catalog_discovery_runs (run_key, objective, family_scope, source_plan, status, candidate_count, normalized_count, rejected_count, started_at, completed_at, metadata)',
     f"VALUES ({q(run['run_key'])}, {q(run['objective'])}, {q(run['family_scope'])}, {q(run['source_plan'])}, 'completed', {run['candidate_count']}, {run['normalized_count']}, {run['rejected_count']}, {q(run['started_at'])}, {q(run['completed_at'])}, {q(run['metadata'])})",
     'ON CONFLICT (run_key) DO NOTHING;']
cols = ['candidate_key', 'fingerprint', 'analysis_level', 'raw_name', 'normalized_name', 'buyer_segment', 'core_job', 'primary_outcome', 'suggested_model_key', 'suggested_market_key', 'status', 'source_count', 'evidence_hints', 'rejection_reason', 'metadata']
for r in rows:
    L.append(f"INSERT INTO reveng.catalog_candidate_inbox ({', '.join(cols)}) VALUES ({', '.join(q(r[c]) for c in cols)}) ON CONFLICT (candidate_key) DO NOTHING;")
L.append(f"INSERT INTO reveng.catalog_discovery_run_candidates (run_id, candidate_id) SELECT r.id, c.id FROM reveng.catalog_discovery_runs r JOIN reveng.catalog_candidate_inbox c ON c.candidate_key LIKE 'G281-SCAN{N}-%' WHERE r.run_key = " + q(RUN_KEY) + ' ON CONFLICT DO NOTHING;')
L.append(f"-- expected after a COMMIT: 1 run, {len(rows)} candidates ({run['rejected_count']} rejected, {run['normalized_count']} research_queue), {len(rows)} run-candidate links")
L.append('ROLLBACK;')
(OUT / f'REVA2_G281_SCAN{N}_IMPORT_DRYRUN.sql').write_text('\n'.join(L) + '\n', encoding='utf-8')
print('candidates', len(rows), 'rejected', run['rejected_count'], 'research_queue', run['normalized_count'], 'rechecks', len(rechecks))
