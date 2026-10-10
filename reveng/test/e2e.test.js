'use strict';
// End-to-end wiring tests. The LLM is a scripted FAKE and the "internet" is a local server: this proves the engine's logic
// (verification, gating, scoring, deep screen, decision, resume) -- NOT market truth and NOT live-provider behaviour.
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const { FakeProvider } = require('./helpers');
const { run } = require('../src/pipeline'), { Fetcher } = require('../src/fetcher'), { decide } = require('../src/decide');
const { FAMILIES_REQUIRED } = require('../src/schema'), { CODES } = require('../src/discover'), S = require('../src/scoring');
const { load } = require('../vendor/load'), { cand } = require('./helpers');

const stmt = (id, kind) => `Documented evidence statement for ${id} about ${kind} appears on this page only.`;
const BASE = 'https://evidence.test';
function world() { return Promise.resolve({ base: BASE, close: async () => {} }); }
const refMap = (user) => { const m = {}; for (const x of user.matchAll(/\[([CS]\d+)\] (\S+) ::/g)) if (!m[x[2]]) m[x[2]] = x[1]; return m; };
const strongDims = { demand_signal: 4, acquisition_efficiency: 4, competition_gap: 4, defensibility: 4, platform_resilience: 4, scale_without_hiring: 5, fulfillment_simplicity: 5, regulatory_simplicity: 4 };
function provider(base, opts = {}) {
  const strong = new Set(opts.strong || ['SAS-01']), free = new Set(opts.free || []), halluc = new Set(opts.hallucinate || []);
  const url = (id, k) => `${base}/p/${id}/${k}`;
  return new FakeProvider(({ system, user, webSearch }) => {
    if (webSearch && /research stage/.test(system)) {   // phase 1 discovery: prose + citations
      const fam = user.match(/Family: (\w+)/)[1], code = CODES[fam], n = +user.match(/exactly (\d+)/)[1], citations = [], searchResults = [];
      for (let i = 1; i <= n; i++) { const id = `${code}-${String(i).padStart(2, '0')}`; for (const k of ['price', 'demand', 'constraint']) { searchResults.push({ url: url(id, k), title: 'T ' + id }); if (!halluc.has(id)) citations.push({ url: url(id, k), title: 'T ' + id, cited_text: stmt(id, k) }); } }
      return { text: `Research notes for ${fam}: ${n} ideas.`, finalText: `Research notes for ${fam}: ${n} ideas. `.repeat(10), citations, searchResults };
    }
    if (!webSearch && /convert research notes/.test(system)) {   // phase 2 discovery: JSON by reference
      const fam = user.match(/Family: (\w+)/)[1], code = CODES[fam], n = +user.match(/exactly (\d+) candidates/)[1], rm = refMap(user), out = [];
      for (let i = 1; i <= n; i++) {
        const id = `${code}-${String(i).padStart(2, '0')}`, st = strong.has(id), fr = free.has(id);
        out.push({ name: `Idea ${id}`, category: 'c', buyer: 'buyers', pain: 'pain', entrant_wedge: 'automates three manual steps with a measured workflow',
          evidence: [['price', 'incumbent_price'], ['demand', 'demand'], ['constraint', 'constraint']].map(([k, kind]) => ({ ref: rm[url(id, k)], kind, shows: 's', class: 'fact' })),
          substitutes: [], entrant_edge: { criterion: 'cash_cost', direction: 'lower_is_better', unit: 'usd_month', incumbent_value: fr ? 0 : 50, incumbent_ref: rm[url(id, 'price')], entrant_value: 10, entrant_basis: 'serverless hosting without per-seat licence costs', falsifier: 'reject if hosting exceeds $10/month' },
          startup_cash_usd: st ? 150 : 2500, time_to_first_revenue_days: st ? 12 : 60, owner_hours_per_week_steady: st ? 2 : 12, automation_potential_pct: st ? 92 : 60,
          unit_economics: { contribution_margin_pct: st ? 80 : 45, class: 'model' }, regulatory_or_platform_dependency: 'none', major_uncertainty: 'demand', unknowns: [],
          dimension_scores: st ? { ...strongDims } : { demand_signal: 2, acquisition_efficiency: 2, competition_gap: 2, defensibility: 2, platform_resilience: 3, scale_without_hiring: 3, fulfillment_simplicity: 5, regulatory_simplicity: 4 },
          dimension_evidence: st ? { demand_signal: ['E2'], acquisition_efficiency: ['E2'], competition_gap: ['E1'], defensibility: ['E3'], platform_resilience: ['E3'], scale_without_hiring: ['E1'] } : {} });
      }
      return { text: '```json\n' + JSON.stringify(out) + '\n```' };
    }
    if (webSearch && /deep-screen stage/.test(system)) {
      const id = user.match(/Candidate ([A-Z]+-\d+)/)[1], ks = ['deep1', 'deep2', 'deep3'], cit = ks.map(k => ({ url: url(id, k), title: 'D', cited_text: halluc.has(id) ? '' : stmt(id, k) })).filter(c => c.cited_text);
      return { text: 'deep notes', finalText: 'deep notes '.repeat(30), citations: cit, searchResults: ks.map(k => ({ url: url(id, k), title: 'D' })) };
    }
    if (!webSearch && /convert deep-screen notes/.test(system)) {
      const id = user.match(/Candidate ([A-Z]+-\d+)/)[1], rm = refMap(user), st = strong.has(id);
      return { text: JSON.stringify({ evidence: [['deep1', 'demand'], ['deep2', 'incumbent_price'], ['deep3', 'constraint']].map(([k, kind]) => ({ ref: rm[url(id, k)], kind, shows: 's', class: 'fact' })),
        competitors: [{ name: 'Inc', price_point: '$50/mo', free_tier: false }], constraints: ['none material'],
        monthly_model: opts.badEconomics ? { price: 10, units: 10, revenue: 100, cashCost: 90, contribution: 10, ownerHours: 40, startup: 500, automation: 80, launchDays: 20, assumptions: ['x'] } : { price: 30, units: 100, revenue: 3000, cashCost: 600, contribution: 2400, ownerHours: 40, startup: 500, automation: 80, launchDays: 20, assumptions: ['100 customers by month 6 (model)'] },
        revised: { dimension_scores: st ? { ...strongDims } : {}, dimension_evidence: st ? { demand_signal: ['E1'], acquisition_efficiency: ['E1'], competition_gap: ['E2'], defensibility: ['E3'], platform_resilience: ['E3'], scale_without_hiring: ['E2'] } : {} },
        kill_reasons: [], unknowns: ['real conversion rate'] }) };
    }
    throw new Error('unexpected prompt: ' + system.slice(0, 60));
  });
}
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'rv-run-'));
const cfg = (o = {}) => ({ families: FAMILIES_REQUIRED, per_family: 4, sources: { enabled: false }, deep: { top_k: 8, min_verified: 3 }, ...o });
const mkFetch = () => new Fetcher({ allowHosts: [], defaultIntervalMs: 0 });

