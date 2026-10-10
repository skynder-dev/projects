'use strict';
// reveng_v6_independent: pure functions. No owner/user context is accepted or read here.
const { DIMENSIONS, MECHANICAL, JUDGED } = require('./schema');
const { load } = require('../vendor/load');
const SCORING_VERSION = 'reveng_v6_independent';
const GLOBAL_PROFILE = 'balanced';
const EVIDENCE_CAP_SCORE = 3, UNKNOWN_DEFAULT = 2;
// Weights come straight from the frozen G280 scoring_profiles.js (label -> dimension key).
const LABEL2KEY = { 'Contribution economics': 'contribution_economics', 'Demand signal': 'demand_signal', 'Acquisition efficiency': 'acquisition_efficiency',
  'Automation': 'automation', 'Competition gap': 'competition_gap', 'Defensibility': 'defensibility', 'Owner time efficiency': 'owner_time_efficiency',
  'Capital efficiency': 'capital_efficiency', 'Launch speed': 'launch_speed', 'Platform resilience': 'platform_resilience',
  'Scale without hiring': 'scale_without_hiring', 'Fulfillment simplicity': 'fulfillment_simplicity', 'Regulatory simplicity': 'regulatory_simplicity' };
const PROFILES = {};
for (const p of load('scoring_profiles').list()) PROFILES[p.key] = Object.fromEntries(p.fullWeights.map(([l, w]) => [LABEL2KEY[l], w]));

const band = (v, bands, higher) => { for (const [t, s] of bands) if (higher ? v >= t : v <= t) return s; return 0; };
function mechanicalScores(c) {
  const m = (c.unit_economics || {}).contribution_margin_pct;
  return {
    capital_efficiency: band(c.startup_cash_usd, [[200, 5], [1000, 4], [3000, 3], [6000, 2], [10000, 1]], false),
    launch_speed: band(c.time_to_first_revenue_days, [[14, 5], [30, 4], [90, 3], [180, 2], [365, 1]], false),
    owner_time_efficiency: band(c.owner_hours_per_week_steady, [[3, 5], [8, 4], [15, 3], [25, 2], [40, 1]], false),
    automation: band(c.automation_potential_pct, [[90, 5], [75, 4], [55, 3], [35, 2], [15, 1]], true),
    contribution_economics: (m === null || m === undefined) ? UNKNOWN_DEFAULT : band(m, [[70, 5], [55, 4], [40, 3], [25, 2], [10, 1]], true),
  };
}
function judgedScores(c, verifiedIds) {
  const out = {}, capped = [], cites = c.dimension_evidence || {};
  for (const d of JUDGED) {
    let v = c.dimension_scores[d];
    if (v > EVIDENCE_CAP_SCORE && !(cites[d] || []).some(i => verifiedIds.has(i))) { capped.push(d); v = EVIDENCE_CAP_SCORE; }
    out[d] = v;
  }
  return { out, capped };
}
const EV_W = { verified: 1.0, search_confirmed: 0.5 };
const evW = (x) => EV_W[(x.verify || {}).status] || 0;
function evidenceConfidence(ev) { if (!ev || !ev.length) return 0.5; return r6(0.5 + 0.5 * (ev.reduce((a, x) => a + evW(x), 0) / ev.length)); }
const r6 = (x) => Math.round(x * 1e6) / 1e6;
const weighted = (s, w) => r6(DIMENSIONS.reduce((a, d) => a + w[d] * s[d], 0) / 5);
function scoreCandidate(c, profile = GLOBAL_PROFILE) {
  const verifiedIds = new Set((c.evidence || []).filter(x => (x.verify || {}).status === 'verified').map(x => x.id));
  const { out, capped } = judgedScores(c, verifiedIds);
  const dims = { ...mechanicalScores(c), ...out }, conf = evidenceConfidence(c.evidence);
  const perProfile = {};
  for (const [n, w] of Object.entries(PROFILES)) { const raw = weighted(dims, w); perProfile[n] = { raw, adjusted: r6(raw * conf) }; }
  return { id: c.id, family: c.family, scoring_version: SCORING_VERSION, profile, dimensions: dims, evidence_capped_dimensions: capped,
    evidence_confidence: conf, raw: perProfile[profile].raw, adjusted: perProfile[profile].adjusted, per_profile: perProfile };
}
const rank = (rows, profile = GLOBAL_PROFILE) => [...rows].sort((a, b) => (b.per_profile[profile].adjusted - a.per_profile[profile].adjusted) || (a.id < b.id ? -1 : 1));
// Integrity guard (FC2-03 / FC2-04 defect class): recompute from raw facts, compare with stored values.
function verifyIntegrity(candidatesById, rows, rankingIds = null, tol = 1e-6) {
  const bad = [];
  for (const r of rows) {
    const c = candidatesById[r.id]; if (!c) { bad.push(`${r.id}:no_source_candidate`); continue; }
    const f = scoreCandidate(c, r.profile);
    for (const k of ['raw', 'adjusted', 'evidence_confidence']) if (Math.abs(f[k] - r[k]) > tol) bad.push(`${r.id}:${k}:stored=${r[k]}:recomputed=${f[k]}`);
    if (JSON.stringify(f.dimensions) !== JSON.stringify(r.dimensions)) bad.push(`${r.id}:dimensions_mismatch`);
    for (const [n, v] of Object.entries(f.per_profile)) { const s = (r.per_profile || {})[n]; if (!s || Math.abs(s.raw - v.raw) > tol || Math.abs(s.adjusted - v.adjusted) > tol) bad.push(`${r.id}:profile:${n}`); }
    if (r.adjusted - r.raw > tol) bad.push(`${r.id}:adjusted_exceeds_raw`);
    if (!(r.raw >= 0 && r.raw <= 100 + tol)) bad.push(`${r.id}:raw_out_of_range`);
    if (r.scoring_version !== SCORING_VERSION) bad.push(`${r.id}:wrong_scoring_version`);
  }
  if (rankingIds) { const exp = rank(rows).map(r => r.id); if (JSON.stringify(rankingIds) !== JSON.stringify(exp)) bad.push('ranking_order_mismatch'); }
  for (const w of Object.values(PROFILES)) if (Object.values(w).reduce((a, b) => a + b, 0) !== 100 || Object.keys(w).length !== 13) bad.push('profile_weights_invalid');
  return bad;
}
module.exports = { SCORING_VERSION, GLOBAL_PROFILE, PROFILES, EVIDENCE_CAP_SCORE, mechanicalScores, evidenceConfidence, scoreCandidate, rank, verifyIntegrity, evW };
