'use strict';
const FAMILIES_REQUIRED = ['games', 'saas_or_micro_saas', 'ecommerce_or_dropshipping', 'services', 'marketplaces', 'digital_or_data_products', 'physical_products', 'media_or_content'];
const FAMILIES_EXTRA = ['education_training', 'b2b_api_devtools'];
const DIMENSIONS = ['contribution_economics', 'demand_signal', 'acquisition_efficiency', 'automation', 'competition_gap', 'defensibility',
  'owner_time_efficiency', 'capital_efficiency', 'launch_speed', 'platform_resilience', 'scale_without_hiring', 'fulfillment_simplicity', 'regulatory_simplicity'];
const MECHANICAL = ['contribution_economics', 'automation', 'owner_time_efficiency', 'capital_efficiency', 'launch_speed'];
const JUDGED = DIMENSIONS.filter(d => !MECHANICAL.includes(d));
const EDGE_CRITERIA = ['cash_cost', 'owner_time', 'cycle_time', 'step_count', 'channel_reach', 'required_tool_count'];
const EDGE_DIRECTIONS = ['lower_is_better', 'higher_is_better'];
const EVIDENCE_KINDS = ['incumbent_price', 'demand', 'constraint', 'other'];
const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
function validateCandidate(c) {
  const e = [];
  if (!c || typeof c !== 'object' || Array.isArray(c)) return ['not_an_object'];
  for (const k of ['id', 'name', 'family', 'buyer', 'pain', 'entrant_wedge']) if (!String(c[k] ?? '').trim()) e.push('missing:' + k);
  for (const k of ['startup_cash_usd', 'time_to_first_revenue_days', 'owner_hours_per_week_steady', 'automation_potential_pct']) if (!isNum(c[k])) e.push('not_number:' + k);
  if (!Array.isArray(c.evidence)) e.push('evidence_not_list');
  else c.evidence.forEach((x, i) => { if (!x || !/^https?:\/\//.test(x.url || '')) e.push(`evidence[${i}]:bad_url`); else if (!EVIDENCE_KINDS.includes(x.kind)) e.push(`evidence[${i}]:bad_kind`); });
  if (!c.dimension_scores || typeof c.dimension_scores !== 'object') e.push('dimension_scores_missing');
  else for (const d of JUDGED) { const v = c.dimension_scores[d]; if (!Number.isInteger(v) || v < 0 || v > 5) e.push(`dimension:${d}:not_int_0_5`); }
  if (!c.unit_economics || typeof c.unit_economics !== 'object') e.push('unit_economics_missing');
  return e;
}
module.exports = { FAMILIES_REQUIRED, FAMILIES_EXTRA, DIMENSIONS, MECHANICAL, JUDGED, EDGE_CRITERIA, EDGE_DIRECTIONS, EVIDENCE_KINDS, validateCandidate, isNum };
