'use strict';
// Bounded live check: 1 research call (<=3 searches) + 1 JSON call, 2 candidates. Run BEFORE any full scan.
const { discoverFamily } = require('./discover');
async function smoke({ provider, family = 'saas_or_micro_saas', n = 2, maxUses = 3 }) {
  const rep = { ok: false, family, requested_candidates: n, max_searches: maxUses };
  let r = null;
  try { r = await discoverFamily({ provider, fetcher: null, collect: null, family, perFamily: n, signalsEnabled: false, breaker: { fails: 0, max: 1 }, maxUses, maxAttempts: 1 }); }
  catch (e) { rep.error = e.message; rep.diags = e.diags || []; rep.usage = provider.budget.used; return rep; }
  const ev = r.candidates.flatMap(c => c.evidence), cnt = (st) => ev.filter(e => e.verify.status === st).length, rs = r.research[0] || { excerpts: [], results: [] };
  Object.assign(rep, { parsed_candidates: r.candidates.length, schema_dropped: r.dropped, excerpts_returned: rs.excerpts.length, search_results: rs.results.length,
    evidence: { total: ev.length, verified: cnt('verified'), search_confirmed: cnt('search_confirmed') }, dropped_refs: r.candidates.reduce((a, c) => a + (c._dropped_refs || 0), 0),
    usage: provider.budget.used, diags: r.diags, memo_head: (rs.memo || '').slice(0, 1200), excerpt_sample: rs.excerpts.slice(0, 5),
    sample: r.candidates.slice(0, 2).map(c => ({ id: c.id, name: c.name, edge: c.entrant_edge, evidence: c.evidence.map(e => ({ url: e.url, kind: e.kind, status: e.verify.status, quote: e.quote })) })) });
  rep.ok = r.candidates.length >= 1 && rs.excerpts.length >= 1;
  if (r.candidates.length >= 1 && rs.excerpts.length === 0) rep.error = 'no_citation_excerpts_returned_by_search: evidence cannot reach verified';
  return rep;
}
module.exports = { smoke };
