#!/usr/bin/env python3
"""Build a DRY-RUN import package for scan #1 (reveng engine run_20261010_031655) into the app's own inbox tables:
reveng.catalog_discovery_runs, reveng.catalog_candidate_inbox, reveng.catalog_discovery_run_candidates.
Pure file transform: reads samples/g281_scan1/*, writes server/REVA2_G281_SCAN1_IMPORT.json and .sql. Performs no network or database access.
The SQL ends with ROLLBACK; only the owner replaces it with COMMIT (external write = owner-gated)."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
S = ROOT / 'samples' / 'g281_scan1'
OUT = ROOT / 'server'
RUN_KEY = 'g281-scan1-run_20261010_031655'
MANUAL = {  # manual deep screen of 2026-10-10, evidence class agent_reported (see manual_deep_screen_2026-10-10.md)
  'EDU-01': 'FREE_OR_CHEAPER_ALTERNATIVE: TutorTab is $0 for tutors (scheduling, invoicing, booking page), so a $9/mo exit kit is not cheaper; the only wedge left (Wyzant roster import) is unproven and contract-restricted.',
  'MED-04': 'FREE_OR_CHEAPER_ALTERNATIVE: several sponsor databases already exist, including a free list (Gumroad) and paid ones; no differentiation shown; lead-data legality unconfirmed.',
  'EDU-04': 'FREE_OR_CHEAPER_ALTERNATIVE: SPED Goals IEP Tracker is free up to 20 students (premium $2.99/mo); the entrant at $5/mo is more expensive than the real incumbent.',
}
APIKILL = ['SAS-03', 'SAS-04', 'ECO-02', 'ECO-03', 'SVC-01']
raw = {c['id']: c for c in json.load(open(S / '01_raw.json'))}
gates = json.load(open(S / '03_gates.json'))
scored = {r['id']: r for r in json.load(open(S / '04_scored.json'))}
deep = {c['id']: (c.get('deep') or {}) for c in json.load(open(S / '05_deep.json'))}
decision = json.load(open(S / '06_decision.json'))
# second pass (2026-10-10): manual deep screen of the 24 queued ideas, agent_reported; two ideas could not be screened (see deep_status.json)
deeps = {f.stem: json.load(open(f)) for f in sorted((S / 'deep').glob('*.json'))} if (S / 'deep').exists() else {}
dstat = json.load(open(S / 'deep_status.json')) if (S / 'deep_status.json').exists() else {}
# second attempt (deep2/): evidence, alternatives and kill reasons are appended; verdict, reason, economics, answers-unverified and next step come from the later attempt
for f in sorted((S / 'deep2').glob('*.json')) if (S / 'deep2').exists() else []:
    b = json.load(open(f)); a = deeps[b['id']]
    a['newEvidence'] = a['newEvidence'] + b['newEvidence']; a['newAlternatives'] = a['newAlternatives'] + b['newAlternatives']
    seen = {k['reason'] for k in a['killReasons']}; a['killReasons'] = a['killReasons'] + [k for k in b['killReasons'] if k['reason'] not in seen]
    a['legalNotes'] = list(dict.fromkeys(a['legalNotes'] + b['legalNotes'])); a['answers'] = a['answers'] + b['answers']
    for k in ('verdict', 'verdictReason', 'economics', 'unverified', 'nextStep'): a[k] = b[k]
rechecks = {}
for f in sorted((S / 'verify').glob('deep_result_*.json')) if (S / 'verify').exists() else []:
    for r in json.load(open(f))['results']: rechecks[(r['candidateId'], r['evidenceId'])] = r
def clip(x, n): x = str(x or ''); return x if len(x) <= n else x[:n - 1] + '…'

def sha(*parts): return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()
rows = []
for cid, c in raw.items():
    g = gates[cid]; ev = c.get('evidence') or []
    status, reason, basis = 'research_queue', None, None
    if cid in MANUAL:
        status, reason, basis = 'rejected', MANUAL[cid], 'manual_reading_agent_reported'
    elif cid in APIKILL:
        kr = deep.get(cid, {}).get('kill_reasons') or []
        status, reason, basis = 'rejected', 'FREE_OR_CHEAPER_ALTERNATIVE: ' + ' '.join(str(x) for x in kr)[:700], 'deep_screen_uncited_provider_claims'
    elif not g['passed']:
        status = 'rejected'
        reason = 'HARD_GATE_FAILED: ' + '; '.join(f"{k}={g['gates'][k]['reason']}" for k in g['failed'])
        basis = 'engine_hard_gate'
    dp = deeps.get(cid) if status == 'research_queue' else None
    if dp and dp['verdict'] == 'killed':
        status, reason, basis = 'rejected', 'KILLED_AFTER_DEEP_SCREEN (agent_reported): ' + clip(dp['verdictReason'], 880), 'independent_manual_reading_agent_reported'
    s = scored[cid]
    hints = [{'url': e.get('url'), 'signal': (e.get('shows') or '')[:240], 'source': e.get('publisher'),
              'evidence_class': (e.get('verify') or {}).get('status', 'unverified'), 'kind': e.get('kind')} for e in ev]
    if dp:
        for e in dp['newEvidence']:
            rc = rechecks.get((cid, e['id']))
            hints.append({'url': e['url'], 'signal': clip(e['quote'], 240), 'source': e.get('publisher'), 'evidence_class': 'agent_reported', 'kind': e['kind'], 'date': e.get('date'), 'stage': 'deep',
                          'recheck': ({'status': rc['status'], 'note': clip(rc['note'], 220)} if rc else None)})
    rows.append({
        'candidate_key': f'G281-SCAN1-{cid}', 'fingerprint': sha('niche', c['name'], c['buyer']), 'analysis_level': 'niche',
        'raw_name': c['name'], 'normalized_name': c['name'], 'buyer_segment': c['buyer'], 'core_job': c['pain'], 'primary_outcome': c['entrant_wedge'],
        'suggested_model_key': None, 'suggested_market_key': c['family'], 'status': status, 'source_count': max(1, len(ev)),
        'evidence_hints': hints, 'rejection_reason': reason,
        'metadata': {
            'scan_run': RUN_KEY, 'engine_id': cid, 'family': c['family'], 'global_independent': True, 'rejection_basis': basis,
            'engine_score': {'label': 'g280_balanced_v1_lens_NOT_reveng_v6', 'adjusted': round(s['adjusted'], 1), 'raw': round(s['raw'], 1),
                             'note': 'Computed with the G280 v1 balanced weights, not with reveng_v6_independent weights; not comparable with score_runs.'},
            'v6_component_scores': None, 'hard_gates_passed': g['passed'],
            'deep_screen': {'done': bool(cid in MANUAL or deep.get(cid, {}).get('done') or dp), 'complete': bool(cid in MANUAL or deep.get(cid, {}).get('complete') or dp),
                            'method': 'manual_reading_agent_reported' if (cid in MANUAL or dp) else ('provider_search_uncited_claims' if deep.get(cid, {}).get('done') else None),
                            **({'second_pass': True, 'verdict': dp['verdict'], 'reason': clip(dp['verdictReason'], 700),
                                'economics': {'revenue365_usd': dp['economics']['revenue365'], 'cost365_usd': dp['economics']['cost365'], 'pessimistic_profit365_usd': dp['economics']['pessimisticProfit365'], 'survives_pessimistic': dp['economics']['survivesPessimistic']},
                                'answers': [{'question': clip(a['question'], 220), 'answer': clip(a['answer'], 420)} for a in dp['answers'][:6]],
                                'unverified': [clip(u, 200) for u in dp.get('unverified', [])[:6]]} if dp else {})},
            **({'final_verdict': dp['verdict'], 'alternatives': [{'label': a['label'], 'kind': a['kind'], 'usd_per_month': a['costUsdPerMonth'], 'covers_wedge': a['coversWedge'], 'url': a['sourceLocator']} for a in dp.get('newAlternatives', [])],
                'kill_reasons': [{'severity': k['severity'], 'reason': clip(k['reason'], 400), 'ref': k.get('ref'), 'ref_class': 'agent_reported'} for k in dp['killReasons']],
                'legal_notes': [clip(n, 400) for n in dp.get('legalNotes', [])], 'verdict_reason': clip(dp['verdictReason'], 1200)} if dp else {}),
            **({'deep_screen_not_screened': dstat['not_screened'][cid]} if cid in dstat.get('not_screened', {}) else {}),
            'next_step': None if status == 'rejected' else 'verify cheapest/free alternative, legal limits and willingness to pay by manual public reading, then judge v6 components',
        }})
fams = sorted({r['metadata']['family'] for r in rows})
run = {'run_key': RUN_KEY, 'objective': 'Global, owner-independent broad scan (reveng_v6_independent rules): >=30 raw candidates across >=8 business-model families; no winner declared.',
       'family_scope': fams, 'source_plan': {'method': 'provider_search_citation', 'scraping': False, 'note': 'LLM provider web search with provider-returned citations; no pages fetched by software'},
       'status': 'completed', 'candidate_count': len(rows), 'normalized_count': sum(r['status'] != 'rejected' for r in rows), 'rejected_count': sum(r['status'] == 'rejected' for r in rows),
       'started_at': '2026-10-10T03:16:55Z', 'completed_at': '2026-10-10T03:58:00Z',
       'metadata': {'verdict': 'no_winner', 'survivors_after_gates': decision.get('survivors'), 'hard_blockers': decision.get('hard_blockers'),
                    'deep_screened': len(deeps), 'deep_screen_completed_at': dstat.get('deep_screen_completed_at'), 'deep_screen_not_screened': sorted(dstat.get('not_screened', {})),
                    'final_verdicts_after_deep_screen': {v: sum(1 for r in rows if r['metadata'].get('final_verdict') == v) for v in ('killed', 'uncertain', 'survives')},
                    'caveat': 'Kills rest on uncited provider claims or manual reading (agent_reported), not on engine-verified quotes. Scores use G280 v1 balanced weights, not v6.'}}
pkg = {'contract': 'reveng_scan_import_dryrun_g281_v1', 'target_tables': ['reveng.catalog_discovery_runs', 'reveng.catalog_candidate_inbox', 'reveng.catalog_discovery_run_candidates'],
       'owner_gated_write': True, 'run': run, 'candidates': rows}
OUT.mkdir(exist_ok=True)
(OUT / 'REVA2_G281_SCAN1_IMPORT.json').write_text(json.dumps(pkg, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

# data file for the standalone global-ranking page (works from file://; no network)
(ROOT / 'app' / 'data').mkdir(exist_ok=True)
(ROOT / 'app' / 'data' / 'g281_scan1_view.js').write_text('window.REVENG_GLOBAL_VIEW_DATA=' + json.dumps(pkg, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + ';\n', encoding='utf-8')

def q(v):
    if v is None: return 'NULL'
    if isinstance(v, (dict, list)): return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    if isinstance(v, int): return str(v)
    return "'" + str(v).replace("'", "''") + "'"
L = ['-- REVA2-G281 scan #1 import. DRY RUN: this script ends with ROLLBACK and writes nothing.',
     '-- Writing to Supabase is owner-gated: only the owner may replace the final ROLLBACK with COMMIT.',
     '-- Target: project media-business-projects, schema reveng (the app\'s own discovery inbox). No new tables.',
     'BEGIN;',
     'INSERT INTO reveng.catalog_discovery_runs (run_key, objective, family_scope, source_plan, status, candidate_count, normalized_count, rejected_count, started_at, completed_at, metadata)',
     f"VALUES ({q(run['run_key'])}, {q(run['objective'])}, {q(run['family_scope'])}, {q(run['source_plan'])}, 'completed', {run['candidate_count']}, {run['normalized_count']}, {run['rejected_count']}, {q(run['started_at'])}, {q(run['completed_at'])}, {q(run['metadata'])})",
     'ON CONFLICT (run_key) DO NOTHING;']
cols = ['candidate_key', 'fingerprint', 'analysis_level', 'raw_name', 'normalized_name', 'buyer_segment', 'core_job', 'primary_outcome', 'suggested_model_key', 'suggested_market_key', 'status', 'source_count', 'evidence_hints', 'rejection_reason', 'metadata']
for r in rows:
    L.append(f"INSERT INTO reveng.catalog_candidate_inbox ({', '.join(cols)}) VALUES ({', '.join(q(r[c]) for c in cols)}) ON CONFLICT (candidate_key) DO NOTHING;")
L.append("INSERT INTO reveng.catalog_discovery_run_candidates (run_id, candidate_id) SELECT r.id, c.id FROM reveng.catalog_discovery_runs r JOIN reveng.catalog_candidate_inbox c ON c.candidate_key LIKE 'G281-SCAN1-%' WHERE r.run_key = " + q(RUN_KEY) + ' ON CONFLICT DO NOTHING;')
L.append(f"-- expected after a COMMIT: 1 run, {len(rows)} candidates ({run['rejected_count']} rejected, {run['normalized_count']} research_queue), {len(rows)} run-candidate links")
L.append('ROLLBACK;')
(OUT / 'REVA2_G281_SCAN1_IMPORT_DRYRUN.sql').write_text('\n'.join(L) + '\n', encoding='utf-8')
print('candidates', len(rows), 'rejected', run['rejected_count'], 'research_queue', run['normalized_count'])
