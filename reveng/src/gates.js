'use strict';
const { validateCandidate, EDGE_CRITERIA, EDGE_DIRECTIONS } = require('./schema');
const { evW } = require('./scoring');
const DEFAULTS = {
  max_startup_cash_usd: 10000, max_days_to_first_revenue: 365, max_owner_hours_per_week: 40, min_relative_edge_improvement: 0.25,
  require_https_incumbent_source: true, min_evidence_items: 3, min_evidence_weight: 2.0, required_evidence_kinds: ['incumbent_price', 'demand', 'constraint'],
  owner_leak_patterns: ['\\bmy (network|contacts|friends|company|truck|license|experience)\\b', "\\bthe owner'?s\\b", '\\bowner (has|already has|owns|knows)\\b',
    '\\bwarm (network|intro)', '\\bprior (trucking|industry) experience\\b'],
};
const GENERIC = new Set(['ai', 'uses ai', 'ai powered', 'ai-powered', 'cheaper', 'better ux', 'better user experience', 'better experience', 'faster', 'simpler']);
const gateSchema = (c) => { const e = validateCandidate(c); return [!e.length, e.slice(0, 5).join(';') || 'ok']; };
function gateReferenceEntrant(c, g) {
  const r = [];
  if (c.startup_cash_usd > g.max_startup_cash_usd) r.push(`startup_cash ${c.startup_cash_usd}>${g.max_startup_cash_usd}`);
  if (c.time_to_first_revenue_days > g.max_days_to_first_revenue) r.push(`days_to_revenue ${c.time_to_first_revenue_days}>${g.max_days_to_first_revenue}`);
  if (c.owner_hours_per_week_steady > g.max_owner_hours_per_week) r.push(`owner_hours ${c.owner_hours_per_week_steady}>${g.max_owner_hours_per_week}`);
  return [!r.length, r.join(';') || 'ok'];
}
function gateEntrantEdge(c, g) {
  const e = c.entrant_edge;
  if (!e || typeof e !== 'object') return [false, 'no_entrant_edge_object'];
  if (!EDGE_CRITERIA.includes(e.criterion)) return [false, 'bad_criterion'];
  if (!EDGE_DIRECTIONS.includes(e.direction)) return [false, 'bad_direction'];
  if (g.require_https_incumbent_source !== false && !/^https:\/\//i.test(String(e.incumbent_source_url || ''))) return [false, 'incumbent_source_not_https'];
  if (!String(e.falsifier || '').trim()) return [false, 'no_falsifier'];
  if (String(e.entrant_basis || '').trim().length < 20) return [false, 'entrant_basis_too_thin'];
  if (GENERIC.has(String(c.entrant_wedge || '').trim().toLowerCase())) return [false, 'generic_wedge_only'];
  const inc = Number(e.incumbent_value), ent = Number(e.entrant_value);
  if (!Number.isFinite(inc) || !Number.isFinite(ent)) return [false, 'edge_values_not_numeric'];
  const delta = e.direction === 'lower_is_better' ? inc - ent : ent - inc;
  if (delta <= 0) return [false, `no_measured_advantage(inc=${inc},ent=${ent})`];
  const rel = inc === 0 ? null : delta / Math.abs(inc);
  if (rel === null || rel < g.min_relative_edge_improvement) return [false, `improvement_below_threshold(${rel})`];
  const src = (c.evidence || []).find(x => x.url === e.incumbent_source_url);
  if (!src) return [false, 'incumbent_source_not_in_evidence'];
  if (!g.provisional && evW(src) === 0) return [false, 'incumbent_source_not_verified'];
  return [true, `relative_improvement=${rel.toFixed(2)}`];
}
function gateEvidenceDepth(c, g) {
  if (g.provisional) return [true, 'waived_provisional(evidence not engine-verified)'];
  const ev = c.evidence || [], kinds = new Set(ev.filter(x => evW(x) > 0).map(x => x.kind)), w = ev.reduce((a, x) => a + evW(x), 0), r = [];
  const miss = g.required_evidence_kinds.filter(k => !kinds.has(k));
  if (ev.length < g.min_evidence_items) r.push(`items ${ev.length}<${g.min_evidence_items}`);
  if (w < g.min_evidence_weight) r.push(`verified_weight ${w}<${g.min_evidence_weight}`);
  if (miss.length) r.push('missing_verified_kinds:' + miss.join(','));
  return [!r.length, r.join(';') || 'ok'];
}
function gateOwnerLeak(c, g) {
  const txt = ['name', 'buyer', 'pain', 'entrant_wedge'].map(k => String(c[k] || '')).join(' ') + ' ' + String((c.entrant_edge || {}).entrant_basis || '');
  const hits = g.owner_leak_patterns.filter(p => new RegExp(p, 'i').test(txt));
  return [!hits.length, hits.length ? 'owner_specific_language:' + hits.join(',') : 'ok'];
}
const ORDER = [['reference_entrant', gateReferenceEntrant], ['entrant_edge', gateEntrantEdge], ['evidence_depth', gateEvidenceDepth], ['owner_leak', gateOwnerLeak]];
function runGates(c, cfg = {}) {
  const g = { ...DEFAULTS, ...cfg }, res = {}, [ok, why] = gateSchema(c);
  res.schema = { passed: ok, reason: why };
  if (!ok) return { passed: false, gates: res, failed: ['schema'] };
  for (const [n, fn] of ORDER) { const [p, r] = fn(c, g); res[n] = { passed: p, reason: r }; }
  const failed = Object.keys(res).filter(k => !res[k].passed);
  return { passed: !failed.length, gates: res, failed };
}
module.exports = { DEFAULTS, runGates };