test('E2E winner path: 32 candidates/8 families, citation-verified evidence, deep screen, single clear leader', async () => {
  const w = await world(); const p = provider(w.base);
  try {
    const dir = tmp(), r = await run({ runDir: dir, cfg: cfg(), provider: p, fetcher: mkFetch() });
    assert.equal(r.candidates.length, 32);
    assert.equal(new Set(r.candidates.map(c => c.family)).size, 8);
    assert.ok(r.candidates.every(c => c.evidence.some(e => e.verify.status === 'verified')), 'every candidate has engine-verified evidence');
    assert.equal(r.decision.verdict, "winner", JSON.stringify(r.decision.unmet_conditions));
    assert.equal(r.decision.leader, 'SAS-01'); assert.deepEqual(r.decision.integrity_violations, []);
    assert.ok(r.decision.margin_adjusted_points >= 5); assert.ok(Object.values(r.decision.rank_by_profile).every(x => x <= 2));
    const lead = r.candidates.find(c => c.id === 'SAS-01'); assert.equal(lead.deep.complete, true); assert.equal(lead.deep.economics.survives_pessimistic, true);
    assert.equal(lead.deep.economics.baseline.cashMarginPct, 80);
    for (const f of ['01_raw.json', '02_verified.json', '03_gates.json', '04_scored.json', '05_deep.json', '06_decision.json', 'REPORT.md', 'checkpoint.json', 'MANIFEST.json', 'snapshot_SAS-01.json']) assert.ok(fs.existsSync(path.join(dir, f)), f);
    const snap = JSON.parse(fs.readFileSync(path.join(dir, 'snapshot_SAS-01.json'), 'utf8'));
    assert.equal(load('decision_snapshot').validate(snap).valid, true, 'snapshot passes frozen G280 validate()');
    assert.ok(snap.unresolved.length > 0 && snap.claimableFacts.every(f => f.state === 'verified'));
    const man = JSON.parse(fs.readFileSync(path.join(dir, 'MANIFEST.json'), 'utf8')); assert.match(man['REPORT.md'], /^[0-9a-f]{64}$/);
    assert.match(fs.readFileSync(path.join(dir, 'REPORT.md'), 'utf8'), /WINNER/);
  } finally { await w.close(); }
});
test('ANTI-HALLUCINATION: search URLs without citation excerpts => cannot survive gates or win', async () => {
  const bad = []; for (const c of Object.values(CODES)) for (let i = 1; i <= 4; i++) bad.push(`${c}-0${i}`);
  const w = await world(); const p = provider(w.base, { hallucinate: bad });
  try { const r = await run({ runDir: tmp(), cfg: cfg(), provider: p, fetcher: mkFetch() });
    assert.equal(r.decision.verdict, 'no_winner'); assert.equal(r.decision.survivors, 0); assert.ok(r.candidates.every(c => c.evidence.every(e => e.verify.status === 'search_confirmed')), 'URL seen in search but no citation excerpt => half weight only');
  } finally { await w.close(); }
});
test('free incumbent (value 0) candidates are rejected even with perfect evidence', async () => {
  const w = await world(); const p = provider(w.base, { free: ['SAS-01'] });
  try { const r = await run({ runDir: tmp(), cfg: cfg(), provider: p, fetcher: mkFetch() }); assert.equal(r.gateById['SAS-01'].passed, false); assert.ok(r.gateById['SAS-01'].failed.includes('entrant_edge')); assert.notEqual(r.decision.leader, 'SAS-01'); } finally { await w.close(); }
});
test('breadth rule: strong leader but <30 candidates / <8 families => NO winner', async () => {
  const w = await world(); const p = provider(w.base);
  try { const r = await run({ runDir: tmp(), cfg: cfg({ families: FAMILIES_REQUIRED.slice(0, 4) }), provider: p, fetcher: mkFetch() });
    assert.equal(r.decision.verdict, 'no_winner'); assert.ok(r.decision.hard_blockers.some(x => /raw_candidates/.test(x))); assert.ok(r.decision.hard_blockers.some(x => /families/.test(x))); assert.equal(r.decision.leader, null); } finally { await w.close(); }
});
test('two equally strong leaders => conditional_winner (margin rule), not winner', async () => {
  const w = await world(); const p = provider(w.base, { strong: ['SAS-01', 'GAM-01'] });
  try { const r = await run({ runDir: tmp(), cfg: cfg(), provider: p, fetcher: mkFetch() }); assert.equal(r.decision.verdict, 'conditional_winner'); assert.ok(r.decision.unmet_conditions.some(x => /margin_over_runner_up/.test(x))); } finally { await w.close(); }
});
test('leader failing pessimistic economics => conditional, never plain winner', async () => {
  const w = await world(); const p = provider(w.base, { badEconomics: true });
  try { const r = await run({ runDir: tmp(), cfg: cfg(), provider: p, fetcher: mkFetch() }); assert.notEqual(r.decision.verdict, 'winner'); assert.ok(r.decision.unmet_conditions.some(x => /pessimistic/.test(x))); } finally { await w.close(); }
});
test('resume: second run on same dir makes ZERO provider calls and same verdict', async () => {
  const w = await world(); const p = provider(w.base), dir = tmp();
  try { const a = await run({ runDir: dir, cfg: cfg(), provider: p, fetcher: mkFetch() }); const calls = p.calls.length;
    const p2 = provider(w.base); const b = await run({ runDir: dir, cfg: cfg(), provider: p2, fetcher: mkFetch() });
    assert.equal(p2.calls.length, 0); assert.ok(calls > 0); assert.equal(b.decision.verdict, a.decision.verdict); assert.equal(b.decision.leader, a.decision.leader);
    const chk = JSON.parse(fs.readFileSync(path.join(dir, 'checkpoint.json'), 'utf8')); assert.ok(chk.stages_done.includes('discover') && chk.stages_done.includes('report')); assert.ok(chk.next_exact_action);
  } finally { await w.close(); }
});
test('spend guard in pipeline: unauthorized provider budget stops the run before any call', async () => {
  const { Budget, SpendNotAuthorized } = require('../src/budget'); const w = await world(); const p = provider(w.base); p.budget = new Budget({});
  try { await assert.rejects(run({ runDir: tmp(), cfg: cfg(), provider: p, fetcher: mkFetch() }), SpendNotAuthorized); assert.equal(p.calls.length, 0); } finally { await w.close(); }
});
test('provisional (imported, unverified) runs can never produce a winner', async () => {
  const cs = []; for (const f of FAMILIES_REQUIRED) for (let i = 1; i <= 4; i++) { const c = cand({ id: `${CODES[f]}-0${i}`, family: f }); c.evidence.forEach(e => { e.verify = { status: 'agent_reported' }; }); cs.push(c); }
  const r = await run({ runDir: tmp(), cfg: cfg(), candidates: cs, provisional: true });
  assert.equal(r.decision.verdict, 'no_winner'); assert.ok(r.decision.hard_blockers.some(x => /provisional/.test(x)));
});
test('decide(): tampered score rows are a hard blocker', () => {
  const cs = []; for (const f of FAMILIES_REQUIRED) for (let i = 1; i <= 4; i++) cs.push(cand({ id: `${CODES[f]}-0${i}`, family: f }));
  const sc = cs.map(c => S.scoreCandidate(c)), g = Object.fromEntries(cs.map(c => [c.id, { passed: true, failed: [] }]));
  const ok = decide({ candidates: cs, scored: sc, gateById: g }); assert.deepEqual(ok.integrity_violations, []);
  sc[0].raw += 10; const bad = decide({ candidates: cs, scored: sc, gateById: g }); assert.equal(bad.verdict, 'no_winner'); assert.ok(bad.hard_blockers.some(x => /score_integrity/.test(x)));
});
