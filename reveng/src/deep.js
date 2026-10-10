'use strict';
const { deepMemoPrompts, deepJsonPrompts } = require('./prompts');
const { twoPhase, resolveEvidence } = require('./research');
const { load } = require('../vendor/load');
const { EDGE_CRITERIA, EDGE_DIRECTIONS, isNum } = require('./schema');
const econ = load('economics_contract');
const DEEP_PROTOCOL = 2;   // 2 = structured kill reasons (severity + cited ref); older deep results are re-screened so every candidate gets the same method
const MODEL_KEYS = ['price', 'units', 'revenue', 'cashCost', 'contribution', 'ownerHours', 'startup', 'automation', 'launchDays'];
// Economics via frozen G280 economics_contract.normalize (cashMargin, startupPayback, firstYearStartupRoi). Pessimistic = explicit MODEL, not evidence.
function economics(model) {
  if (!model || typeof model !== 'object') return { status: 'no_model' };
  const raw = Object.fromEntries(MODEL_KEYS.filter(k => Number.isFinite(Number(model[k]))).map(k => [k, Number(model[k])]));
  const base = econ.normalize(raw, { source: 'deep_screen_model' });
  const val = (m, k) => (m[k] && m[k].known ? m[k].value : null);
  const pess = { ...raw, price: raw.price * 0.8, units: raw.units * 0.5, revenue: raw.revenue * 0.4, cashCost: raw.cashCost * 0.5 };
  pess.contribution = pess.revenue - pess.cashCost;
  const p = econ.normalize(pess, { source: 'deep_screen_pessimistic_model' });
  return { status: 'computed', class: 'model', assumptions: model.assumptions || [],
    baseline: { cashMarginPct: val(base, 'cashMargin'), profitPerOwnerHour: val(base, 'profitOwnerHour'), startupPaybackMonths: val(base, 'startupPayback'), firstYearRoiPct: val(base, 'firstYearStartupRoi'), contributionUsdPerMonth: val(base, 'contribution') },
    pessimistic: { rule: 'price x0.8, units x0.5, cash cost x0.5', cashMarginPct: val(p, 'cashMargin'), contributionUsdPerMonth: val(p, 'contribution'), startupPaybackMonths: val(p, 'startupPayback') },
    survives_pessimistic: val(p, 'contribution') !== null && val(p, 'contribution') > 0 };
}
// Normalise kill reasons: {reason, severity: fatal|major|minor, ref}. fatal+C# ref (provider excerpt) = verified; anything else is only a claim.
function killReasons(list, idx) {
  return (Array.isArray(list) ? list : []).map(x => {
    const o = typeof x === 'string' ? { reason: x, severity: 'minor' } : (x && typeof x === 'object' ? x : null);
    if (!o || !String(o.reason || '').trim()) return null;
    const sev = ['fatal', 'major', 'minor'].includes(o.severity) ? o.severity : 'minor', ref = String(o.ref || ''), src = idx.byId[ref];
    return { reason: String(o.reason).trim().slice(0, 400), severity: sev, ref: src ? ref : null, ref_status: src ? (ref.startsWith('C') ? 'verified' : 'search_confirmed') : 'none', url: src ? src.url : null, cited_text: src && src.cited_text ? src.cited_text.slice(0, 300) : null };
  }).filter(Boolean);
}
async function deepScreen({ provider, candidate, minVerified = 3, maxUses }) {
  const r = await twoPhase({ provider, p1: deepMemoPrompts({ candidate }), buildP2: (memo, idx) => deepJsonPrompts({ candidate, memo, idx }), maxUses, expect: 'object' });
  if (!r.ok) throw new Error('deep_screen_failed:' + r.error);
  const d = r.data, c = JSON.parse(JSON.stringify(candidate));
  const { evidence: newEv, map } = resolveEvidence(d.evidence, r.idx, `${c.id}-D`);
  newEv.forEach(e => { e.stage = 'deep'; });
  c.evidence = [...(c.evidence || []), ...newEv];
  const rv = d.revised || {}, num = (k) => (Number.isFinite(rv[k]) ? rv[k] : c[k]);
  c.startup_cash_usd = num('startup_cash_usd'); c.time_to_first_revenue_days = num('time_to_first_revenue_days');
  c.owner_hours_per_week_steady = num('owner_hours_per_week_steady'); c.automation_potential_pct = num('automation_potential_pct');
  if (rv.contribution_margin_pct !== undefined) c.unit_economics = { ...c.unit_economics, contribution_margin_pct: rv.contribution_margin_pct, class: 'model' };
  if (rv.dimension_scores) for (const [k, v] of Object.entries(rv.dimension_scores)) if (Number.isInteger(v) && v >= 0 && v <= 5 && k in c.dimension_scores) c.dimension_scores[k] = v;
  if (rv.dimension_evidence) { const de = {}; for (const [k, refs] of Object.entries(rv.dimension_evidence)) de[k] = (Array.isArray(refs) ? refs : []).map(x => map[String(x)]).filter(Boolean); c.dimension_evidence = de; }
  let edgeNote = null;
  if (rv.entrant_edge && typeof rv.entrant_edge === 'object') {
    const e = { ...rv.entrant_edge }, src = r.idx.byId[String(e.incumbent_ref || '')];
    // A revised edge must keep the schema (enumerated criterion/direction, numeric values). Otherwise keep the ORIGINAL edge: a formatting slip must not silently decide a candidate's fate.
    if (EDGE_CRITERIA.includes(e.criterion) && EDGE_DIRECTIONS.includes(e.direction) && isNum(e.incumbent_value) && isNum(e.entrant_value)) {
      e.incumbent_source_url = src ? src.url : (c.entrant_edge || {}).incumbent_source_url || ''; delete e.incumbent_ref; c.entrant_edge = e;
    } else edgeNote = 'revised_entrant_edge_rejected_by_schema(kept original)';
  }
  const ver = newEv.filter(x => x.verify.status === 'verified').length;
  c.deep = { done: true, verified_deep_evidence: ver, complete: ver >= minVerified, competitors: d.competitors || [], constraints: d.constraints || [], kill_reasons: killReasons(d.kill_reasons, r.idx), protocol: DEEP_PROTOCOL, edge_note: edgeNote, unknowns: d.unknowns || [],
    economics: economics(d.monthly_model), excerpts_returned: r.idx.excerpts.length, usage: [r.r1.usage, r.r2.usage] };
  return c;
}
module.exports = { deepScreen, economics, killReasons, DEEP_PROTOCOL };
