'use strict';
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const { cand } = require('./helpers');
const S = require('../src/scoring'), { runGates } = require('../src/gates'), { DIMENSIONS } = require('../src/schema');
const { load, manifest } = require('../vendor/load');

test('vendored G280 modules match frozen baseline split-manifest hashes and load', () => {
  for (const [f, m] of Object.entries(manifest.files)) { assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, '../vendor/g280', f))).digest('hex'), m.sha256, f); load(f); }
  assert.equal(manifest.baseline_zip_sha256, 'b83930f25163f47895a903014eb594fa6b5ab26becbe1d8230ce9b188fca25d2');
});
test('profile weights: 13 dims, total 100, taken from G280 scoring_profiles', () => {
  for (const [n, w] of Object.entries(S.PROFILES)) { assert.equal(Object.values(w).reduce((a, b) => a + b, 0), 100, n); assert.deepEqual(Object.keys(w).sort(), [...DIMENSIONS].sort(), n); }
  assert.equal(S.PROFILES.balanced.contribution_economics, 12);
});
test('mechanical bands', () => {
  const m = S.mechanicalScores(cand({ over: { startup_cash_usd: 150, time_to_first_revenue_days: 10, owner_hours_per_week_steady: 2, automation_potential_pct: 95, unit_economics: { contribution_margin_pct: 80 } } }));
  assert.deepEqual(m, { capital_efficiency: 5, launch_speed: 5, owner_time_efficiency: 5, automation: 5, contribution_economics: 5 });
  const w = S.mechanicalScores(cand({ over: { startup_cash_usd: 20000, time_to_first_revenue_days: 500, owner_hours_per_week_steady: 60, automation_potential_pct: 5, unit_economics: { contribution_margin_pct: 3 } } }));
  assert.deepEqual(Object.values(w), [0, 0, 0, 0, 0]);
  assert.equal(S.mechanicalScores(cand({ over: { unit_economics: {} } })).contribution_economics, 2, 'unknown margin defaults to 2, not 0 or 5');
});
test('score arithmetic is exact and reproducible', () => {
  const c = cand(), a = S.scoreCandidate(c), b = S.scoreCandidate(JSON.parse(JSON.stringify(c)));
  assert.deepEqual(a, b);
  const w = S.PROFILES.balanced, d = a.dimensions;
  const expected = Math.round(DIMENSIONS.reduce((s, k) => s + w[k] * d[k], 0) / 5 * 1e6) / 1e6;
  assert.equal(a.raw, expected);
  assert.ok(a.adjusted <= a.raw && a.raw <= 100);
  assert.equal(a.evidence_confidence, 1);
});
test('GLOBAL INDEPENDENCE: owner/user-fit fields cannot change global score', () => {
  const base = S.scoreCandidate(cand());
  const tainted = cand({ over: { owner_fit: 5, user_fit: { trucking: 5 }, owner_bio: 'ten years trucking', dimension_scores: { ...cand().dimension_scores } } });
  assert.deepEqual(S.scoreCandidate(tainted), base);
  const src = fs.readFileSync(path.join(__dirname, '../src/scoring.js'), 'utf8');
  assert.ok(!/owner_fit|user_fit|ownerFit|userFit|biograph/i.test(src.replace(/\/\/.*$/gm, '')), 'scoring source must not reference owner/user fit');
});
test('evidence cap: judged score >3 without verified citation is capped at 3', () => {
  const c = cand({ over: { dimension_scores: { ...cand().dimension_scores, demand_signal: 5 } } });
  let s = S.scoreCandidate(c); assert.equal(s.dimensions.demand_signal, 3); assert.ok(s.evidence_capped_dimensions.includes('demand_signal'));
  c.dimension_evidence = { demand_signal: [c.evidence[1].id] }; s = S.scoreCandidate(c); assert.equal(s.dimensions.demand_signal, 5); assert.ok(!s.evidence_capped_dimensions.includes('demand_signal'));
  c.evidence[1].verify.status = 'fetch_failed'; s = S.scoreCandidate(c); assert.equal(s.dimensions.demand_signal, 3);
});
test('evidence confidence multiplier: verified=1, search_confirmed=.5, else 0', () => {
  const c = cand(); c.evidence[0].verify.status = 'search_confirmed'; c.evidence[1].verify.status = 'fetch_failed';
  assert.equal(S.evidenceConfidence(c.evidence), +(0.5 + 0.5 * ((0.5 + 0 + 1) / 3)).toFixed(6));
});
test('INTEGRITY GUARD catches raw/adjusted/dimension/ranking tampering (FC2-03/04 class)', () => {
  const cs = [cand({ id: 'A-1' }), cand({ id: 'B-1', over: { startup_cash_usd: 5000 } })], by = Object.fromEntries(cs.map(c => [c.id, c]));
  const rows = cs.map(c => S.scoreCandidate(c)), order = S.rank(rows).map(r => r.id);
  assert.deepEqual(S.verifyIntegrity(by, rows, order), []);
  for (const mut of [r => { r.raw += 1; }, r => { r.adjusted = r.raw + 5; }, r => { r.dimensions.demand_signal = 5; }, r => { r.per_profile.balanced.adjusted -= 2; }, r => { r.scoring_version = 'old'; }]) {
    const t = JSON.parse(JSON.stringify(rows)); mut(t[0]); assert.ok(S.verifyIntegrity(by, t, order).length > 0, String(mut));
  }
  assert.ok(S.verifyIntegrity(by, rows, [...order].reverse()).includes('ranking_order_mismatch'));
  assert.ok(S.verifyIntegrity(by, [...rows, { ...rows[0], id: 'ZZ-9' }], null).some(x => x.includes('no_source_candidate')));
});
test('ranking is deterministic with ties broken by id', () => {
  const a = S.scoreCandidate(cand({ id: 'B-1' })), b = S.scoreCandidate(cand({ id: 'A-1' }));
  assert.deepEqual(S.rank([a, b]).map(r => r.id), ['A-1', 'B-1']);
});
test('gates: happy path passes', () => assert.equal(runGates(cand()).passed, true));
test('gate: free incumbent (value 0) is never an edge', () => {
  const c = cand(); c.entrant_edge.incumbent_value = 0; c.entrant_edge.entrant_value = 0;
  const g = runGates(c); assert.ok(g.failed.includes('entrant_edge')); assert.match(g.gates.entrant_edge.reason, /no_measured_advantage/);
});
test('gate: edge needs >=25% relative improvement, falsifier, sourced evidence, non-generic wedge', () => {
  const t = (f) => { const c = cand(); f(c); return runGates(c).gates.entrant_edge; };
  assert.equal(t(c => { c.entrant_edge.entrant_value = 40; }).passed, false);
  assert.equal(t(c => { c.entrant_edge.falsifier = ''; }).reason, 'no_falsifier');
  assert.equal(t(c => { c.entrant_edge.incumbent_source_url = 'http://x.com/a'; }).reason, 'incumbent_source_not_https');
  assert.equal(t(c => { c.entrant_edge.incumbent_source_url = 'https://other.com/'; }).reason, 'incumbent_source_not_in_evidence');
  assert.equal(t(c => { c.entrant_wedge = 'Cheaper'; }).reason, 'generic_wedge_only');
  assert.equal(t(c => { c.entrant_edge.entrant_basis = 'short'; }).reason, 'entrant_basis_too_thin');
  assert.equal(t(c => { c.evidence[0].verify.status = 'fetch_failed'; }).reason, 'incumbent_source_not_verified');
});
test('gate: reference entrant limits', () => {
  assert.ok(runGates(cand({ over: { startup_cash_usd: 50000 } })).failed.includes('reference_entrant'));
  assert.ok(runGates(cand({ over: { owner_hours_per_week_steady: 60 } })).failed.includes('reference_entrant'));
});
test('gate: evidence depth needs verified weight and kinds; provisional waives it explicitly', () => {
  const c = cand(); c.evidence.forEach(e => { e.verify = { status: 'agent_reported' }; });
  assert.ok(runGates(c).failed.includes('evidence_depth'));
  assert.equal(runGates(c, { provisional: true }).gates.evidence_depth.reason.startsWith('waived_provisional'), true);
});
test('gate: owner-specific language is rejected from a global candidate', () => {
  assert.ok(runGates(cand({ over: { pain: 'works because my network of dispatchers will buy' } })).failed.includes('owner_leak'));
  assert.ok(runGates(cand({ over: { entrant_wedge: "uses the owner's existing relationships to win customers" } })).failed.includes('owner_leak'));
});
test('gate: schema failure short-circuits', () => { const c = cand(); delete c.dimension_scores; const g = runGates(c); assert.deepEqual(g.failed, ['schema']); });
test('gate: https-only incumbent source is the DEFAULT; only an explicit config may relax it', () => {
  const c = cand({ url: 'http://example.com/pricing' });
  assert.equal(runGates(c).gates.entrant_edge.reason, 'incumbent_source_not_https');
  assert.equal(runGates(c, { require_https_incumbent_source: false }).gates.entrant_edge.passed, true);
});
const { evaluateMeasured } = require('../src/measure');
test('Phase E: G280 entrant_advantage via engine — synthetic evidence never supports a claim; real measured evidence can', () => {
  const sample = JSON.parse(fs.readFileSync(path.join(__dirname, '../fixtures/REVA2_G097_entrant_advantage_fixture.json'), 'utf8'));
  const synth = evaluateMeasured('X-1', sample);
  assert.equal(synth.supportedAdvantageHypothesis, false); assert.ok(synth.reasons.includes('synthetic_evidence_cannot_support_market_claim'));
  const real = JSON.parse(JSON.stringify(sample)); real.incumbentEvidence.syntheticEvidence = false; real.entrantEvidence.syntheticEvidence = false; real.entrantEvidence.artifactSha256 = 'b'.repeat(64);
  const ok = evaluateMeasured('X-1', real); assert.equal(ok.supportedAdvantageHypothesis, true); assert.equal(ok.advantageProven, false, 'even supported claims are only hypotheses (G280 rule)');
  real.entrantEvidence.value = 30; assert.equal(evaluateMeasured('X-1', real).supportedAdvantageHypothesis, false);
});
